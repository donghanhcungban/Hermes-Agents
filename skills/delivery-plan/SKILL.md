---
name: delivery-plan
description: "[omh] Hermes Ralplan workflow: consensus planning with review gates. Use when the user says: ralplan, consensus plan, reviewed plan, issue to PR, acceptance criteria, verification command, reviewable PR, risky planning."
metadata:
 hermes:
 tags: [workflow, oh-my-hermes, planning]
 category: planning
 phase: reviewed-plan
 role: planner
 quality_tier: reviewed-plan-gated
---

# Ralplan

This is an OMH `ralplan` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists

`ralplan` exists to make planning reviewable before execution: the host should gather codebase/source facts, compare options, expose risks, define acceptance criteria, and prepare a handoff without pretending implementation already happened.

## Do Not Use When

- The request is still too ambiguous to name requirements, non-goals, or acceptance criteria; use `deep-interview` first.
- The user asks for one full research-plan-implementation-review-PR cycle; use `ultrawork` (its `delivery_boundary` capability) and keep ralplan as the planning stage.
- The change is a small local refactor or cleanup with no architectural or regression risk; use `ultrawork`, or `ai-slop-cleaner` when observable behavior must stay identical.
- The refactor's direction is already decided and what is missing is its execution shape - which files move in which phase, what verifies each phase, where each phase rolls back to; use `refactor-plan`.
- One plan-blocking choice still needs behavior evidence rather than argument; run `decision-prototype` first and consume its decision receipt without transcript replay.
- The user wants a pure source lookup, citation check, or paper explanation with no implementation plan.
- The unresolved work is repository terminology alignment or a project-language decision frontier; use `context` before planning.

## Examples

Good example:

- Prompt: $ralplan turn this risky refactor into a reviewable plan with acceptance criteria and verification commands.
- Expected behavior: Produce repo/source facts, alternatives, risk review, acceptance criteria, exact verification commands, and handoff readiness without editing code.
- Why: The request is clear enough to plan but risky enough to require consensus-style review before execution.

Bad example:

- Prompt: $ralplan implement the refactor now and open the PR.
- Expected behavior: Stop at the reviewed plan or route the full delivery cycle to `ultrawork` after plan acceptance.
- Why: Ralplan is a planning gate, not implementation, review, CI, or PR evidence.

## Completion Checklist

- Observed repo facts and source/web evidence gaps are named.
- At least two options or one chosen option plus rejected alternatives are recorded.
- Risks, acceptance criteria, and verification commands are testable or explicitly blocked.
- The plan exists as a recorded file-backed artifact, not only as chat narration.
- The implementation handoff is pr
