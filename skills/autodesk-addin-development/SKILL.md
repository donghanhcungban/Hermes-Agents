---
name: autodesk-addin-development
description: "Use when building Revit or AutoCAD C# plugins."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [autodesk, revit, autocad, csharp, addin, bim, plugin]
    related_skills: [evidence-driven-delivery]
---

# Autodesk Add-in Development (Revit + AutoCAD)

**Given:** a task to build, extend, or debug a Revit or AutoCAD C# plugin.
**Produces:** a .NET Framework 4.8 DLL that loads cleanly, dispatches commands thread-safely, and optionally exposes an HTTP Bridge for agent/script control.

## NuGet Packages

| Platform | Package | Notes |
|---|---|---|
| Revit | `Nice3point.Revit.Api.RevitAPI` | Community wrapper, version = `$(RevitVersion).*` |
| Revit | `Nice3point.Revit.Api.RevitAPIUI` | Same pattern |
| AutoCAD | `AutoCAD.NET` | **Official Autodesk** (owner: `Autodesk` on nuget.org), `24.*` = 2024, `26.*` = 2026 |
| Both | `Newtonsoft.Json` `13.0.3` | HTTP Bridge JSON serialization |

Use `Directory.Build.props` at solution root to share `<LangVersion>latest</LangVersion>`, `<Nullable>enable</Nullable>`, `<TargetFramework>net48</TargetFramework>` across all projects.

## .NET 4.8 Language Pitfalls

These C# features look valid but are **NOT available on net48**:

### 1. `String.Contains(string, StringComparison)` — not in net48
```csharp
// ❌ Compiles, fails at runtime on net48
name.Contains("foo", StringComparison.OrdinalIgnoreCase)

// ✅ Use IndexOf instead
name.IndexOf("foo", StringComparison.OrdinalIgnoreCase) >= 0
```
Also affects `.Any(k => x.Contains(k, ...))` chains — replace every occurrence.

### 2. `init` accessor and `required` keyword — need polyfill
Add `Polyfills.cs` to **every** project targeting net48 that uses C# 9+ syntax:

```csharp
#if !NET5_0_OR_GREATER
namespace System.Runtime.CompilerServices
{
    internal static class IsExternalInit { }
}
#endif
```

### 3. AutoCAD namespace collision
`Autodesk.AutoCAD.Runtime` exports its own `Exception` — always qualify:
```csharp
catch (System.Exception ex)   // ✅
catch (Exception ex)           // ❌ CS0104 ambiguous
```

### 4. Target-typed `new()` in object initializers
If you get `CS8400`, replace `new()` with `new List<string>()` etc. explicitly.

## Revit Thread Safety — ExternalEvent Pattern

Revit's API is **strictly single-threaded**. Background threads (e.g. HttpListener) must marshal onto the Revit main thread via `ExternalEvent`.

```csharp
// 1. Implement the handler — runs on Revit main thread
public class BridgeEventHandler : IExternalEventHandler
{
    private readonly ConcurrentQueue<(Request req, TaskCompletionSource<Result> tcs)> _queue = new();

    public void Enqueue(Request req, TaskCompletionSource<Result> tcs)
        => _queue.Enqueue((req, tcs));

    public void Execute(UIApplication app)
    {
        while (_queue.TryDequeue(out var item))
        {
            try   { item.tcs.SetResult(RunCommand(app, item.req)); }
            catch (System.Exception ex) { item.tcs.SetException(ex); }
        }
    }
    public string GetName() => "DhcbBridge";
}

// 2. Register in OnStartup — MUST happen on main thread
var handler = new BridgeEventHandler();
var externalEvent = ExternalEvent.Create(handler);

// 3. From background thread:
var tcs = new TaskCompletionSource<Result>();
handler.Enqueue(request, tcs);
externalEvent.Raise();
var result = await tcs.Task;   // safe to await
```

### UIApplication availability timing
- **`OnStartup(UIControlledApplication)`** — cannot construct `UIApplication` here.
- **`ApplicationInitialized` event** — `UIApplication` is ready. Start the HTTP Bridge here:

```csharp
public Result OnStartup(UIControlledApplication app)
{
    var bridge = new DhcbHttpBridge();
    app.ControlledApplication.ApplicationInitialized += (_, _) => bridge.Start();
    return Result.Succeeded;
}
```

## AutoCAD Thread Safety — ExecuteInCommandContextAsync

```csharp
// From background thread (HttpListener):
var tcs = new TaskCompletionSource<Result>();
await Application.DocumentManager.ExecuteInCommandContextAsync(
    async _ =>
    {
        var db = Application.DocumentManager.MdiActiveDocument.Database;
        using var tr = db.TransactionManager.StartTransaction();
        // ... do work ...
        tr.Commit();
        tcs.SetResult(result);
    },
    null);
return await tcs.Task;
```

## HTTP Bridge Pattern (AI Agent → Desktop App)

Allows agents, scripts, or Hermes to drive a live Revit/AutoCAD session over HTTP.

**Architecture:**
```
Agent / Python script
    POST http://localhost:<port>/execute  {"command": "...", "config": {...}}
    ↓
HttpListener (background thread, always on)
    ↓  marshal via ExternalEvent (Revit) or ExecuteInCommandContextAsync (AutoCAD)
    ↓
Main thread → ICoreCommand.Execute() → CommandResult
    ↓
HTTP response  {"success": true, "summary": "...", "messages": [...]}
```

| App | Port | Marshal mechanism |
|---|---|---|
| Revit | 8765 | `ExternalEvent.Raise()` |
| AutoCAD | 8766 | `ExecuteInCommandContextAsync()` |

**Python client (stdlib only, no deps):**
```python
import json, urllib.request

def send(url, command, config):
    payload = json.dumps({"command": command, "config": config}).encode()
    req = urllib.request.Request(url, data=payload,
          headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read())

result = send("http://localhost:8765/execute", "Cleanup", {"dryRun": True})
```

## HTTP Bridge — /query endpoint (đọc ngữ cảnh)

Ngoài `/execute` (ghi), Bridge còn có `POST /query` và `GET /health`:

| Endpoint | Mô tả |
|---|---|
| `GET /health` | Kiểm tra bridge đang chạy (`{"status":"ok"}`) |
| `POST /execute` | Gửi lệnh ghi vào model |
| `POST /query` | Đọc ngữ cảnh — không mở transaction ghi |

### Revit — các query type
`document_info`, `elements`, `levels`, `views`, `sheets`, `rooms`, `families`, `warnings`, `links`, `stats`

```python
result = send("http://localhost:8765/query", {
    "query": "elements",
    "params": {
        "categories": ["Doors"],
        "parameterNames": ["Mark", "Level"],
        "limit": 100
    }
})
```

### AutoCAD — các query type
`drawing_info`, `layers`, `blocks`, `inserts`, `entities`, `text`, `xrefs`, `layouts`, `stats`

```python
result = send("http://localhost:8766/query", {
    "query": "stats"
})
```

### MCP command-exposure audit

Do not infer MCP coverage from the number of add-in commands. Verify all three layers separately:

1. **Core dispatch table** — count the command names accepted by `RevitCommandTable` or `AcadCommandTable`.
2. **Bridge catalog** — inspect `GET /tools`; this is the actual dynamic contract the generic MCP wrapper exposes.
3. **Installed MCP server** — inspect its tool schemas and allowlists. A bespoke MCP tool may expose only a safe subset of the Bridge catalog even when the host add-in supports more commands.

For dynamic MCP wrappers, generate `tools/list` from the live Bridge catalog and preserve each tool's declared input schema. For write tools, default to `dryRun:true`; require a preview-bound `documentId` and `previewToken` plus an explicit confirmation before `dryRun:false`.

When reporting availability, distinguish **implemented**, **exposed through MCP**, and **live now**. The last requires a successful `/health` probe against the host Bridge; an MCP process being registered is not evidence that Revit or AutoCAD is connected.

### net48 pitfalls bổ sung cho /query
- `Database.Extents` không tồn tại — dùng `db.Extmin` / `db.Extmax`
- `BlockTableRecord.Count` không tồn tại — enumerate ObjectIds thủ công
- `BlockTableRecord.IsUnresolved` không tồn tại — dùng `btr.XrefStatus == XrefStatus.Resolved`
- `Dictionary<K,V>.GetValueOrDefault()` không tồn tại trên net48 — dùng `TryGetValue`
- `dynamic` yêu cầu `Microsoft.CSharp` — dùng typed struct/record thay thế

## Browser/HTML Control Panels over a Local Bridge

A standalone `file://` panel should **not call the Autodesk bridge directly**. Browser private-network/CORS rules and strict `HttpListener` host-prefix matching can make the UI report “disconnected” while MCP or Python clients still reach the bridge.

Use a loopback sidecar gateway:

```text
panel.html (file://)
    ↓ CORS-safe HTTP on 127.0.0.1:<panel-port>
local sidecar
    ├── /health, /query, /execute → Autodesk bridge on http://localhost:<bridge-port>
    └── /ai/chat → configured AI provider → validated read-only query → bridge
```

Rules:

1. Probe the bridge independently before diagnosing the UI; verify `/health` and one real `/query`.
2. Preserve the bridge hostname it registered. An `HttpListener` accepting `http://localhost:8766/` may return HTTP 400 for `http://127.0.0.1:8766/`.
3. Have the sidecar emit explicit CORS headers for `file://` clients and validate request size/schema at the boundary.
4. Treat AI output as an untrusted plan: restrict query/command names to allowlists, clamp limits, and feed exact tool results back to the model for explanation.
5. Keep writes out of free-form chat by default. Route destructive actions through dedicated forms, confirmation, and DryRun.
6. For destructive forms, do **not** hide the real-write path behind an inverse `DryRun` checkbox. Expose two unmistakable actions: a neutral **Preview — no changes** button that sends `dryRun:true`, and a red **DELETE/APPLY FOR REAL** button that sends `dryRun:false`. The real button must show a confirmation dialog listing the selected operations, disable both buttons while running, and report an unambiguous terminal state such as `DRY RUN — NOT DELETED`, `DELETED FOR REAL`, or `DELETE FAILED`. Never claim deletion from a preview result, and never click the destructive button on the user's live drawing without their explicit action/approval.
7. Make the MCP server start the sidecar idempotently: probe its health first, then spawn detached only when absent.
8. Verify all layers end-to-end: syntax/compile, sidecar health, proxied real query, real AI status reply, AI-selected query against live drawing data, and DOM/static assertions that both preview and real-write paths send the intended boolean. Verification of the real-write path should normally stop before mutating a live drawing unless the user explicitly authorizes the exact operation.

See `references/browser-panel-ai-gateway.md` for a condensed implementation and verification recipe.

## Solution Structure (2-in-1 monorepo)

```
solution/
├── Directory.Build.props          # shared TargetFramework, LangVersion, Nullable
├── src/
│   ├── DhcbTools.Core/            # Revit commands — NO Revit API refs (pure logic)
│   ├── DhcbTools.Revit/           # Revit shell: App.cs, Ribbon, Bridge/
│   ├── DhcbTools.Core.AutoCAD/    # AutoCAD commands — pure logic
│   └── DhcbTools.AutoCAD/         # AutoCAD shell: App.cs, Commands/, Bridge/
└── scripts/
    └── dhcb_agent.py              # Python client
```

Core projects have zero Autodesk API references — they only implement `ICoreCommand` / return `CommandResult`. Shell projects reference Core + add the Autodesk API NuGet.

## Host-real regression

Khi chạy bộ kiểm tự mở Revit/AutoCAD, phân biệt host-real, GUI-observed và MCP-live; đọc quy trình và cổng bằng chứng ở [`references/host-real-regression.md`](references/host-real-regression.md).
