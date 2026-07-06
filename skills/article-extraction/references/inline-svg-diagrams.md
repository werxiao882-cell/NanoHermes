# Inline Diagram Generation for Markdown Documents

When users ask to add diagrams/illustrations to markdown documents, use this technique to generate inline SVG images that work everywhere (no external hosting needed).

## Technique: SVG → Base64 Data URI

1. Write SVG content as a string in Python
2. Base64 encode it
3. Use as `![alt](data:image/svg+xml;base64,...)` in Markdown

```python
import base64

svg = '''<svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="10" width="580" height="180" fill="#f0f8ff" stroke="#4682b4" stroke-width="3" rx="10"/>
  <text x="300" y="35" font-family="Arial" font-size="16" fill="navy" text-anchor="middle" font-weight="bold">Title</text>
  <!-- Add shapes, arrows, text boxes -->
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="black" />
    </marker>
  </defs>
</svg>'''

b64 = "data:image/svg+xml;base64," + base64.b64encode(svg.encode('utf-8')).decode('utf-8')
print(f"![Diagram]({b64})")
```

## Common SVG Elements

- `<rect x="..." y="..." width="..." height="..." fill="color" rx="5"/>` — Rounded boxes
- `<line x1="..." y1="..." x2="..." y2="..." stroke="black" stroke-width="2" marker-end="url(#arrow)"/>` — Arrows
- `<text x="..." y="..." text-anchor="middle" font-weight="bold">Label</text>` — Centered text
- `<marker id="arrow" ...>` — Arrowhead definition (reuse with `marker-end`)

## Inserting into Existing Documents

```python
# Read current content
with open('doc.md', 'r') as f:
    content = f.read()

# Insert before a specific section marker
content = content.replace("### Next Section", f"![Diagram]({b64})\n\n### Next Section")

# Write back
with open('doc.md', 'w') as f:
    f.write(content)
```

## Why SVG + Base64?
- **No external dependencies**: Works offline, no image hosting needed
- **Scalable**: Vector graphics, crisp at any zoom level
- **Universal**: Supported by all modern Markdown renderers, WeChat, browsers
- **Self-contained**: Single file, no broken image links