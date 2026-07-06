---
name: wechat-article-extraction
category: research
description: Extract WeChat (mp.weixin.qq.com) articles to Markdown with images, headings, lists, and formatting preserved.
trigger: Extract content from WeChat (微信公众号/mp.weixin.qq.com) articles, convert to Markdown, preserve images and formatting.
---

## Overview

Extract articles from `mp.weixin.qq.com/s/<id>` and convert to clean Markdown with images, headings, lists, and tables preserved.

## Extraction Method

1. **Download HTML via curl** (browser is unreliable due to captcha):
```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "https://mp.weixin.qq.com/s/<article_id>" > /tmp/wechat_article.html
```

2. **Extract article content** using Python + BeautifulSoup (run via `terminal` with conda Python, NOT execute_code sandbox):
   - Locate `id="js_content"` div
   - Walk the DOM tree collecting text nodes, images (`<img>` with `data-src`), and styled `<section>` elements
   - Detect headings via `font-weight: bold` or `font-size: 16px+` inline styles
   - Convert `**bold**`, `*italic*`, lists, blockquotes to Markdown
   - Extract background images from section `style="url(...)"` declarations
   - Preserve image `alt` text as Markdown image alt attributes

3. **Image placement**: Process images in document order — each `<img>` is placed at its natural position relative to surrounding text, NOT batched at the top.

4. **Cleanup**: Remove JavaScript artifacts (`var first_sceen__time`, etc.), stray UI text (`预览时标签不可点`), and excessive blank lines.

## Platform-Specific Notes

- **WeChat (mp.weixin.qq.com)**: ✅ Works reliably via curl + BeautifulSoup. No login needed. Anti-bot is mild (captcha only in browser).
- **Zhihu (zhuanlan.zhihu.com)**: ❌ Fails consistently. Returns 40362 error. API returns code 10003. The `zse-ck` anti-bot blocks all non-browser requests. Workaround: ask user to provide content manually, or search cached/mirrored versions.

## Pitfalls

- **Images lost during extraction**: WeChat wraps images in `<section> > <figure> > <span> > <img>`. Must recurse into sections and handle `<img>` before recursing into text children.
- **Headings missed**: WeChat uses inline styles (`font-weight`, `font-size`) rather than `<h1>`-`<h6>` tags. Must check style attributes, not just tag names.
- **Execute_code sandbox lacks packages**: `bs4` (BeautifulSoup) is NOT available in the execute_code sandbox. Use `terminal` with conda-activated Python instead.
- **f-string backslash error**: Python f-strings cannot contain backslashes in the expression part. Use a variable for regex patterns instead.

## Reference Files

- `references/vocabulary-glossary-guide.md` — How to create plain-language glossaries for technical articles
- `references/hermes-context-explanation-guide.md` — How to explain abstract concepts using the user's own project as analogy
