"""Multi-provider bridge profiles for Hermes Agent.

Providers:
  - Antigravity (Google OAuth): Gemini + Claude
  - Claude Code CLI: Claude subscription via `claude -p`
  - Codex CLI: ChatGPT/OpenAI subscription via `codex exec`

All three route through the shared bridge on port 8100.
"""

from __future__ import annotations

import sys
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


class AntigravityProfile(ProviderProfile):
    """Antigravity OAuth Bridge provider profile."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context: Any
    ) -> dict[str, Any]:
        """Support reasoning/thinking config forwarding and auto-wake bridge daemon."""
        try:
            from hermes_constants import get_hermes_home

            bridge_root = get_hermes_home() / "bridge" / "antigravity"
            if bridge_root.is_dir() and str(bridge_root) not in sys.path:
                sys.path.insert(0, str(bridge_root))
            from tools.antigravity_bridge.server import ensure_antigravity_bridge_running
            ensure_antigravity_bridge_running()
        except Exception:
            pass
        reasoning_config = context.get("reasoning_config")
        if not reasoning_config:
            return {}
        return {"thinking_config": reasoning_config}


class ClaudeCodeCliProfile(ProviderProfile):
    """Claude Code subscription CLI through the local OpenAI-compatible bridge."""

    def build_extra_body(self, **context: Any) -> dict[str, Any]:
        try:
            from hermes_constants import get_hermes_home

            bridge_root = get_hermes_home() / "bridge" / "antigravity"
            if bridge_root.is_dir() and str(bridge_root) not in sys.path:
                sys.path.insert(0, str(bridge_root))
            from tools.antigravity_bridge.server import ensure_claude_code_bridge_running
            ensure_claude_code_bridge_running()
        except Exception:
            pass
        return {}


class CodexCliProfile(ProviderProfile):
    """OpenAI Codex CLI (ChatGPT subscription) through the local bridge.

    Supports multi-account round-robin rotation via AccountPool when more than
    one Codex account is registered (``manage.py add-account codex``).
    """

    def build_extra_body(self, **context: Any) -> dict[str, Any]:
        try:
            from hermes_constants import get_hermes_home

            bridge_root = get_hermes_home() / "bridge" / "antigravity"
            if bridge_root.is_dir() and str(bridge_root) not in sys.path:
                sys.path.insert(0, str(bridge_root))
            from tools.antigravity_bridge.server import ensure_codex_bridge_running
            ensure_codex_bridge_running()
        except Exception:
            pass
        return {}


antigravity = AntigravityProfile(
    name="antigravity",
    aliases=("google-antigravity", "antigravity-oauth"),
    display_name="Google Antigravity (OAuth)",
    description="Google Gemini & Claude models via Antigravity OAuth local bridge",
    signup_url="https://antigravity.google",
    env_vars=("ANTIGRAVITY_API_KEY",),
    base_url="http://127.0.0.1:8100/v1",
    auth_type="api_key",
    fallback_models=(
        "gemini-3.7-flash",
        "gemini-3.7-flash-medium",
        "gemini-3.7-flash-low",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "gpt-oss-120b",
    ),
    default_aux_model="gemini-3.7-flash",
    supports_vision=True,
)

register_provider(antigravity)

claude_code_cli = ClaudeCodeCliProfile(
    name="claude-code-cli",
    aliases=("claude-code", "claude-subscription"),
    display_name="Claude Code (Subscription CLI)",
    description="Local Claude Code CLI bridge using an authenticated Claude subscription. "
                "Supports multiple accounts via CLAUDE_HOME isolation.",
    signup_url="https://claude.ai",
    env_vars=("CLAUDE_CODE_CLI_KEY",),
    base_url="http://127.0.0.1:8100/v1/claude-code",
    auth_type="api_key",
    fallback_models=("fable", "opus", "sonnet", "haiku"),
    default_aux_model="sonnet",
    supports_vision=False,
)

register_provider(claude_code_cli)

codex_cli = CodexCliProfile(
    name="codex-cli",
    aliases=("codex", "openai-codex", "codex-subscription"),
    display_name="Codex CLI (ChatGPT Subscription)",
    description="OpenAI Codex CLI bridge using a ChatGPT Plus/Team subscription. "
                "Supports multiple accounts via CODEX_HOME isolation.",
    signup_url="https://chatgpt.com",
    env_vars=("CODEX_CLI_KEY",),
    base_url="http://127.0.0.1:8100/v1/codex",
    auth_type="api_key",
    fallback_models=("gpt-6-astra", "o3-mini", "o3", "gpt-4o"),
    default_aux_model="gpt-6-astra",
    supports_vision=False,
)

register_provider(codex_cli)

