#!/usr/bin/env python3
"""
WeChat Article to Markdown Extractor
Extracts text, images, headings, and lists from WeChat articles (mp.weixin.qq.com)
"""

from bs4 import BeautifulSoup, NavigableString
import re
import html as html_mod

def extract_wechat_article(html_content):
    """Extract WeChat article content to Markdown."""
    
    # Extract title
    title_match = re.search(r'var msg_title = ["\']([^"\']+)["\']', html_content)
    title = html_mod.unescape(title_match.group(1)) if title_match else 'Unknown'
    
    # Find content area
    start_idx = html_content.find('id="js_content"')
    tag_start = html_content.rfind('<', 0, html_content.find('>', start_idx))
    
    # Find end boundary
    end_patterns = ['id="js_pc_qr_code"', 'id="js_tpl_container', 'class="rich_media_tool"']
    best_end = len(html_content)
    for p in end_patterns:
        idx = html_content.find(p, start_idx + 1000)
        if idx != -1 and idx < best_end:
            best_end = idx
    
    article_html = html_content[tag_start:best_end]
    soup = BeautifulSoup(article_html, 'html.parser')
    
    # Collect all images first for ordering
    all_images = []
    for img in soup.find_all('img'):
        src = img.get('data-src') or img.get('src') or img.get('data-original', '')
        alt = img.get('alt', '') or img.get('data-original-alt', '')
        if src:
            all_images.append((src, alt))
    
    # Walk tree and collect blocks
    img_idx = [0]
    blocks = []
    
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
            tag = child.name
            if tag == 'img':
                if img_idx[0] < len(all_images):
                    src, alt = all_images[img_idx[0]]
                    img_idx[0] += 1
                    parts.append(f'![{alt}]({src})')
                continue
            if tag == 'br':
                parts.append(' ')
                continue
            if tag in ['strong', 'b']:
                t = child.get_text(strip=True)
                if t:
                    parts.append(f'**{t}**')
            elif tag in ['em', 'i']:
                t = child.get_text(strip=True)
                if t:
                    parts.append(f'*{t}*')
            elif tag == 'span':
                style = child.get('style', '')
                inner = get_inline(child).strip()
                if inner:
                    if 'font-weight: bold' in style or 'font-weight:bold' in style:
                        parts.append(f'**{inner}**')
                    else:
                        parts.append(inner)
            elif tag == 'a':
                href = child.get('href', '')
                inner = get_inline(child).strip()
                if inner:
                    parts.append(f'[{inner}]({href})')
            else:
                inner = get_inline(child)
                if inner.strip():
                    parts.append(inner)
        return ''.join(parts)
    
    def walk(el):
        if isinstance(el, NavigableString):
            text = str(el).strip()
            if text:
                blocks.append(('text', text))
            return
        if not hasattr(el, 'name') or el.name is None:
            return
        
        tag = el.name
        
        if tag == 'img':
            if img_idx[0] < len(all_images):
                src, alt = all_images[img_idx[0]]
                img_idx[0] += 1
                blocks.append(('image', f'![{alt}]({src})'))
            return
        
        if tag == 'br':
            blocks.append(('br',))
            return
        
        if tag == 'section':
            # Check for background images
            style = el.get('style', '')
            bg_m = re.search(r'url\(["\']?([^"\'()]+)["\']?\)', style)
            if bg_m:
                bg_url = bg_m.group(1)
                if bg_url and ('mmbiz' in bg_url or 'wx' in bg_url):
                    blocks.append(('image', f'![]({bg_url})'))
            
            # Check for heading
            text = el.get_text(strip=True)
            clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', text).strip()
            
            if len(clean_text) > 1 and len(clean_text) < 200:
                has_bold = 'font-weight: bold' in style or 'font-weight:bold' in style
                has_big = any(f'font-size: {s}px' in style for s in ['16','17','18','20','22','24','26'])
                classes = el.get('class', [])
                has_title = any('title' in c.lower() for c in classes)
                has_data_title = 'title' in el.get('data-type', '').lower() if el.get('data-type') else False
                if has_bold or has_big or has_title or has_data_title:
                    level = 3
                    if any(f'font-size: {s}px' in style for s in ['20','22','24','26','28']):
                        level = 2
                    blocks.append(('heading', f'{"#" * level} {clean_text}'))
                    return
            
            for child in el.children:
                walk(child)
            return
        
        if tag in ['h1','h2','h3','h4','h5','h6']:
            text = el.get_text(strip=True)
            if text:
                blocks.append(('heading', f'{"#" * int(tag[1])} {text}'))
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
                if 'font-weight: bold' in style or 'font-weight:bold' in style:
                    blocks.append(('text', f'**{text}**'))
                else:
                    blocks.append(('text', text))
            return
        
        if tag in ['ul', 'ol']:
            items = []
            for li in el.find_all('li', recursive=False):
                text = get_inline(li).strip()
                if text:
                    items.append(f"- {text}")
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
                blocks.append(('blockquote', text))
            return
        
        if tag == 'a':
            href = el.get('href', '')
            text = get_inline(el).strip()
            if text:
                blocks.append(('text', f'[{text}]({href})'))
            return
        
        for child in el.children:
            walk(child)
    
    walk(soup)
    
    # Convert to markdown
    output = []
    for i, (etype, text) in enumerate(blocks):
        output.append(text)
        if i < len(blocks) - 1:
            next_type = blocks[i+1][0]
            if etype != next_type or etype in ('heading', 'image', 'list', 'blockquote'):
                output.append('')
    
    md = '\n'.join(output)
    md = re.sub(r'\n{4,}', '\n\n\n', md)
    md = md.strip()
    
    final_md = f"# {title}\n\n{md}"
    
    # Remove JS artifacts
    final_md = re.sub(r'\n\s*var first_sceen.*', '', final_md, flags=re.DOTALL)
    final_md = final_md.replace('预览时标签不可点', '').strip()
    
    return final_md


if __name__ == '__main__':
    import sys
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        html = f.read()
    print(extract_wechat_article(html))
