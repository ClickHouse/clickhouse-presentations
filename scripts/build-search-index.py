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
OCRed with tesseract. OCR results are cached in scripts/ocr-cache.json, keyed
by the SVG file's SHA-256, so only new or changed SVGs require the OCR tools.

Usage: python3 scripts/build-search-index.py
Dependencies (only on OCR cache miss): librsvg2-bin, tesseract-ocr.
"""

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


def ocr_svg(svg_path, cache, used_cache):
    """Returns OCRed text of an SVG slide, using/updating the cache."""
    with open(svg_path, 'rb') as f:
        content = f.read()
    digest = hashlib.sha256(content).hexdigest()
    rel_path = os.path.relpath(svg_path, REPO_ROOT)
    if digest in cache:
        used_cache[digest] = {'file': rel_path, 'text': cache[digest]['text']}
        return cache[digest]['text']

    if not (shutil.which('rsvg-convert') and shutil.which('tesseract')):
        sys.exit(f'error: need to OCR {rel_path} but rsvg-convert/tesseract '
                 f'are not installed (apt-get install librsvg2-bin tesseract-ocr)')

    print(f'  OCR {rel_path}')
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, 'slide.png')
        subprocess.run(['rsvg-convert', '-w', str(SVG_RENDER_WIDTH), svg_path, '-o', png],
                       check=True)
        result = subprocess.run(['tesseract', png, 'stdout', '-l', 'eng'],
                                check=True, capture_output=True, text=True)
    text = ' '.join(result.stdout.split())
    used_cache[digest] = {'file': rel_path, 'text': text}
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
    size_mb = os.path.getsize(OUTPUT_JS) / 1e6
    print(f'{len(presentations)} presentations, {total_slides} slides, '
          f'{len(used_cache)} OCRed SVGs, search-index.js {size_mb:.1f} MB')


if __name__ == '__main__':
    main()
