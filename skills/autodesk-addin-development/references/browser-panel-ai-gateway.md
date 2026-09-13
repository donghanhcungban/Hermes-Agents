# Browser Panel + AI Gateway for Autodesk Bridges

Use this pattern when a local HTML control panel must communicate with a Revit/AutoCAD `HttpListener` bridge and a real AI provider.

## Proven architecture

```text
file:// panel
  → http://127.0.0.1:8767 (stdlib ThreadingHTTPServer sidecar, CORS enabled)
      → http://localhost:8766 (AutoCAD bridge)
      → Hermes/model CLI for AI planning and summarization
```

The panel uses only the sidecar base URL. The sidecar proxies `/health`, `/query`, and `/execute`; `/ai/chat` invokes the configured model.

## Critical hostname detail

Keep bridge upstream URLs exactly aligned with the registered `HttpListener` prefix. In the validated AutoCAD case:

- `http://localhost:8766` worked.
- `http://127.0.0.1:8766` returned HTTP 400.
- The panel-facing sidecar could still bind to `127.0.0.1`.

Do not infer bridge failure from the browser UI alone. Probe the bridge with MCP/Python first.

## AI boundary

Use a two-stage read-only flow:

1. Ask the model for strict JSON such as `{"reply":"...","query":{"type":"stats","limit":50}}`.
2. Parse the JSON defensively; allowlist query types and clamp limits.
3. Run the selected bridge query deterministically.
4. Send the exact result to the model for a concise explanation.

Do not let model text become an arbitrary command. Writes should remain in dedicated UI tabs with explicit confirmation and DryRun by default.

## Sidecar lifecycle

At MCP server startup:

1. Probe `http://127.0.0.1:<panel-port>/health` with a short timeout.
2. If healthy, do nothing.
3. Otherwise spawn the sidecar detached with the same Python interpreter, no inherited stdin, and hidden/no-window flags on Windows.

This is idempotent and survives reopening the panel.

## Verification checklist

- Compile/lint both MCP and sidecar code.
- Parse the panel JavaScript (for standalone HTML, extract `<script>` and pass it to `new Function(...)`).
- `GET sidecar/health` returns the live Autodesk app and bridge port.
- `POST sidecar/query` returns real drawing/model data.
- `POST sidecar/ai/chat` with a connection question reports actual health.
- Ask AI for a statistic and verify its numbers equal the raw query result.
- Reload the `file://` panel and confirm its status indicator changes to connected.
- Stop the sidecar, import/start the MCP server, and confirm the sidecar is recreated automatically.
