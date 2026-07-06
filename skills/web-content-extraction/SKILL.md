---
name: web-content-extraction
category: research
trigger: User asks to extract, scrape, or convert web page content to Markdown. Includes WeChat articles, blog posts, documentation pages, or any HTML-to-Markdown conversion where preserving formatting and images matters.
description: Extract HTML page content and convert to clean Markdown, preserving headings, images, lists, bold/italic text, tables, and blockquotes.
---

# Web Content Extraction

Extract HTML page content and convert to clean Markdown, preserving headings, images, lists, bold/italic text, tables, and blockquotes.

## Prerequisites

- `beautifulsoup4` — install with pip: `pip install beautifulsoup4`
- **Do NOT use `execute_code`** for this — the sandbox lacks conda packages. Use `terminal` with conda activation instead.

## Workflow

### 1. Download the page

```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "URL" > /tmp/page.html
```

### 2. Identify the content area

Inspect the HTML to find the main content container:
- WeChat articles: `id="js_content"`
- Standard blogs: `class="post-content"`, `id="main-content"`, or `<article>` tag
- Use `grep -o 'id="[^"]*"' /tmp/page.html | sort -u` to discover IDs

### 3. Extract and convert with Python

Use a depth-first walk collecting leaf-level content blocks:

```python
from bs4 import BeautifulSoup, NavigableString
import re

with open('/tmp/page.html', 'r') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
content = soup.find(id='js_content')  # adjust selector per site

blocks = []

def walk(el):
    if isinstance(el, NavigableString):
        t = str(el).strip()
        if t:
            blocks.append(('text', t))
        return
    if not hasattr(el, 'name') or el.name is None:
        return
    tag = el.name

    if tag == 'img':
        src = el.get('data-src') or el.get('src') or ''
        alt = el.get('alt', '')
        if src:
            blocks.append(('image', src, alt))
        return

    if tag == 'section':
        # Background images
        style = el.get('style', '')
        bg = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
        if bg and ('mmbiz' in bg.group(1) or 'wx' in bg.group(1)):
            blocks.append(('image', bg.group(1), ''))
        # Child images
        imgs = el.find_all('img')
        if imgs:
            for img in imgs:
                src = img.get('data-src') or img.get('src') or ''
                if src:
                    blocks.append(('image', src, img.get('alt', '')))
            return
        # Heading detection by style
        has_bold = 'font-weight: bold' in style
        has_big = any(f'font-size: {s}px' in style for s in ['16','17','18','20','22','24'])
        text = el.get_text(strip=True)
        if (has_bold or has_big) and len(text) < 150:
            level = 2 if any(f'font-size: {s}px' in style for s in ['18','20','22','24']) else 3
            blocks.append(('heading', text, level))
            return
        for child in el.children:
            walk(child)
        return

    if tag in ['h1','h2','h3','h4','h5','h6']:
        text = el.get_text(strip=True)
        if text:
            blocks.append(('heading', text, int(tag[1])))
        return

    if tag == 'p':
        text = get_inline(el).strip()
        if text:
            blocks.append(('text', text))
        return

    if tag in ['strong', 'b']:
        text = el.get_text(strip=True)
        if text:
            blocks.append(('text', f'**{text}**'))
        return

    if tag in ['em', 'i']:
        text = el.get_text(strip=True)
        if text:
            blocks.append(('text', f'*{text}*'))
        return

    if tag == 'span':
        style = el.get('style', '')
        text = get_inline(el).strip()
        if text:
            if 'font-weight: bold' in style:
                blocks.append(('text', f'**{text}**'))
            else:
                blocks.append(('text', text))
        return

    if tag in ['ul', 'ol']:
        items = []
        for i, li in enumerate(el.find_all('li', recursive=False)):
            prefix = f"{i+1}." if tag == 'ol' else "-"
            t = get_inline(li).strip()
            if t:
                items.append(f"{prefix} {t}")
        if items:
            blocks.append(('list', '\n'.join(items)))
        return

    if tag == 'li':
        text = get_inline(el).strip()
        if text:
            blocks.append(('text', text))
        return

    if tag == 'blockquote':
        text = get_inline(el).strip()
        if text:
            quoted = '\n'.join(f'> {l}' for l in text.split('\n'))
            blocks.append(('blockquote', quoted))
        return

    if tag == 'table':
        text = extract_table(el)
        if text:
            blocks.append(('table', text))
        return

    for child in el.children:
        walk(child)

def get_inline(el):
    parts = []
    for child in el.children:
        if isinstance(child, NavigableString):
            t = str(child)
            if t.strip():
                parts.append(t)
            continue
        if not hasattr(child, 'name') or child.name is None:
            continue
        if child.name == 'img':
            continue
        if child.name == 'br':
            parts.append(' ')
            continue
        if child.name in ['strong', 'b']:
            t = child.get_text(strip=True)
            if t:
                parts.append(f'**{t}**')
        elif child.name in ['em', 'i']:
            t = child.get_text(strip=True)
            if t:
                parts.append(f'*{t}*')
        elif child.name == 'span':
            inner = get_inline(child).strip()
            if inner:
                parts.append(inner)
        else:
            inner = get_inline(child)
            if inner.strip():
                parts.append(inner)
    return ''.join(parts)

def extract_table(el):
    rows = []
    for tr in el.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if cells:
            rows.append(cells)
    if not rows:
        return ''
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append('')
    lines = ['| ' + ' | '.join(rows[0]) + ' |']
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    for r in rows[1:]:
        lines.append('| ' + ' | '.join(r) + ' |')
    return '\n'.join(lines)

walk(content)

# Convert blocks to markdown
lines = []
for block in blocks:
    if block[0] == 'text':
        lines.append(block[1])
    elif block[0] == 'image':
        lines.append(f'![{block[2]}]({block[1]})')
    elif block[0] == 'heading':
        lines.append(f'{"#" * block[2]} {block[1]}')
    elif block[0] == 'list':
        lines.append(block[1])
    elif block[0] == 'blockquote':
        lines.append(block[1])
    elif block[0] == 'table':
        lines.append(block[1])

# Add spacing between block types
md_parts = []
for i, line in enumerate(lines):
    md_parts.append(line)
    if i < len(lines) - 1:
        curr, nxt = blocks[i][0], blocks[i+1][0]
        if curr != nxt or curr in ('heading', 'image', 'list', 'blockquote', 'table'):
            md_parts.append('')

md = '\n'.join(md_parts)
md = re.sub(r'\n{4,}', '\n\n\n', md).strip()
print(md)
```

### 4. Post-processing

- Remove JS artifacts with regex cleanup
- Reconstruct flat table data into proper Markdown tables when tables rendered as text
- Verify image count matches expected from page

## Pitfalls

- **execute_code sandbox lacks packages**: beautifulsoup4 is NOT available in the execute_code sandbox. Always use `terminal` with conda activation.
- **WeChat captcha**: mp.weixin.qq.com may trigger captcha in browser. Use `curl` with standard User-Agent.
- **Deeply nested sections**: WeChat articles use deeply nested `<section>` elements. Walk depth-first collecting leaf blocks rather than mapping section hierarchy to headings.
- **Heading detection**: WeChat uses inline styles (font-size, font-weight) not `<h1>`-`<h6>` tags. Check style attributes.
- **CSS background images**: Some images use `background-image: url(...)` instead of `<img>` tags. Check section styles for `url()` patterns.
- **Tables as flat text**: Complex tables may render as flat text blocks. Identify repeating groups and reconstruct as Markdown tables.
