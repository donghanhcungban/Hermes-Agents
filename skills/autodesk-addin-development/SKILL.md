---
name: autodesk-addin-development
description: "Use when building Revit or AutoCAD C# plugins; verify the exact host version, update and SDK before choosing a target framework."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [autodesk, revit, autocad, csharp, addin, bim, plugin]
    related_skills: [evidence-driven-delivery]
---

# Autodesk add-in development: host-version-first

Produce source, a build targeted to the verified host, tests and installation
instructions. A successful compile is not proof that the host loads the add-in.
Do not claim that a described HTTP bridge exists or is live.

## Runtime and SDK gate

Record product, full version/update/build, supported SDK, installed runtime,
architecture and authoritative documentation date. Do not set a universal
`<TargetFramework>net48</TargetFramework>` for all Revit/AutoCAD projects.
Revit 2025/2026 originally use .NET 8, while Autodesk has introduced .NET 10
transitions in updates; Revit 2027 uses .NET 10. AutoCAD 2026 compatibility also
changes at Update 1.2. Check the exact installed update before choosing the TFM
and validate managed/native dependencies in that host. Do not infer SDK package
versions from the marketing year or equate an AutoCAD release number with it.

Official references, checked 2026-09-26:
- https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Revit--Requirements-for-products-affected-by-the-Microsoft--NET-10-transition.html
- https://help.autodesk.com/cloudhelp/2027/ENU/Revit-WhatsNew/files/GUID-8D7A4715-EAF8-4BD1-BE78-061F900D0BCE.htm
- https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-A6C680F2-DE2E-418A-A182-E4884073338A.htm

Separate pure calculation/domain projects from host adapters. Share language and
nullable settings in Directory.Build.props, not a blindly shared framework.
Reference the verified host API assemblies/SDK, lock dependency versions and
retain licenses. Community NuGet wrappers are not official SDK certification.
For a genuinely legacy net48 host, check unavailable BCL APIs and compiler support;
`init` and `required` have different compatibility requirements. Prefer explicit
types over dynamic and qualify `System.Exception` where Autodesk namespaces clash.

## API context and transactions

Revit calls run only in a supported API context. Create the ExternalEvent in a
valid context; marshal background requests to an IExternalEventHandler. Bound the
queue and timeout, handle rejected raises/cancellation, capture document identity
and revision, and revalidate them in Execute. Never touch Revit model objects from
the HTTP worker. Use an explicit Transaction/TransactionGroup for writes and roll
back on validation or execution failure.

For AutoCAD, use the host-supported command/document context, document locking
where required, and transactions. Check that the intended document is still active
before changing its database. Keep pure calculation code independent of API refs.

## Bridge contract: implement and verify, do not assume

Prefer read-only integration first: `/health`, a typed query catalog and bounded
queries for document metadata, elements, systems, levels, schedules or layers.
A bridge must authenticate clients even on loopback, validate host/origin where
relevant, bound payloads, reject unknown commands and avoid leaking model data or
tokens in logs. Do not enable wildcard CORS as an authentication workaround.
Never expose a desktop bridge directly to the public internet.

A future write flow must be preview-first. Bind approval to exact document ID,
revision, operation digest and expiring single-use preview token; the server must
verify it. A model-supplied `approved: true` is not permission. Keep separate,
unambiguous Preview and Apply controls. Invalid/stale previews fail closed.

Python read-only example for a bridge that actually implements this contract:

```python
import json
import urllib.request
from urllib.parse import urlsplit

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Bridge redirects are not allowed")

def query(base_url, payload, token):
    parsed = urlsplit(base_url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("Use the verified loopback bridge origin")
    if not token or not isinstance(payload, dict):
        raise ValueError("Authenticated structured query required")
    body = json.dumps(payload, allow_nan=False).encode("utf-8")
    if len(body) > 100_000:
        raise ValueError("Query too large")
    req = urllib.request.Request(base_url.rstrip("/") + "/query", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(req, timeout=30) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Bridge response too large")
    return json.loads(raw)

# After a verified host and authenticated bridge are available:
# result = query(base_url, {"query": "document_info", "params": {}}, token)
```

All examples use the same three-argument signature; secrets must come from the
operator's secret storage, never checked-in code or tool output. The contract
above is a design target, not a claim about any installed host.

## Evidence and regression

Report separately: implemented dispatch commands, bridge-exposed schemas,
MCP-exposed tools, successful compilation, host-real loading, GUI-observed behavior
and live read/write evidence. Test permission denial, wrong documents, stale
previews, timeouts, cancellation, rollback and repeated writes on disposable files.
Only perform a live write with authorization for the exact mutation.

Existing detailed references remain available, but this runtime/security gate
takes precedence over conflicting legacy examples:
- [Browser panel and AI gateway](references/browser-panel-ai-gateway.md)
- [Host-real regression](references/host-real-regression.md)
