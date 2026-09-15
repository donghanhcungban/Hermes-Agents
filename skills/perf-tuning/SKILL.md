---
name: perf-tuning
description: "Profile and tune performance: CPU, memory, I/O bottlenecks."
---

# Ultraperf
This is an OMH `ultraperf` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists
`ultraperf` exists because most performance work starts unlocalized: something is slow, leaking, or expensive and nobody knows where. It forces measurement before edits, one hypothesis at a time, executor-owned changes, and a regression budget, so an optimization loop cannot end in unverified claims.

...

## Use When
```
Strong routing signals: `ultraperf`, `$ultraperf`, `ulw-perf`, `performance audit`, `performance bottleneck`, `find the bottleneck`, `profile the hot path`, `memory leak investigation`, `token cost hotspot`, `storage footprint audit`, `rendering jank`, `model inference hotspot`, `slow ci pipeline`, `query performance audit
```
