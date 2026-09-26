"""Claude Code subscription CLI adapter with an OpenAI-compatible response.

The adapter intentionally disables Claude Code's own tools. Hermes remains the
only process that may execute a requested Hermes tool call.
"""

from __future__ import annotations

from .protocol import normalize_tool_calls, strict_json

import asyncio
import json
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


CLI_MODEL_ALIASES = {
    "fable": "fable",
    "sonnet": "sonnet",
    "opus": "opus",
    "haiku": "haiku",
    "claude-sonnet-4-6": "sonnet",
    "claude-opus-4-6": "opus",
    "claude-haiku-4-5": "haiku",
}


def discover_models_from_help(help_text: str) -> list[str]:
    """Extract advertised Claude aliases/model IDs from the installed CLI."""
    defaults = set(CLI_MODEL_ALIASES.values())
    match = re.search(r"(?ms)^\s*--model <model>.*?(?=^\s{2}--[a-z]|^Commands:|\Z)", help_text)
    if not match:
        return sorted(defaults)
    candidates = re.findall(r"'([a-z0-9][a-z0-9._-]+)'", match.group(0).lower())
    return sorted(defaults | set(candidates))

Runner = Callable[[list[str], str, dict[str, str]], Awaitable[tuple[int, str, str]]]


class ClaudeCodeCliError(RuntimeError):
    """An actionable failure from the local Claude Code CLI."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


async def _run_cli(
    command: list[str], prompt: str, extra_env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run the Claude Code CLI subprocess.

    *extra_env* is merged into the current environment, enabling per-account
    isolation via the ``CLAUDE_CONFIG_DIR`` env var.
    """
    import os as _os
    # This provider is subscription-only. Do not inherit Hermes' paid fallback API
    # key/gateway settings into claude -p; never mutate the parent environment.
    env = {**_os.environ, **(extra_env or {})}
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                "ANTHROPIC_CUSTOM_HEADERS", "ANTHROPIC_AWS_API_KEY",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        env.pop(key, None)
    if extra_env and extra_env.get("CLAUDE_CONFIG_DIR"):
        env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)  # A selected account must not use an ambient token.
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise ClaudeCodeCliError(
            "Claude Code CLI was not found. Install it, then run `claude auth login`.", 503
        ) from exc

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(prompt.encode("utf-8")), timeout=300)
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise ClaudeCodeCliError("Claude Code CLI timed out after 300 seconds.", 504) from exc
    except asyncio.CancelledError:
        # Cancellation is not a provider failure and must not leave a billing process alive.
        import contextlib
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        await process.wait()
        raise

    return process.returncode or 0, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "input_text"}
        )
    return ""


def _tool_specs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for item in payload.get("tools") or []:
        function = item.get("function") if isinstance(item, dict) else None
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            continue
        tools.append(
            {
                "name": function["name"],
                "description": str(function.get("description") or ""),
                "parameters": function.get("parameters") or {"type": "object"},
            }
        )
    return tools


def _build_prompt(messages: Any, tools: list[dict[str, Any]]) -> str:
    if not isinstance(messages, list) or not messages:
        raise ClaudeCodeCliError("Request must include at least one chat message.", 400)

    transcript: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").upper()
        content = _content_to_text(message.get("content"))
        if message.get("tool_calls"):
            content += "\nRequested tool calls: " + json.dumps(message["tool_calls"], ensure_ascii=False)
        if message.get("tool_call_id"):
            content = f"Tool result ({message['tool_call_id']}): {content}"
        transcript.append(f"[{role}]\n{content}")

    tool_instructions = "No Hermes tools are available; answer directly."
    if tools:
        tool_instructions = (
            "You may either answer directly or request Hermes tools. Only request a tool from "
            "the supplied list, with JSON-object arguments that match its parameters. Hermes, not "
            "you, executes those tool calls."
        )

    return "\n\n".join(
        [
            "You are the model in a Hermes Agent conversation.",
            tool_instructions,
            "Do not claim to have executed a tool. Give a concise helpful answer in the user's language.",
            "Conversation:",
            "\n\n".join(transcript),
            "Available Hermes tools:",
            json.dumps(tools, ensure_ascii=False),
        ]
    )


def _output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["content", "tool_calls"],
        "properties": {
            "content": {"type": "string"},
            "tool_calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "arguments"],
                    "properties": {
                        "name": {"type": "string"},
                        "arguments": {"type": "object", "additionalProperties": True},
                    },
                },
            },
        },
    }


class ClaudeCodeCliClient:
    """Maps an OpenAI chat-completions payload onto `claude -p` safely.

    If an AccountPool is registered for the "claude-code" provider, requests
    are distributed round-robin across accounts via CLAUDE_CONFIG_DIR env isolation.
    """

    MODEL_CATALOG_TTL_SECONDS = 300.0

    def __init__(
        self,
        runner: Runner | None = None,
        cli_path: str | None = None,
        use_account_pool: bool = True,
    ) -> None:
        self._runner = runner or _run_cli
        self._cli_path = cli_path or os.environ.get("CLAUDE_CODE_CLI_PATH") or shutil.which("claude") or "claude"
        self._use_account_pool = use_account_pool
        self._models = sorted(set(CLI_MODEL_ALIASES.values()))
        self._models_refreshed_at = 0.0
        self._models_lock = asyncio.Lock()

    def _get_pool(self):
        if not self._use_account_pool:
            return None
        try:
            from bridge.account_pool import get_pool
        except ImportError:
            try:
                from tools.antigravity_bridge.account_pool import get_pool
            except ImportError:
                return None
        pool = get_pool("claude-code")
        return pool if pool.count() > 0 else None

    async def list_models(self, *, force_refresh: bool = False) -> list[str]:
        """Refresh models advertised by the installed CLI without restarting."""
        now = time.monotonic()
        if (
            not force_refresh
            and self._models_refreshed_at
            and now - self._models_refreshed_at < self.MODEL_CATALOG_TTL_SECONDS
        ):
            return list(self._models)
        async with self._models_lock:
            now = time.monotonic()
            if (
                not force_refresh
                and self._models_refreshed_at
                and now - self._models_refreshed_at < self.MODEL_CATALOG_TTL_SECONDS
            ):
                return list(self._models)
            try:
                returncode, stdout, stderr = await self._runner([self._cli_path, "--help"], "", {})
                if returncode == 0:
                    self._models = discover_models_from_help(stdout or stderr)
            except Exception as exc:  # noqa: BLE001 - discovery is best-effort
                logger.debug("Claude Code model discovery failed: %s", exc)
            self._models_refreshed_at = time.monotonic()
            return list(self._models)

    async def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run Claude Code CLI for a single turn and return an OpenAI-format response.

        When an AccountPool is active:
        - Transparently fails over to the next available account if one hits 429
          (Rate Limit / Usage Quota exceeded).
        - Automatically tracks rate-limit cooldown per account so exhausted accounts
          are temporarily bypassed until their limit resets.
        """
        tools = _tool_specs(payload)
        prompt = _build_prompt(payload.get("messages"), tools)
        requested_model = str(payload.get("model") or "sonnet").lower()
        for prefix in ("claude-code-cli/", "claude-code/"):
            if requested_model.startswith(prefix):
                requested_model = requested_model[len(prefix):]
                break
        model = CLI_MODEL_ALIASES.get(requested_model, requested_model)
        command = [
            self._cli_path,
            "-p",
            "--tools",
            "",
            "--strict-mcp-config",
            "--setting-sources",
            "",  # --tools "" alone does not disable MCP tools.
            "--no-session-persistence",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(_output_schema(), separators=(",", ":")),
            "--model",
            model,
        ]

        pool = self._get_pool()
        max_attempts = max(1, pool.count()) if pool else 1
        attempted_ids: set[int] = set()

        for attempt in range(max_attempts):
            account = pool.pick(exclude_ids=attempted_ids) if pool else None
            if pool and pool.count() and account is None:
                nearest = pool.get_nearest_reset_seconds()
                status = 429 if nearest else 503
                raise ClaudeCodeCliError("No configured account is available; global credentials were not used.", status)
            if account:
                attempted_ids.add(account.id)
                extra_env: dict[str, str] = pool.env_for(account)
                account_tag = f"account-{account.id} ({account.name})"
            else:
                extra_env = {}
                account_tag = "default"

            logger.debug("Claude Code CLI attempt %d/%d using %s", attempt + 1, max_attempts, account_tag)

            try:
                returncode, stdout, stderr = await self._runner(command, prompt, extra_env)
            except FileNotFoundError as exc:
                if pool and account:
                    pool.record_failure(account.id)
                raise ClaudeCodeCliError(
                    "Claude Code CLI was not found. Install it, then run `claude auth login`.", 503
                ) from exc

            if returncode != 0:
                detail = (stderr or stdout or "Claude Code CLI failed.").strip()
                try:
                    cli_error = json.loads(stdout)
                    detail = str(cli_error.get("result") or detail)
                except (TypeError, json.JSONDecodeError):
                    pass
                detail_lower = detail.lower()

                # Rate limit / usage limit (HTTP 429)
                is_rate_limit = (
                    "rate limit" in detail_lower
                    or "usage limit" in detail_lower
                    or "message limit" in detail_lower
                    or "too many requests" in detail_lower
                    or "429" in detail_lower
                )
                if is_rate_limit:
                    if pool and account:
                        cooldown, reason = pool.record_rate_limit(account.id, detail)
                        remaining = [
                            a for a in pool.list_accounts()
                            if a.id not in attempted_ids and a.is_available
                        ]
                        if remaining:
                            logger.warning(
                                "Claude Code account '%s' hit rate limit (%s, cooldown: %.0fs). Retrying with next available account...",
                                account.name, reason, cooldown,
                            )
                            continue

                    nearest = pool.get_nearest_reset_seconds() if pool else None
                    wait_hint = f" (nearest reset in {nearest}s)" if nearest else ""
                    raise ClaudeCodeCliError(
                        f"All Claude Code accounts rate-limited{wait_hint}: {detail}", 429
                    )

                # Auth error (HTTP 401)
                if "not logged in" in detail_lower or "auth" in detail_lower:
                    if pool and account:
                        pool.record_auth_error(account.id, "CLI authentication failed; sign in locally to this account")
                        remaining = [
                            a for a in pool.list_accounts()
                            if a.id not in attempted_ids and a.is_available
                        ]
                        if remaining:
                            logger.warning(
                                "Claude Code account '%s' auth expired. Retrying with next available account...",
                                account.name,
                            )
                            continue
                    raise ClaudeCodeCliError("Claude Code is not logged in. Run `claude auth login`.", 401)

                # General error
                if pool and account:
                    pool.record_failure(account.id)
                raise ClaudeCodeCliError(detail, 502)

            break  # Success: do not call a second account or consume another request.

        try:
            output = strict_json(stdout)
            structured = output["structured_output"]
            content = structured["content"]
            tool_calls = structured["tool_calls"]
        except (KeyError, ValueError, TypeError, RecursionError) as exc:
            if pool and account:
                pool.record_failure(account.id)
            raise ClaudeCodeCliError("Claude Code returned an invalid structured response.", 502) from exc

        if not isinstance(content, str) or not isinstance(tool_calls, list):
            if pool and account:
                pool.record_failure(account.id)
            raise ClaudeCodeCliError("Claude Code returned an invalid structured response.", 502)

        try:
            validated_calls = normalize_tool_calls(tool_calls, tools, payload.get("tool_choice"))
        except (ValueError, TypeError, RecursionError) as exc:
            if pool and account:
                pool.record_failure(account.id)
            raise ClaudeCodeCliError(str(exc), 502) from None
        openai_tool_calls: list[dict[str, Any]] = []
        for tool_call in validated_calls:
            name, arguments = tool_call["name"], tool_call["arguments"]
            openai_tool_calls.append(
                {
                    "id": f"call_{uuid.uuid4().hex}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
                }
            )

        # Record success
        if pool and account:
            pool.record_success(account.id)

        message: dict[str, Any] = {"role": "assistant", "content": content or None}
        if openai_tool_calls:
            message["tool_calls"] = openai_tool_calls
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": requested_model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if openai_tool_calls else "stop",
                }
            ],
        }

