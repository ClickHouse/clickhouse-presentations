#!/usr/bin/env python3
"""
Generate the ClickHouse Theater front page with all presentations.
Run: python3 generate_theater.py
"""

import os
import re
from html import escape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def extract_title(filepath):
    """Extract the title from an HTML file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(4096)  # Read first 4KB
        match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    except:
        pass
    return None

def is_shower_presentation(filepath):
    """Check if the file is a Shower presentation."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(8192)
        return 'shower' in content.lower() and 'class="slide"' in content
    except:
        return False

def extract_date_key(dirname):
    """Extract a sortable date key from directory name."""
    # Try to extract year and version/date info
    # Patterns: "2025-release-25.12", "meetup138", "2024-aws", etc.

    # First, try to find a year at the start
    year_match = re.match(r'^(\d{4})', dirname)
    year = int(year_match.group(1)) if year_match else 0

    # Try to extract release version (e.g., 25.12 -> 2512)
    release_match = re.search(r'release[_-](\d+)\.(\d+)', dirname)
    if release_match:
        major = int(release_match.group(1))
        minor = int(release_match.group(2))
        # Convert to sortable: 25.12 -> 202512, 24.1 -> 202401
        return (2000 + major, minor * 100 + 1000, dirname)

    # Try meetup number
    meetup_match = re.search(r'meetup(\d+)', dirname)
    if meetup_match:
        meetup_num = int(meetup_match.group(1))
        return (year if year else 2020, meetup_num, dirname)

    # Default: use year and alphabetical
    return (year if year else 2000, 0, dirname)

def find_presentations():
    """Find all presentations with their metadata."""
    presentations = []

    for root, dirs, files in os.walk(BASE_DIR):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['shower', 'node_modules', '.git', 'pictures']]

        if 'index.html' not in files:
            continue

        filepath = os.path.join(root, 'index.html')

        # Skip the main index.html (theater page itself)
        if root == BASE_DIR:
            continue

        if not is_shower_presentation(filepath):
            continue

        title = extract_title(filepath)
        if not title:
            continue

        # Get relative path from base
        rel_path = os.path.relpath(root, BASE_DIR)

        # Check for preview image
        preview_jpg = os.path.join(root, 'pictures', 'preview.jpg')
        preview_png = os.path.join(root, 'pictures', 'preview.png')

        if os.path.isfile(preview_jpg):
            preview = f"{rel_path}/pictures/preview.jpg"
        elif os.path.isfile(preview_png):
            preview = f"{rel_path}/pictures/preview.png"
        else:
            preview = None

        # Get date key for sorting
        date_key = extract_date_key(rel_path.split('/')[0])

        presentations.append({
            'title': title,
            'path': rel_path,
            'preview': preview,
            'date_key': date_key,
        })

    # Sort by date, newer first
    presentations.sort(key=lambda x: x['date_key'], reverse=True)

    return presentations

def generate_html(presentations):
    """Generate the theater HTML page."""

    cards_html = []
    for p in presentations:
        title = escape(p['title'])
        path = escape(p['path'])

        if p['preview']:
            preview = escape(p['preview'])
            img_html = f'<img src="{preview}" alt="{title}" loading="lazy">'
        else:
            img_html = f'<div class="no-preview"><span>No Preview</span></div>'

        card = f'''<a href="{path}/" class="card" data-title="{title.lower()}">
    {img_html}
    <div class="card-title">{title}</div>
</a>'''
        cards_html.append(card)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>ClickHouse Theater</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            background: #222;
            min-height: 100vh;
            color: #fff;
        }}

        .header {{
            text-align: center;
            padding: 40px 20px 30px 20px;
            backdrop-filter: blur(10px) brightness(0.5);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ff0, #fff, #ff0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .links {{
            color: gray;
            font-size: 1.2rem;
            margin-top: 20px;
        }}

        .links a {{
            color: #887;
            text-decoration: none;
            padding: 1em;
        }}

        .links a:hover {{
            color: #FFD;
        }}

        .search-container {{
            max-width: 500px;
            margin: 0 auto;
        }}

        #search {{
            width: 100%;
            padding: 15px 20px;
            font-size: 1.1em;
            border: none;
            border-radius: 30px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            outline: none;
            transition: all 0.3s ease;
        }}

        #search::placeholder {{
            color: #888;
        }}

        #search:focus {{
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 0 20px rgba(249, 199, 79, 0.3);
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
            padding: 30px;
        }}

        .grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 25px;
            justify-content: center;
        }}

        .card {{
            width: 320px;
            background: black;
            overflow: hidden;
            text-decoration: none;
            color: #fff;
            transition: all 0.1s ease;
            box-shadow: 0px 0px 30px black;
        }}

        .card:hover {{
            transform: translateY(-10px) scale(1.03);
            box-shadow: 0 20px 40px black;
        }}

        .card img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            display: block;
        }}

        .no-preview {{
            width: 100%;
            height: 180px;
            background: linear-gradient(135deg, #2d2d44 0%, #1a1a2e 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #555;
            font-size: 0.9em;
        }}

        .card-title {{
            color: gray;
            padding: 0.5rem 1rem;
            font-size: 0.95em;
            line-height: 1.4;
            text-align: center;
            background: rgba(0, 0, 0, 0.3);
        }}

        .card.hidden {{
            display: none;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2em;
            }}

            .card {{
                width: 280px;
            }}

            .header {{
                padding: 20px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ClickHouse Theater</h1>
        <div class="search-container">
            <input type="text" id="search" placeholder="Search presentations..." autocomplete="off">
        </div>
        <div class="links">
            <a href="https://github.com/ClickHouse/ClickHouse">Source code</a>
            <a href="https://github.com/ClickHouse/clickhouse-presentations">All presentations</a>
        </div>
    </div>

    <div class="container">
        <div class="grid" id="grid">
            {chr(10).join(cards_html)}
        </div>
    </div>

    <script>
        const searchInput = document.getElementById('search');
        const cards = document.querySelectorAll('.card');
        const countEl = document.getElementById('count');
        const total = cards.length;

        searchInput.addEventListener('input', function() {{
            const query = this.value.toLowerCase().trim();
            let visible = 0;

            cards.forEach(card => {{
                const title = card.getAttribute('data-title');
                const matches = !query || title.includes(query);
                card.classList.toggle('hidden', !matches);
                if (matches) visible++;
            }});

            if (query) {{
                countEl.textContent = `Showing ${{visible}} of ${{total}} presentations`;
            }} else {{
                countEl.textContent = `Showing all ${{total}} presentations`;
            }}
        }});

        // Focus search on key press
        document.addEventListener('keydown', function(e) {{
            if (e.key === '/' && document.activeElement !== searchInput) {{
                e.preventDefault();
                searchInput.focus();
            }}
            if (e.key === 'Escape') {{
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
                searchInput.blur();
            }}
        }});
    </script>
</body>
</html>
'''
    return html

def main():
    print("Finding presentations...")
    presentations = find_presentations()
    print(f"Found {len(presentations)} presentations")

    print("Generating HTML...")
    html = generate_html(presentations)

    output_path = os.path.join(BASE_DIR, "index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Created {output_path}")

if __name__ == '__main__':
    main()
