---
name: tech-debt-audit
description: "Audit and prioritise technical debt across a codebase."
---

# Tech Debt Audit
This is an OMH `tech-debt-audit` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists
`tech-debt-audit` exists so accumulated debt becomes a ranked, reconcilable ledger instead of a one-off complaint: findings cite file:line, severity and effort make the trade-off explicit, quick wins are separated from big fixes, and reruns mark what was resolved instead of rediscovering it.

...

## Use When
```
Strong routing signals: `tech-debt-audit`, `tech debt`, `tech debt audit`, `technical debt`, `technical debt audit`, `tech debt ledger`, `debt ledger`, `audit our tech debt`, `tech debt report`, `code debt audit`, `where is our tech debt`, `기술부채`, `기술 부채`, `기술부채 감사`, `기술부채 감사해줘`, `기술부채 점검`, `기술부채 장부`, `부채 원장`
```

...

## Catalog Metadata
- Audit dimension by dimension from the named list - architectural decay, consistency rot, type and contract gaps, test debt, dependency and configuration debt, performance and resource debt, error-handling and observability debt, security hygiene, documentation drift; the full contract is
`omh-tech-debt-audit/references/debt-dimensions.md`.
- Every finding row carries a stable id, its dimension, a file:line citation, a severity, an effort class (S/M/L), and a bounded recommendation - never a rewrite.

...

Required inputs:
- the repo root or the scoped path list the audit is confined to
- the stack truth from manifests (package/build files), not from memory of the tree
- the previous ledger when one exists, so the rerun can reconcile instead of restart
Expected outputs:

...

Artifact expectations:
- debt ledger per `omh-tech-debt-audit/references/debt-dimensions.md`
- prepared detection commands named per stack, marked observed only after their output is seen
Safety rules:
