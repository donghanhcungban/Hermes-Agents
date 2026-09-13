---
name: cli-provider-bridges
description: "Use when integrating a local AI CLI as a model provider."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cli, provider, bridge, llm, integration, proxy]
    related_skills: [hermes-provider-management, provider-proxy-engineering]
---

# CLI Provider Bridges

## Purpose

Use this skill when an application needs to consume a locally installed, user-authenticated AI CLI (for example, a subscription-backed coding CLI) through an OpenAI-compatible provider endpoint.

## Architecture

1. **Provider profile**: register a named provider and expose only supported model aliases.
2. **Local bridge**: bind to loopback only; expose `/v1/models` and `/v1/chat/completions`.
3. **CLI adapter**: invoke the executable with argument arrays, never a shell string.
4. **Response adapter**: convert CLI structured output into OpenAI messages and tool calls.
5. **Setup command**: install the plugin/runtime and write the chosen provider/model configuration.

Keep the bridge local. Treat its local API key as a routing token, never as an upstream subscription credential.

## Tool-call safety

- The host agent remains the only executor of its tools.
- Disable the delegated CLI's own tools when using it as a model backend (for Claude Code: `--tools ""`).
- Supply an explicit structured-output schema for either a text response or a host-tool request.
- Validate every returned tool name against the tools offered by the host, and require object-valued arguments before returning an OpenAI tool call.
- Do not pass untrusted request text into a shell command.

## Authentication compatibility

Before using isolation/minimal-start flags, test a real subscription request. Some CLIs keep subscription authentication in user-level state that minimalist modes deliberately skip.

For Claude Code specifically, do **not** use `--bare` for a subscription-backed bridge: it prevented the CLI from using the authenticated subscription in a verified local test. Keep `--tools ""` and `--no-session-persistence` instead.

## Verification sequence

1. Add a focused test for CLI command construction and structured-response parsing; run it red first for new behavior.
2. Run the full project suite.
3. Run the installed setup command's `--help` to catch parser/handler wiring defects that unit tests can miss.
4. Reinstall the runtime, restart the bridge, and query `/v1/models`.
5. Make a real loopback request with a minimal prompt such as `Reply exactly: OK`.
6. Test each advertised model alias, including the expected response when plan/credit entitlement blocks one.
7. Only claim availability after the live request succeeds.

## Failure handling

- Parse the CLI's JSON error payload when it exits nonzero; surface its concise result instead of returning the raw blob.
- Map recognizable login failures to an actionable authentication error.
- Preserve upstream plan/usage-credit errors verbatim; do not relabel an entitlement restriction as a transport failure.
- If a model is accepted by the CLI but not entitled by the user's plan, keep it listed only when the provider is intentionally exposing that optional model and document the credit requirement.

## Release discipline

- Commit the feature on a dedicated branch.
- Create a PR, verify checks, merge only when clean, then reinstall from the merged `main` revision.
- Re-test the installed artifact, not merely the working tree.

See `references/claude-code-subscription.md` for the verified Claude Code flags, output contract, and model-entitlement behavior.
