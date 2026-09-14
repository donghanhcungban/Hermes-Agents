---
name: "omh-native-debugging"
description: "[omh] Hermes native-debugging workflow: prepare hypothesis-driven debugging of native binaries and instruct the executor to drive a DAP debugger instead of printf. Use when the user says: native-debugging, native debugging, native binary, segfault, segmentation fault, core dump, stack corruption, memory corruption."
metadata:
 hermes:
 tags: [workflow, oh-my-hermes, verification]
 category: verification
 phase: native-debugging
 role: reviewer
 quality_tier: native-debug-evidence-gated
---

# Native Debugging

This is an OMH `native-debugging` workflow skill, projected for Agent Skills hosts (Claude Code, Codex, Cursor, opencode, OpenClaw, pi).

## Why This Exists

`native-debugging` closes OMH's zero-coverage low-level domain by preparing a hypothesis-driven, DAP-first debugging plan for native binaries, while OMH itself continues to execute nothing.

## Do Not Use When

- The failure is a build or CI failure rather than a runtime fault in a binary; use `build-failure-triage`.
- The subject is an agent or workflow misbehaving rather than a native binary; use `agent-debug`.
- The change is Rust source work whose risk is `unsafe` or UB discipline; use `rust`.
- The request is to judge whether a fix is verified rather than to find the fault; use `verification-gate`.

## Examples

Good example:

- Prompt: This binary segfaults on the third request; help me debug it.
- Expected behavior: Prepare native_fault_statement/v1, three competing hypotheses with distinguishing observations, and a debugger_session_plan/v1 naming the DAP adapter, breakpoints, and values to read.
- Why: The request is a runtime fault in a native binary where the plan, not the guess, is what OMH can prepare.

Bad example:

- Prompt: Add some printfs and tell me it is fixed once the crash stops.
- Expected behavior: Name the DAP-driven observation plan, and keep reproduction, root cause, and fix as separate not_observed states.
- Why: A disappearing symptom is not a root cause, and printf-via-rebuild is the fallback rather than the method.

## Completion Checklist

- The fault is stated as an observed symptom with a reproduction command, separate from any assumed cause.
- At least three hypotheses span distinct axes and each carries its refuting observation.
- The debugger session plan names the DAP adapter, breakpoints, watchpoints, threads, frames, and values to read.
- The handoff says the executor drives the debugger and OMH executes nothing.
- Reproduction, debugger output, root cause, and fix are reported as separate observed or not_observed states.

## Recovery Notes

- If the fault does not reproduce, make reproduction the first hypothesis and plan the observation that would establish it, rather than debugging a fault no one can trigger.
- If no debug adapter or symbols are available, say so, plan the coarser evidence path, and keep root cause unclaimed instead of upgrading a guess.

## Use When

Use when Hermes should prepare
