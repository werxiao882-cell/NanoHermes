---
name: article-extraction
description: Extract web article content from WeChat MP, blogs, and other platforms, converting text, images, formatting, and tables to clean Markdown.
trigger: User asks to extract content from a web article/blog/WeChat MP/Zhihu post and convert to markdown
---

# Article Extraction

Extract web article content (text, images, formatting, tables) and convert to clean Markdown.

## Workflow

### Step 1: Try curl first
```bash
curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "URL" > /tmp/article.html
```
- If content > 50KB, good — proceed to parsing
- If content < 1KB or shows captcha/error, the site blocks bots (see Pitfalls)

### Step 2: Identify content container
Key selectors by platform:
- **WeChat MP** (`mp.weixin.qq.com`): `id="js_content"` — contains all article HTML
- **Generic blog**: Look for `<article>`, `.post-content`, `.entry-content`, `.rich_media_content`

### Step 3: Parse with BeautifulSoup (conda py312)
Use `terminal` with conda environment (not `execute_code` sandbox):
```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312 && pip install beautifulsoup4 -q
```

Parsing strategy for WeChat MP (most common):
1. Extract title from `var msg_title = "..."` in page JS
2. Find `id="js_content"` div, extract HTML between it and end markers (`id="js_pc_qr_code"`, `id="js_tpl_container"`)
3. Walk the tree depth-first collecting blocks:
   - `img` tags → `![alt](src)`
   - `section` with `font-weight: bold` or large `font-size` → heading
   - `strong`/`b` → `**text**`
   - Text nodes → plain text
4. Convert detected comparison/capability tables to Markdown pipe tables
5. Clean up JS artifacts, excessive newlines

### Step 4: Output and save
- Save to `~/article-name.md`
- Display full markdown to user
- Report stats: image count, heading count, character count

## Pitfalls

### Zhihu (zhuanlan.zhihu.com) — BLOCKED
Zhihu has aggressive anti-bot that blocks ALL automated access:
- curl → returns 584-byte anti-bot challenge page (no initialData)
- browser_navigate → JSON error `{"error":{"code":40362}}`
- API (`/api/v4/articles/ID`) → 403 with `code:10003`
- Search engine caches → also blocked
- Third-party extractors → return empty

**Workaround**: Ask user to copy-paste the article content, or find a repost/mirror on another platform.

### WeChat MP captcha
Browser navigation triggers captcha. Use curl instead — it bypasses the captcha and gets the full HTML.

### Images in WeChat articles
WeChat wraps images in complex `<section>` → `<span>` → `<figure>` → `<img>` chains. Must:
- Search all `<img>` tags for `data-src` (primary) then `src` (fallback)
- Also check `<section>` style for `background-image: url(...)`
- Deduplicate by URL

### execute_code sandbox limitations
- The `execute_code` sandbox does NOT have conda packages installed. Always use `terminal` with the conda activation command for any Python script requiring bs4, requests, etc.
- **Never use triple-quoted strings (`"""` or `'''`) in execute_code** — they break at the script boundary due to how the sandbox processes the code. Use a list of single-quoted strings instead: `lines = ["line1", "line2"]; f.write('\n'.join(lines))`
- When writing large content blocks to files, prefer writing to a temp file first, then using `cat >> target` to append

### Image placement in WeChat articles
WeChat HTML often groups all `<img>` tags at the top of the content div, but they render inline in the actual article. Use a **two-pass approach**:
1. First pass: collect all image URLs in document order into a list
2. Second pass: walk the tree collecting text blocks; when you hit an `<img>` tag, pop the next image from the list
This ensures images appear at their correct semantic positions in the output Markdown.

### Table reconstruction
WeChat articles often render tables as flat sequences of div/section elements. Detect these patterns (repeated label-value pairs) and reconstruct as proper Markdown tables.

## Resources
- `references/verl-agentic-rl-analysis.md` — Detailed analysis of VeRL source code architecture, state machine implementation, and Agentic RL training pipeline
- `references/inline-svg-diagrams.md` — Generate inline SVG diagrams as Base64 data URIs for embedding illustrations directly in Markdown documents (no external hosting needed)
