---
name: chinese-content-extraction
description: Extract content from Chinese platforms (WeChat articles, Zhihu, etc.) with full text, images, and formatting preserved as Markdown.
trigger: User provides a WeChat (mp.weixin.qq.com) or Zhihu (zhuanlan.zhihu.com) URL and asks to extract content, preserve images, or convert to Markdown.
---

# Chinese Content Extraction

## WeChat Articles (mp.weixin.qq.com)

WeChat articles are the most reliable Chinese platform to extract. The content is fully present in the initial HTML response.

### Workflow

1. **Download HTML via curl**:
   ```bash
   curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "https://mp.weixin.qq.com/s/<ARTICLE_ID>" > /tmp/wechat_article.html
   ```

2. **Extract title**:
   ```python
   import re, html as html_mod
   title_match = re.search(r'var msg_title = ["\']([^"\']+)["\']', content)
   title = html_mod.unescape(title_match.group(1)) if title_match else 'Unknown'
   ```

3. **Find content anchor**: Search for `id="js_content"` — this is the div containing all article body content.

4. **Parse with BeautifulSoup**:
   - Walk the tree depth-first, collecting text blocks, images, and headings in document order
   - WeChat uses `<section>` tags heavily for layout — detect headings by checking for `font-weight: bold`, large `font-size`, or `title` in class names
   - Images are in `<img>` tags with `data-src` attributes; some sections have background images via `url()` in style
   - Build a flat ordered list of blocks: `('text', content)`, `('image', src, alt)`, `('heading', text, level)`

5. **Convert to Markdown**:
   - Text → plain text
   - Images → `![alt](src)`
   - Headings → `#`, `##`, `###` based on font size
   - Lists → `- item` or `1. item`
   - Blockquotes → `> text`

### Key Pitfalls

- **Image placement**: WeChat often puts images inline with text, not as separate paragraphs. Walk the tree in document order and interleave images at their exact positions.
- **Background images**: Some sections use `background-image: url(...)` in their style attribute — extract these as separate images.
- **Comparison tables**: WeChat often renders comparison tables as multiple child sections side-by-side. Detect these by checking if a section has 2+ child sections with short text — convert to Markdown tables.
- **JS artifacts**: The HTML ends with inline JavaScript (`var first_sceen__time...`) and UI text (`预览时标签不可点`). Strip these from the output.
- **Captcha**: WeChat may show a captcha page if accessed from certain IPs. If `id="js_content"` is not found, the page is likely blocked.

### Zhihu (zhuanlan.zhihu.com)

**Zhihu has aggressive anti-bot protection (code 40362) that blocks:**
- curl requests (returns zse-ck challenge page)
- Browser automation (returns JSON error)
- API calls (requires authenticated session + specific headers)
- Third-party proxy services (12ft.io, etc.)

**Workarounds (limited success):**
- Try mobile user-agent (usually still blocked)
- Try `api.zhihu.com` endpoint (requires valid cookies)
- **Most reliable**: Ask user to copy-paste content or use Zhihu app's share-to-image feature

**Do NOT waste time** trying to bypass Zhihu's anti-bot with curl, browser, or API — it consistently returns 403 errors across all methods.

## General Tips for Chinese Platforms

- Always use a realistic Chinese browser User-Agent
- Set `Accept-Language: zh-CN,zh;q=0.9`
- Use `terminal` for curl, not `execute_code` (sandbox lacks packages)
- Install `beautifulsoup4` in conda environment if needed: `pip install beautifulsoup4`
- For WeChat: the full article content is in the initial HTML response, no JS rendering needed
- For Zhihu: content requires JS rendering + authentication — extremely difficult to extract programmatically

## Reusable Script

A ready-to-use extraction script is available at `scripts/extract_wechat.py`. Usage:
```bash
python3 scripts/extract_wechat.py /tmp/wechat_article.html > output.md
```
