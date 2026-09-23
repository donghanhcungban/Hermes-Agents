---
name: context-budget
description: "Manage context window budget: compression, eviction, priority."
---

# Context
This is an OMH `context` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists
`context` exists to reduce repository terminology drift without creating a second machine store or a vocabulary router: the host can answer lookups, facilitate dependency-aware alignment, and project approved results into existing review and handoff boundaries.

## Do Not Use When
- A safe one-term definition or source lookup can be answered directly; use the read-only lookup mode and do not enter the full context interview.
- The request is broad ambiguity with no project-language conflict; use `deep-interview`.

...

- The user wants to capture or curate general retained memory rather than repository terminology; use `memory-new` or `memory-sync`.
- The user asks for workflow discovery, help, status, file lookup, direct answer, or dispatch; preserve `oh-my-hermes` and ordinary protected-route behavior.

...

## Examples
- Prompt: Use ulw-context to align the names this repository uses before we plan the feature.
- Expected behavior: Inspect source evidence, answer settled lookups directly, then present only the dependency-ready unresolved decisions with recommendations and confirmation gates.

...

- Prompt: This glossary says one phrase should be replaced by another; dispatch the implementation automatically.
- Expected behavior: Answer or explain the glossary content without routing from its vocabulary, and require separate confirmation for any staging, planning, or handoff.

...

## Use When
```
Strong routing signals: `ulw-context`, `$context`, `./context`, `project terminology alignment`, `review project terms`, `align project terminology`, `terminology this project uses`
```

## Catalog Metadata
Category: `clarification`
Phase: `terminology-alignment`
Quality tier: `clarity-gated`
Reasoning demand: `light`
Quality bar:
