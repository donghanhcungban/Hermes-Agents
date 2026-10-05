---
name: figma
description: "Inspect Figma design files, extract tokens/assets, and convert frames to HTML/CSS/Tailwind."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [figma, design, ui, tailwind, css, tokens, frontend, layout]
    related_skills: [frontend-design, frontend-ui-engineering, claude-design]
---

# Figma Skill

Inspect Figma files, extract design tokens and media assets, and transform design frames into clean, responsive, production-ready HTML/Tailwind CSS or React components.

---

## 1. Authentication & Prerequisites

Figma REST API requires a Personal Access Token or OAuth2 Token.

1. **Environment Variable**: Set `FIGMA_ACCESS_TOKEN` (or `FIGMA_TOKEN`) in environment or shell:
   ```bash
   export FIGMA_ACCESS_TOKEN="figd_..."
   ```
2. **HTTP Header**: All REST requests use header `X-Figma-Token: <token>`.

---

## 2. Parsing Figma Links

Figma file URLs typically follow one of these formats:
- `https://www.figma.com/design/:file_key/:file_title?node-id=1-23`
- `https://www.figma.com/file/:file_key/:file_title?node-id=1%3A23`

### Extraction Rules:
- **File Key**: The hash string after `/design/` or `/file/`.
- **Node ID**: From query param `node-id`. Convert hyphens `-` or URL encoding `%3A` to colons `:` (e.g. `1-23` -> `1:23`).

---

## 3. Core REST API Endpoints

| Purpose | Method | Endpoint |
|---|---|---|
| **Get Entire File** | `GET` | `https://api.figma.com/v1/files/:file_key` |
| **Get Specific Nodes** | `GET` | `https://api.figma.com/v1/files/:file_key/nodes?ids=:node_id` |
| **Export Image/SVG** | `GET` | `https://api.figma.com/v1/images/:file_key?ids=:node_id&format=svg|png&scale=2` |
| **Get Variables/Tokens** | `GET` | `https://api.figma.com/v1/files/:file_key/variables/local` |
| **Get File Styles** | `GET` | `https://api.figma.com/v1/files/:file_key/styles` |

---

## 4. Helper Tool: `figma_cli.py`

Use the included helper script to extract simplified, clean JSON hierarchy from Figma nodes:

```bash
python scripts/figma_cli.py "<figma_url_or_file_key>" [node_id] [output_file.json]
```

### Output Data Structure:
`figma_cli.py` reduces verbose Figma API payloads into actionable layout structures:
- `layoutMode`: `HORIZONTAL` or `VERTICAL` (Auto Layout)
- `itemSpacing`: Gap between children in px
- `padding`: `{ top, right, bottom, left }`
- `fills` / `strokes`: Clean HEX or RGBA colors
- `cornerRadius`: Border radius in px
- `font`: Font family, weight, size, line-height, letter-spacing, alignment

---

## 5. Auto-Layout to Tailwind CSS Mapping

When converting Figma frames to Tailwind CSS, follow these exact mappings:

### Flex Directions & Layout Mode
- `layoutMode: HORIZONTAL` $\rightarrow$ `flex flex-row`
- `layoutMode: VERTICAL` $\rightarrow$ `flex flex-col`

### Alignment (Primary Axis)
- `primaryAxisAlignItems: MIN` $\rightarrow$ `justify-start`
- `primaryAxisAlignItems: CENTER` $\rightarrow$ `justify-center`
- `primaryAxisAlignItems: MAX` $\rightarrow$ `justify-end`
- `primaryAxisAlignItems: SPACE_BETWEEN` $\rightarrow$ `justify-between`

### Alignment (Counter Axis)
- `counterAxisAlignItems: MIN` $\rightarrow$ `items-start`
- `counterAxisAlignItems: CENTER` $\rightarrow$ `items-center`
- `counterAxisAlignItems: MAX` $\rightarrow$ `items-end`
- `counterAxisAlignItems: BASELINE` $\rightarrow$ `items-baseline`

### Spacing & Padding
- `itemSpacing: 16` $\rightarrow$ `gap-4` (or `gap-[16px]`)
- `paddingTop/Right/Bottom/Left` $\rightarrow$ `pt-[Npx] pr-[Npx] pb-[Npx] pl-[Npx]` or `px-X py-Y`

### Sizing Constraints
- `layoutSizingHorizontal: FIXED` $\rightarrow$ `w-[Wpx]` (or fixed width)
- `layoutSizingHorizontal: HUG` $\rightarrow$ `w-fit`
- `layoutSizingHorizontal: FILL` $\rightarrow$ `w-full` / `flex-1`

### Colors & Appearance
- Solid Fill (`color: {r, g, b, a}`) $\rightarrow$ `bg-[#RRGGBB]` or `bg-[#RRGGBBAA]`
- Stroke $\rightarrow$ `border border-[Npx] border-[#HEX]`
- `cornerRadius` $\rightarrow$ `rounded-[Npx]` (or `rounded-lg`, `rounded-full`)

---

## 6. Asset Export Workflow (Icons & Images)

1. Identify vector nodes (`VECTOR`, `BOOLEAN_OPERATION`, `STAR`, `LINE`, `ELLIPSE`, `INSTANCE` for icons) or image fill nodes.
2. Request export URLs via API:
   ```bash
   curl -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
     "https://api.figma.com/v1/images/:file_key?ids=:node_id&format=svg"
   ```
3. Fetch the returned SVG/PNG URL and save it into project assets directory (e.g. `assets/icon-arrow.svg`).
4. Inline or reference the SVG asset directly in HTML/React code.

---

## 7. Step-by-Step Conversion Pipeline

When asked to build or convert a design from Figma:

1. **Parse & Verify**: Extract `file_key` and `node_id`. Confirm `FIGMA_ACCESS_TOKEN` is available.
2. **Inspect Hierarchy**: Run `figma_cli.py` to extract node structure or query node API directly.
3. **Download Assets**: Export all icons as SVG and raster images as WebP/PNG.
4. **Identify Component Boundaries**: Break down complex frames into modular, reusable UI components (e.g., Header, Card, Button, Navbar).
5. **Generate Markup**: Write clean, semantic HTML/JSX using Tailwind CSS utility classes based on the Auto-Layout parameters.
6. **Verify Visual Fidelity**: Render/preview the generated UI and compare layout, spacing, colors, and typography against Figma specifications.

---

## 8. Best Practices & Quality Standards

- **Never Hardcode Absolute Positioning**: If Figma node uses Auto Layout (`HORIZONTAL` or `VERTICAL`), convert to standard CSS Flexbox/Grid rather than `absolute top-X left-Y`.
- **Semantic HTML**: Map Figma frames to semantic tags (`<header>`, `<nav>`, `<main>`, `<article>`, `<button>`, `<input>`) instead of flat `<div>` stacks.
- **Responsive Layout**: Adjust fixed pixel dimensions to responsive classes (`w-full`, `max-w-7xl`, `md:flex-row`) where appropriate.
- **Accessibility**: Ensure sufficient text contrast ratio and add proper `alt` tags on image assets exported from Figma.
