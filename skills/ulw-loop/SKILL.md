---
name: "ulw-loop"
description: "[omh] Hermes Loop workflow: agentic interviewer -> planner -> researcher -> builder -> reviewer cycles until a real gate. Use when the user says: loop, goal loop, long horizon goal, never stop, research plan goal feedback, token exhaustion resume, permission profile, star 10k."
compatibility: "Requires the omh CLI on PATH (pip install oh-my-hermes)."
metadata:
 hermes:
 tags: [workflow, oh-my-hermes, goal-loop]
 category: goal-loop
 phase: continuous-goal-loop
 role: planner
 quality_tier: loop-gated
---

# Loop

This is an OMH `loop` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists

`loop` exists for goals whose correct implementation cannot be known upfront but can be discovered through bounded cycles of definition, action, verification, and revision without confusing planned cycles with observed progress.

## Do Not Use When

- The user asks for one bounded delivery cycle; use `ultrawork`'s delivery-boundary capability instead.
- Scope and milestones are already known and only durable checkpoint/resume tracking is needed; use `ultrawork`'s durable-checkpoint capability.
- The user gives only a north-star outcome such as revenue, stars, or adoption and has not accepted a bounded first loop goal.
- The goal is too vague to name an observable problem, next artifact, verification signal, or stop condition.
- The goal depends mainly on external waiting, adoption, revenue, or community response without observable local next actions.
- The permission profile does not allow repeated research, handoff, queue, or feedback cycles.

## Examples

Good example:

- Prompt: ./loop make OMH a credible Hermes workflow pack with install, docs, QA, and feedback cycles.
- Expected behavior: Start a permission-scoped loop, maintain loop_cycle/v2 selected-driver state, choose the next concrete task, and keep external outcomes as waiting states.
- Why: The request is long-horizon and needs repeated discovery, verification, feedback, and resume decisions.

Bad example:

- Prompt: ./loop merge this already reviewed one-line README fix.
- Expected behavior: Use a direct delivery or PR workflow instead of starting a persistent loop.
- Why: The task is bounded and should stop after merge evidence rather than create ongoing cycles.

## Completion Checklist

- The request is classified as task, project, north-star ambition, external-wait, or unclear before a loop starts.
- The current loop_status_card/v1 names the queue item, tick status, verification_plan, and next action.
- failure_mode_summary checks verification_gap, comprehension_debt, and cognitive_surrender before progress advances.
- Completion is backed by linked goal/runtime evidence; queued loop ticks alone are not observed work.
- Native goal activation remains unavailable unless independently observed in its owning runtime; host results never substitute for native activation or contiguous-turn evidence.
