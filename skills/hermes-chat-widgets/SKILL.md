---
name: hermes-chat-widgets
description: "Build inline HTML widgets in Hermes chat via ::preview{}."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [hermes, widgets, html, interactive, sqlite, token-stats]
    related_skills: [hermes-agent, claude-design]
---

# Hermes In-Chat HTML Widgets

Build live, interactive HTML panels that render **directly inside** the Hermes chat pane. Unlike the preview pane (`desktop_preview`), the `::preview{file="..."}` directive embeds the widget inline in the assistant turn — no separate tab.

## The `::preview{}` Directive

Place on its own line at the end of an assistant turn:

```
::preview{file="C:\\Users\\liend\\my_widget.html"}
```

Rules:
- Must be on its **own line** — no surrounding text on the same line
- Path must be **absolute**
- Rendered in a sandboxed iframe inside the chat message
- The frame auto-themes: app CSS vars + app font are injected before your styles
- Height auto-sizes to content; width follows content's natural first span
- Navigation in chat does NOT destroy the widget (it re-renders on scroll-back)

## CSS Theme Variables (injected automatically)

| Variable | Semantic use |
|----------|--------------|
| `var(--foreground)` | Primary text |
| `var(--muted-foreground)` | Secondary / dimmed text |
| `var(--accent)` | Brand accent colour |
| `var(--border)` | Borders / dividers |
| `var(--card)` | Card / surface background |

**Do NOT** set `background`, `font-family`, or `margin` on `body` — they override the injected theme and break dark/light switching.

For subtle accent fills: `color-mix(in srgb, var(--accent) 8%, transparent)`

## Widget Interaction: `data-hermes-send`

Add `data-hermes-send="prompt text"` to any clickable element. When the user clicks it, Hermes sends that string as a hidden user turn — the agent regenerates the widget with fresh data.

```html
<button data-hermes-send="cập nhật thống kê token">↻ Cập nhật</button>
```

Also available programmatically from widget JS: `window.hermes.send("prompt")`

## Data Embedding Pattern (RECOMMENDED)

**Embed data as a JSON literal in a `<script>` block** rather than `fetch()`. The iframe sandbox context can make relative fetches unreliable.

```python
# In execute_code: read data, serialise, inject into HTML template
import json, os

data = { ... }  # your data dict
data_json = json.dumps(data, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html><head>...</head><body>
...
<script>
const DATA = {data_json};
render(DATA);
</script></body></html>"""

workspace = os.environ.get('BH_AGENT_WORKSPACE', r'C:\Users\liend')
out_path = os.path.join(workspace, 'my_widget.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
```

Then in the assistant reply:
```
::preview{file="C:\\Users\\liend\\my_widget.html"}
```

## Reading Hermes state.db

Hermes stores all session + token + cost data in SQLite:

| Platform | Path |
|----------|------|
| Windows | `C:\Users\<user>\AppData\Local\hermes\state.db` |
| Linux | `~/.local/share/hermes/state.db` |
| macOS | `~/Library/Application Support/hermes/state.db` |

From `execute_code`, resolve with:
```python
from hermes_constants import get_hermes_home
db_path = get_hermes_home() / 'state.db'
```

Key tables: **`sessions`** (one row per chat, includes token + cost columns), **`session_model_usage`** (per-model breakdown within a session), **`messages`** (full message log). See `references/hermes-state-db.md` for full column lists and sample queries.

## Widget Layout Rules

- Set `min-width` on the root container (e.g. `420px`) — the frame measures from content span
- Use `var(--card)` for panel backgrounds, `var(--border)` for dividers
- Scrollable sub-sections: `max-height` + `overflow-y: auto` with slim custom scrollbar (`width: 4px`)
- `font-variant-numeric: tabular-nums` on numeric cells for clean column alignment
- CSS Grid (2 or 4 equal columns) works well for summary stat cards
- For active/live indicators: small dot (`border-radius: 50%`) with CSS `@keyframes pulse` opacity animation

## Common Widget Patterns

### Summary card grid
```html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border)">
  <div style="background:var(--card);padding:9px 14px">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-foreground)">Label</div>
    <div style="font-size:19px;font-weight:700;color:var(--accent)">$12.18</div>
    <div style="font-size:11px;color:var(--muted-foreground)">sub text</div>
  </div>
</div>
```

### Proportional token bar
```html
<div style="height:8px;border-radius:4px;background:var(--border);overflow:hidden;display:flex">
  <div style="background:#3b82f6;width:5%"></div>   <!-- input -->
  <div style="background:#10b981;width:10%"></div>  <!-- output -->
  <div style="background:#f59e0b;width:85%"></div>  <!-- cache read -->
</div>
```

## Pitfalls

- **`::preview{}` not on its own line** — renders as raw text; must have nothing else on the same line
- **`fetch()` with relative paths** — use embedded JSON instead; fetch to absolute `file://` paths may also fail in sandboxed iframes
- **Setting `body { background: ... }`** — kills theme; leave body background transparent
- **Centering root with `margin: auto`** — breaks the iframe's width measurement; lay content flush left
- **Windows paths in the directive** — use `\\` (escaped backslashes) or `/` forward slashes
- **`data-hermes-send` state across re-renders** — the iframe is recreated on each widget update; don't rely on JS state surviving a refresh button click
