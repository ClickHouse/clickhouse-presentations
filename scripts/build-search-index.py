#!/usr/bin/env python3
"""Build search-index.js for the ClickHouse Theater main page (index.html).

For every presentation card linked from index.html, extracts the visible text
of each slide so the main page can offer instant full-text search with links
to individual slides. The index is a JS file assigning window.SEARCH_INDEX
(not JSON + fetch) so that the page also works when opened from file://.

Slide ids replicate shower.js behavior (see shower/shower.js, _initSlides):
a slide keeps its explicit id attribute; a slide without one gets its 1-based
position among the non-hidden slides. This makes "path/#id" deep links work.

Slides that have (almost) no HTML text but display an SVG image (via
<img src="*.svg"> or a CSS background url) are rendered with rsvg-convert and
transcribed. The primary transcriber is Claude (vision), used when
ANTHROPIC_API_KEY is set; otherwise tesseract OCR is the fallback. Results are
cached in scripts/ocr-cache.json, keyed by the SVG file's SHA-256, with the
engine recorded per entry — tesseract-produced entries are automatically
re-transcribed with Claude on the first run that has an API key.

Usage: [ANTHROPIC_API_KEY=...] python3 scripts/build-search-index.py
Dependencies (only on OCR cache miss): librsvg2-bin, and either the anthropic
Python package (with ANTHROPIC_API_KEY) or tesseract-ocr.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(REPO_ROOT, 'index.html')
OUTPUT_JS = os.path.join(REPO_ROOT, 'search-index.js')
OCR_CACHE_JSON = os.path.join(REPO_ROOT, 'scripts', 'ocr-cache.json')

# A slide with less text than this that shows an SVG is considered image-only.
MIN_TEXT_FOR_NO_OCR = 20
SVG_RENDER_WIDTH = 1920

CLAUDE_MODEL = 'claude-haiku-4-5'
TRANSCRIBE_PROMPT = (
    'Transcribe all text visible in this slide image, in reading order. '
    'Output only the transcribed plain text, with no commentary and no markdown. '
    'Include code, URLs, and numbers verbatim. '
    'Never describe pictures, logos, charts, or visual layout — output only '
    'text that is literally visible. '
    'If the slide contains no readable text, output exactly: (no text)'
)

SVG_URL_RE = re.compile(r'''url\(\s*['"]?([^'")]+\.svg)['"]?\s*\)''', re.I)


class CardParser(HTMLParser):
    """Collects hrefs of <a class="card"> links from index.html."""

    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        attrs = dict(attrs)
        if 'card' in (attrs.get('class') or '').split():
            href = attrs.get('href')
            if href and not href.startswith('http'):
                self.hrefs.append(href)


class SlideParser(HTMLParser):
    """Extracts per-slide text and SVG references from a presentation page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.slides = []          # {'id': str, 'text': [chunks], 'svgs': [paths]}
        self.current = None
        self.section_depth = 0    # nested <section> inside the current slide
        self.skip_tag = None      # inside <script> or <style>
        self.visible_index = 0    # counts non-hidden slides, like shower.js

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.current is None:
            if tag == 'section' and 'slide' in (attrs.get('class') or '').split():
                if 'hidden' in attrs:
                    return
                self.visible_index += 1
                self.current = {
                    'id': attrs.get('id') or str(self.visible_index),
                    'text': [],
                    'svgs': [],
                }
                self._collect_svgs(tag, attrs)
            return
        if tag == 'section':
            self.section_depth += 1
        if tag in ('script', 'style') and self.skip_tag is None:
            self.skip_tag = tag
        self._collect_svgs(tag, attrs)

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == self.skip_tag:
            self.skip_tag = None
            return
        if tag == 'section':
            if self.section_depth > 0:
                self.section_depth -= 1
            else:
                slide = self.current
                slide['text'] = ' '.join(' '.join(slide['text']).split())
                self.slides.append(slide)
                self.current = None
                self.skip_tag = None

    def handle_data(self, data):
        if self.current is not None and self.skip_tag is None:
            self.current['text'].append(data)

    def _collect_svgs(self, tag, attrs):
        src = attrs.get('src') or ''
        if tag == 'img' and src.lower().endswith('.svg'):
            self.current['svgs'].append(src)
        style = attrs.get('style') or ''
        for match in SVG_URL_RE.findall(style):
            self.current['svgs'].append(match)


def load_ocr_cache():
    if os.path.exists(OCR_CACHE_JSON):
        with open(OCR_CACHE_JSON, encoding='utf-8') as f:
            return json.load(f)
    return {}


_claude_client = None  # None = not initialized, False = unavailable


def claude_client():
    """Returns an Anthropic client, or None when ANTHROPIC_API_KEY is not set."""
    global _claude_client
    if _claude_client is None:
        if os.environ.get('ANTHROPIC_API_KEY'):
            try:
                import anthropic
            except ImportError:
                sys.exit('error: ANTHROPIC_API_KEY is set but the anthropic '
                         'package is not installed (pip install anthropic)')
            _claude_client = anthropic.Anthropic(max_retries=5)
        else:
            _claude_client = False
    return _claude_client or None


def transcribe_with_claude(png_path):
    with open(png_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')
    response = claude_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image',
                 'source': {'type': 'base64', 'media_type': 'image/png', 'data': image_data}},
                {'type': 'text', 'text': TRANSCRIBE_PROMPT},
            ],
        }],
    )
    if response.stop_reason == 'refusal':
        raise RuntimeError('transcription refused')
    text = ' '.join(' '.join(b.text for b in response.content if b.type == 'text').split())
    if text.strip('.').lower() == '(no text)':
        return ''
    return text


def transcribe_with_tesseract(png_path, rel_path):
    if not shutil.which('tesseract'):
        sys.exit(f'error: need to OCR {rel_path} but neither ANTHROPIC_API_KEY '
                 f'nor tesseract is available (apt-get install tesseract-ocr)')
    result = subprocess.run(['tesseract', png_path, 'stdout', '-l', 'eng'],
                            check=True, capture_output=True, text=True)
    return ' '.join(result.stdout.split())


def ocr_svg(svg_path, cache, used_cache):
    """Returns transcribed text of an SVG slide, using/updating the cache.

    Cache entries record which engine produced them; when Claude is available,
    tesseract-produced entries are re-transcribed once and upgraded.
    """
    with open(svg_path, 'rb') as f:
        content = f.read()
    digest = hashlib.sha256(content).hexdigest()
    rel_path = os.path.relpath(svg_path, REPO_ROOT)

    entry = cache.get(digest)
    claude = claude_client()
    if entry and (entry.get('engine') == CLAUDE_MODEL or not claude):
        entry = {'file': rel_path, 'engine': entry.get('engine', 'tesseract'),
                 'text': entry['text']}
        used_cache[digest] = entry
        return entry['text']

    if not shutil.which('rsvg-convert'):
        sys.exit(f'error: need to render {rel_path} but rsvg-convert is not '
                 f'installed (apt-get install librsvg2-bin)')

    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, 'slide.png')
        subprocess.run(['rsvg-convert', '-w', str(SVG_RENDER_WIDTH), svg_path, '-o', png],
                       check=True)
        if claude:
            import anthropic
            try:
                print(f'  transcribe {rel_path} ({CLAUDE_MODEL})')
                text, engine = transcribe_with_claude(png), CLAUDE_MODEL
            except anthropic.AuthenticationError:
                sys.exit('error: the Anthropic API rejected ANTHROPIC_API_KEY')
            except Exception as e:
                print(f'  warning: Claude transcription of {rel_path} failed '
                      f'({e}), falling back', file=sys.stderr)
                if entry:  # keep the existing tesseract text, retry next run
                    used_cache[digest] = {'file': rel_path, 'engine': 'tesseract',
                                          'text': entry['text']}
                    return entry['text']
                text, engine = transcribe_with_tesseract(png, rel_path), 'tesseract'
        else:
            print(f'  OCR {rel_path} (tesseract)')
            text, engine = transcribe_with_tesseract(png, rel_path), 'tesseract'

    used_cache[digest] = {'file': rel_path, 'engine': engine, 'text': text}
    return text


def process_presentation(href, cache, used_cache):
    if href.endswith('/'):
        html_path = os.path.join(REPO_ROOT, href, 'index.html')
    elif href.endswith(('.html', '.htm')):
        html_path = os.path.join(REPO_ROOT, href)
    else:
        return None  # PDFs and the like: searchable by title only
    if not os.path.exists(html_path):
        print(f'  warning: {href} has no index.html, skipping', file=sys.stderr)
        return None

    parser = SlideParser()
    with open(html_path, encoding='utf-8', errors='replace') as f:
        parser.feed(f.read())
    parser.close()

    base_dir = os.path.dirname(html_path)
    slides = []
    for slide in parser.slides:
        text = slide['text']
        if len(text) < MIN_TEXT_FOR_NO_OCR and slide['svgs']:
            for svg in dict.fromkeys(slide['svgs']):
                svg_path = os.path.normpath(os.path.join(base_dir, svg))
                if not svg_path.startswith(REPO_ROOT) or not os.path.exists(svg_path):
                    continue
                ocr_text = ocr_svg(svg_path, cache, used_cache)
                text = ' '.join(filter(None, [text, ocr_text]))
        if text:
            slides.append([slide['id'], text])
    if not slides:
        return None
    return {'path': href, 'slides': slides}


def main():
    with open(INDEX_HTML, encoding='utf-8') as f:
        card_parser = CardParser()
        card_parser.feed(f.read())
        card_parser.close()
    if not card_parser.hrefs:
        sys.exit('error: no presentation cards found in index.html')

    cache = load_ocr_cache()
    used_cache = {}
    presentations = []
    for href in card_parser.hrefs:
        entry = process_presentation(href, cache, used_cache)
        if entry:
            presentations.append(entry)

    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write('window.SEARCH_INDEX=')
        json.dump({'presentations': presentations}, f,
                  ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    with open(OCR_CACHE_JSON, 'w', encoding='utf-8') as f:
        json.dump(used_cache, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')

    total_slides = sum(len(p['slides']) for p in presentations)
    by_engine = {}
    for entry in used_cache.values():
        by_engine[entry['engine']] = by_engine.get(entry['engine'], 0) + 1
    engines = ', '.join(f'{n} by {e}' for e, n in sorted(by_engine.items()))
    size_mb = os.path.getsize(OUTPUT_JS) / 1e6
    print(f'{len(presentations)} presentations, {total_slides} slides, '
          f'{len(used_cache)} transcribed SVGs ({engines or "none"}), '
          f'search-index.js {size_mb:.1f} MB')


if __name__ == '__main__':
    main()
