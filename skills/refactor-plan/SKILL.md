---
name: refactor-plan
description: "Vendored from oh-my-hermes: Refactor Plan"
---

# Refactor Plan
This is an OMH `refactor-plan` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists
`refactor-plan` exists because boundary-changing refactors bounced between goal planning and behavior-preserving cleanup with neither owning the execution shape: the phase order, the per-phase rollback, and the files table that make a large refactor reviewable and abortable.

...

## Catalog Metadata
- Reconnaissance first: affected files, ownership boundaries, hidden coupling, and blast radius are mapped before any phase is ordered; the full contract is `omh-refactor-plan/references/refactor-phases.md`.

...

- Ship the files table with the plan: one row per file with action, phase, and blocks/blocked-by; a row without a phase is unplanned work.
- Size verification to the blast radius, not to optimism: a phase touching public surfaces or persisted shapes carries the full gate, not the fast one.

...

- The plan comes from observed repo evidence, never from memory of the tree.
- Every phase ends at a commit that could ship; a phase that cannot end green is split further.
- Nothing is deleted before the cleanup phase, and cleanup starts from a tagged rollback point.
