"""OpenAI Codex subscription CLI adapter with an OpenAI-compatible response.

The adapter intentionally runs Codex with:
  - --sandbox read-only  (no shell writes, no file mutations)
  - --ignore-user-config (no MCP servers, no plugins, clean environment)
  - --ephemeral          (no session persistence on disk)
  - --skip-git-repo-check (works from any directory)
  - --json + --output-schema <strict_schema>

Hermes remains the only process that may execute a requested Hermes tool call.
Codex is reduced to a pure language model endpoint.
"""

from __future__ import annotations

from .protocol import normalize_tool_calls, strict_json

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model catalogue (ChatGPT subscription via Codex CLI)
# ---------------------------------------------------------------------------

CODEX_SUPPORTED_MODELS = [
    {
        "id": "gpt-6-astra",
        "name": "GPT-6 Astra (Codex CLI)",
        "description": "OpenAI GPT-6 Astra model via Codex subscription CLI.",
    },
    {
        "id": "o3-mini",
        "name": "o3-mini (Codex CLI)",
        "description": "OpenAI o3-mini reasoning model via Codex CLI.",
    },
    {
        "id": "o3",
        "name": "o3 (Codex CLI)",
        "description": "OpenAI o3 reasoning model via Codex CLI.",
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o (Codex CLI)",
        "description": "OpenAI GPT-4o multimodal model via Codex CLI.",
    },
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini (Codex CLI)",
        "description": "OpenAI GPT-4o mini via Codex CLI.",
    },
]

# Canonical model IDs that Codex CLI (ChatGPT subscription) supports
CODEX_MODEL_IDS: set[str] = {m["id"] for m in CODEX_SUPPORTED_MODELS}

# Aliases: maps user-supplied names -> canonical Codex CLI model IDs
CODEX_MODEL_ALIASES: dict[str, str] = {
    "gpt-6-astra": "gpt-6-astra",
    "gpt6-astra": "gpt-6-astra",
    "astra": "gpt-6-astra",
    "o3-mini": "o3-mini",
    "o3mini": "o3-mini",
    "o3": "o3",
    "gpt-4o": "gpt-4o",
    "gpt4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt4o-mini": "gpt-4o-mini",
    # Legacy / placeholder names the Hermes config may still carry
    "gpt-5-codex": "gpt-6-astra",
    "gpt5-codex": "gpt-6-astra",
    "codex": "gpt-6-astra",
}


def _default_model() -> str:
    """Read the user's default model from ~/.codex/config.toml (best-effort)."""
    try:
        import re as _re

        config_path = Path.home() / ".codex" / "config.toml"
        if config_path.is_file():
            text = config_path.read_text(encoding="utf-8")
            # Look for a top-level  model = "..."  entry (not inside a section)
            m = _re.search(r'^model\s*=\s*["\']([^"\']+)["\']', text, _re.MULTILINE)
            if m:
                raw = m.group(1).strip()
                # Validate that it's a plausible Codex model or alias
                if raw in CODEX_MODEL_ALIASES or raw in CODEX_MODEL_IDS:
                    return CODEX_MODEL_ALIASES.get(raw, raw)
                return raw
    except Exception:
        pass
    return "gpt-6-astra"


# ---------------------------------------------------------------------------
# Runner type (injectable for tests)
# ---------------------------------------------------------------------------

# Signature: (command, stdin_text, extra_env) -> (returncode, stdout, stderr)
Runner = Callable[[list[str], str, dict[str, str]], Awaitable[tuple[int, str, str]]]


async def _run_cli(
    command: list[str], prompt: str, extra_env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    """Run a Codex CLI subprocess, piping *prompt* to stdin.

    *extra_env* is merged into the current process environment, allowing
    per-account config isolation via ``CODEX_HOME``.
    """
    env = None
    if extra_env:
        env = {**os.environ, **extra_env}
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise CodexCliError(
            "Codex CLI was not found. Install it with `npm install -g @openai/codex`, "
            "then run `codex login`.",
            503,
        ) from exc

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(prompt.encode("utf-8")), timeout=300
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise CodexCliError("Codex CLI timed out after 300 seconds.", 504) from exc

    except asyncio.CancelledError:
        # Cancellation is not a provider failure and must not leave a billing process alive.
        import contextlib
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        await process.wait()
        raise

    return process.returncode or 0, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class CodexCliError(RuntimeError):
    """An actionable failure from the local Codex CLI."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


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
    """Extract Hermes-sanctioned tool specs from the OpenAI payload."""
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
    """Build a text prompt for `codex exec` from an OpenAI messages array."""
    if not isinstance(messages, list) or not messages:
        raise CodexCliError("Request must include at least one chat message.", 400)

    transcript: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").upper()
        content = _content_to_text(message.get("content"))
        if message.get("tool_calls"):
            content += "\nRequested tool calls: " + json.dumps(
                message["tool_calls"], ensure_ascii=False
            )
        if message.get("tool_call_id"):
            content = f"Tool result ({message['tool_call_id']}): {content}"
        transcript.append(f"[{role}]\n{content}")

    if tools:
        tool_instructions = (
            "You may either answer directly or request Hermes tools. Only request a tool from "
            "the supplied list below with JSON-object arguments that match its parameters. "
            "Hermes, not you, executes those tool calls. "
            "Return tool_calls as an array of objects with 'name' and 'arguments' (JSON string)."
        )
    else:
        tool_instructions = "No Hermes tools are available; answer directly."

    return "\n\n".join(
        [
            "You are the model in a Hermes Agent conversation.",
            tool_instructions,
            "Do not claim to have executed a tool. Do NOT run any shell commands, "
            "file edits, or web searches yourself. Give a concise helpful answer in the user's language.",
            "Conversation:",
            "\n\n".join(transcript),
            "Available Hermes tools:",
            json.dumps(tools, ensure_ascii=False),
        ]
    )


def _output_schema() -> dict[str, Any]:
    """Strict JSON schema for Codex CLI --output-schema."""
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
                        # arguments is a JSON-encoded string (to match Codex output format)
                        "arguments": {"type": "string"},
                    },
                },
            },
        },
    }


def _extract_text_from_jsonl(jsonl_output: str) -> str:
    """Extract the final agent_message text from Codex --json JSONL output."""
    last_text = ""
    for line in jsonl_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            obj.get("type") == "item.completed"
            and isinstance(obj.get("item"), dict)
            and obj["item"].get("type") == "agent_message"
        ):
            text = obj["item"].get("text") or ""
            if text:
                last_text = text
        elif obj.get("type") == "error":
            raise CodexCliError(str(obj.get("message") or "Unknown Codex CLI error."), 502)
        elif obj.get("type") == "turn.failed":
            err_msg = ""
            if isinstance(obj.get("error"), dict):
                err_msg = obj["error"].get("message") or ""
            else:
                err_msg = str(obj.get("error") or "")
            err_lower = err_msg.lower()
            if "401" in err_msg or "auth" in err_lower or "login" in err_lower:
                raise CodexCliError(
                    "Codex CLI is not authenticated. Run `codex login`.", 401
                )
            if "429" in err_msg or "rate limit" in err_lower:
                raise CodexCliError("Codex CLI rate limit reached.", 429)
            if "400" in err_msg:
                raise CodexCliError(f"Codex CLI request error: {err_msg}", 400)
            raise CodexCliError(f"Codex CLI turn failed: {err_msg}", 502)
    return last_text


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class CodexCliClient:
    """Maps an OpenAI chat-completions payload onto `codex exec` safely.

    If an AccountPool is available for the "codex" provider, requests are
    distributed round-robin across all registered accounts. Each account is
    isolated via CODEX_HOME env var pointing to its own config directory.

    Single-account mode (no pool / pool empty) is the default; the current
    global ``~/.codex/`` config is used in that case.
    """

    MODEL_CATALOG_TTL_SECONDS = 300.0

    def __init__(
        self,
        runner: Runner | None = None,
        cli_path: str | None = None,
        use_account_pool: bool = True,
    ) -> None:
        self._runner = runner or _run_cli
        self._cli_path = cli_path or os.environ.get("CODEX_CLI_PATH") or shutil.which("codex") or "codex"
        self._use_account_pool = use_account_pool
        self._models: list[dict[str, Any]] = list(CODEX_SUPPORTED_MODELS)
        self._models_refreshed_at = 0.0
        self._models_lock = asyncio.Lock()

    def _get_pool(self):  # -> Optional[AccountPool]
        if not self._use_account_pool:
            return None
        try:
            from bridge.account_pool import get_pool
        except ImportError:
            try:
                from tools.antigravity_bridge.account_pool import get_pool
            except ImportError:
                return None
        pool = get_pool("codex")
        return pool if pool.count() > 0 else None

    async def list_models(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Return catalog of models available via the installed Codex CLI."""
        now = time.monotonic()
        if (
            not force_refresh
            and self._models_refreshed_at
            and now - self._models_refreshed_at < self.MODEL_CATALOG_TTL_SECONDS
        ):
            return list(self._models)
        async with self._models_lock:
            # Double-checked locking
            now = time.monotonic()
            if (
                not force_refresh
                and self._models_refreshed_at
                and now - self._models_refreshed_at < self.MODEL_CATALOG_TTL_SECONDS
            ):
                return list(self._models)
            # Discovery: pull default model from config.toml and enrich catalog
            try:
                default_model_id = await asyncio.to_thread(_default_model)
                if default_model_id and default_model_id not in CODEX_MODEL_IDS:
                    # Unknown model from user config – add it to the catalogue
                    if not any(m["id"] == default_model_id for m in self._models):
                        self._models = [
                            {"id": default_model_id, "name": default_model_id, "description": "User-configured model."},
                            *list(CODEX_SUPPORTED_MODELS),
                        ]
                else:
                    self._models = list(CODEX_SUPPORTED_MODELS)
            except Exception as exc:
                logger.debug("Codex model discovery failed: %s", exc)
            self._models_refreshed_at = time.monotonic()
            return list(self._models)

    async def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run `codex exec` for a single turn and return an OpenAI-format response.

        When an AccountPool is active:
        - Transparently fails over to the next available account if one hits 429
          (Rate Limit / Usage Quota exceeded).
        - Automatically tracks rate-limit cooldown per account so exhausted accounts
          are temporarily bypassed until their limit resets.
        """
        tools = _tool_specs(payload)
        prompt = _build_prompt(payload.get("messages"), tools)

        requested_model = str(payload.get("model") or "gpt-6-astra").lower()
        # Strip provider prefix (codex/, codex-cli/)
        for prefix in ("codex-cli/", "codex/"):
            if requested_model.startswith(prefix):
                requested_model = requested_model[len(prefix):]
                break
        model = CODEX_MODEL_ALIASES.get(requested_model, requested_model)

        schema_dict = _output_schema()
        schema_json = json.dumps(schema_dict, separators=(",", ":"))

        pool = self._get_pool()
        max_attempts = max(1, pool.count()) if pool else 1
        attempted_ids: set[int] = set()

        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            account = pool.pick(exclude_ids=attempted_ids) if pool else None
            if pool and pool.count() and account is None:
                nearest = pool.get_nearest_reset_seconds()
                status = 429 if nearest else 503
                raise CodexCliError("No configured account is available; global credentials were not used.", status)
            if account:
                attempted_ids.add(account.id)
                extra_env: dict[str, str] = pool.env_for(account)
                account_tag = f"account-{account.id} ({account.name})"
            else:
                extra_env = {}
                account_tag = "default"

            logger.debug("Codex CLI attempt %d/%d using %s", attempt + 1, max_attempts, account_tag)

            # Write schema to a temp file so we can pass it via --output-schema
            tmp_schema = None
            try:
                fd, tmp_schema = tempfile.mkstemp(suffix=".json", prefix="hermes_codex_")
                os.close(fd)
                with open(tmp_schema, "w", encoding="utf-8") as f:
                    f.write(schema_json)

                command = [
                    self._cli_path,
                    "exec",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--ignore-user-config",
                    "--output-schema",
                    tmp_schema,
                    "--json",
                    "-m",
                    model,
                    "-",  # read prompt from stdin
                ]

                try:
                    returncode, stdout, stderr = await self._runner(command, prompt, extra_env)
                except FileNotFoundError as exc:
                    if pool and account:
                        pool.record_failure(account.id)
                    raise CodexCliError(
                        "Codex CLI was not found. Install it with `npm install -g @openai/codex`, "
                        "then run `codex login`.",
                        503,
                    ) from exc
            finally:
                if tmp_schema:
                    try:
                        os.unlink(tmp_schema)
                    except OSError:
                        pass

            if returncode not in (0,):
                # Non-zero exit – parse stderr/stdout for rate limit, auth, or crash
                detail = (stderr or stdout or "Codex CLI failed.").strip()
                detail_lower = detail.lower()

                # Check for rate limit / usage limit (HTTP 429)
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
                                "Codex account '%s' hit rate limit (%s, cooldown: %.0fs). Retrying with next available account...",
                                account.name, reason, cooldown,
                            )
                            last_error = CodexCliError(detail[:512], 429)
                            continue

                    nearest = pool.get_nearest_reset_seconds() if pool else None
                    wait_hint = f" (nearest reset in {nearest}s)" if nearest else ""
                    raise CodexCliError(
                        f"All Codex accounts rate-limited{wait_hint}: {detail[:512]}", 429
                    )

                # Check for authentication failure (HTTP 401)
                if "not logged in" in detail_lower or "auth" in detail_lower or "401" in detail_lower:
                    if pool and account:
                        pool.record_auth_error(account.id, "CLI authentication failed; sign in locally to this account")
                        remaining = [
                            a for a in pool.list_accounts()
                            if a.id not in attempted_ids and a.is_available
                        ]
                        if remaining:
                            logger.warning(
                                "Codex account '%s' auth expired. Retrying with next available account...",
                                account.name,
                            )
                            last_error = CodexCliError("Codex CLI is not authenticated. Run `codex login`.", 401)
                            continue
                    raise CodexCliError("Codex CLI is not authenticated. Run `codex login`.", 401)

                # General non-zero exit (502)
                if pool and account:
                    pool.record_failure(account.id)
                raise CodexCliError(detail[:512], 502)

            # Parse JSONL output
            try:
                raw_text = _extract_text_from_jsonl(stdout)
            except CodexCliError:
                if pool and account:
                    pool.record_failure(account.id)
                raise

            break  # First successful result is final; do not consume other accounts.

        # --output-schema promised structured JSON. Never turn malformed/empty output into success.
        try:
            structured = strict_json(raw_text)
            if not isinstance(structured, dict) or not isinstance(structured.get("content"), str):
                raise ValueError("Codex returned invalid structured content")
            content = structured["content"]
            validated_calls = normalize_tool_calls(
                structured.get("tool_calls"), tools, payload.get("tool_choice"), string_arguments=True
            )
        except (ValueError, TypeError, RecursionError) as exc:
            if pool and account:
                pool.record_failure(account.id)
            raise CodexCliError(str(exc), 502) from None
        openai_tool_calls = [
            {"id": f"call_{uuid.uuid4().hex}", "type": "function", "function": {
                "name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False, allow_nan=False)
            }} for tc in validated_calls
        ]

        # Record success for the chosen account
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

