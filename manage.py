#!/usr/bin/env python3
"""CLI utility to manage the Antigravity Local OAuth Bridge for Hermes Agent.

Usage:
  python manage.py start     # Start bridge server daemon
  python manage.py stop      # Stop bridge server
  python manage.py status    # Check status and token health
  python manage.py login     # Log in via Google OAuth PKCE
  python manage.py install   # Install plugin to ~/.hermes/ for upgrade persistence
  python manage.py setup     # Configure Hermes config.yaml to use Antigravity
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PLUGIN_ROOT.parent

# Add paths to sys.path so imports work
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from bridge.auth import AntigravityAuthManager, get_hermes_dir
    from bridge.server import (
        DEFAULT_BRIDGE_HOST,
        DEFAULT_BRIDGE_PORT,
        get_log_file,
        get_pid_file,
        is_server_running,
        bridge_launch_command,
    )
except ImportError:
    from tools.antigravity_bridge.auth import AntigravityAuthManager, get_hermes_dir
    from tools.antigravity_bridge.server import (
        DEFAULT_BRIDGE_HOST,
        DEFAULT_BRIDGE_PORT,
        get_log_file,
        get_pid_file,
        is_server_running,
        bridge_launch_command,
    )


def cmd_start(args: argparse.Namespace) -> int:
    port = args.port or DEFAULT_BRIDGE_PORT
    host = args.host or DEFAULT_BRIDGE_HOST
    try:
        cmd, package_root = bridge_launch_command(host, port)
    except ValueError as exc:
        print(f"[-] {exc}")
        return 2
    pid_file = get_pid_file()
    log_file = get_log_file()

    if is_server_running(host, port):
        print(f"[*] Antigravity Bridge is already running on http://{host}:{port}")
        return 0

    if getattr(args, "foreground", False):
        print(f"[*] Starting Antigravity Bridge in foreground on http://{host}:{port}...")
        try:
            from bridge.server import run_server
        except ImportError:
            from tools.antigravity_bridge.server import run_server
        run_server(host=host, port=port)
        return 0

    print(f"[*] Starting Antigravity Bridge daemon on http://{host}:{port}...")

    log_fd = open(log_file, "a", encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"

    flags = 0
    if sys.platform == "win32":
        flags = 0x00000008 | 0x00000200 | 0x01000000

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(package_root),
            stdout=log_fd,
            stderr=log_fd,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            env=env,
        )
    except Exception:
        # creationflags chỉ hợp lệ trên Windows — retry kiểu này ở POSIX sẽ
        # ném ValueError che mất lỗi gốc.
        if sys.platform != "win32":
            raise
        flags = 0x00000008 | 0x00000200
        proc = subprocess.Popen(
            cmd,
            cwd=str(package_root),
            stdout=log_fd,
            stderr=log_fd,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            env=env,
        )

    log_fd.close()  # The child owns its duplicated log handles.

    with open(pid_file, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))

    deadline = time.time() + 10.0
    while time.time() < deadline:
        if proc.poll() is not None:
            pid_file.unlink(missing_ok=True)
            print("[-] Bridge exited before becoming healthy. Check logs at:", log_file)
            return 1
        if is_server_running(host, port):
            print(f"[+] Antigravity Bridge started successfully (PID: {proc.pid})")
            print(f"    Endpoint: http://{host}:{port}/v1")
            print(f"    Logs:     {log_file}")
            return 0
        time.sleep(0.3)

    print("[-] Bridge process started but healthcheck timed out. Check logs at:", log_file)
    return 1


def cmd_stop(args: argparse.Namespace) -> int:
    pid_file = get_pid_file()
    if not pid_file.is_file():
        print("[*] No active bridge PID file found.")
        return 0

    try:
        with open(pid_file, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
    except Exception:
        pid = 0

    if pid > 0:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
            print(f"[+] Stopped Antigravity Bridge (PID: {pid})")
        except Exception as e:
            print(f"[*] Process {pid} not running or failed to stop: {e}")

    pid_file.unlink(missing_ok=True)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    port = args.port or DEFAULT_BRIDGE_PORT
    host = args.host or DEFAULT_BRIDGE_HOST

    running = is_server_running(host, port)
    auth_mgr = AntigravityAuthManager()
    creds = auth_mgr.load_stored_credentials() or auth_mgr.discover_local_tokens()

    print("=" * 60)
    print("       HERMES MULTI-PROVIDER BRIDGE STATUS REPORT       ")
    print("=" * 60)
    print(f"  Server Running:  {'YES [ONLINE]' if running else 'NO [OFFLINE]'}")
    print(f"  Listening On:    http://{host}:{port}/v1")
    print(f"  PID File:        {get_pid_file()}")
    print(f"  Log File:        {get_log_file()}")
    print("-" * 60)
    print("  [1] Google Antigravity (OAuth):")
    if creds:
        print(f"      Status:      AUTHENTICATED ({creds.email or 'Primary User'})")
        print(f"      Project ID:  {creds.project_id or 'auto-detected'}")
        if creds.expires_at:
            exp_str = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(creds.expires_at))
            status_text = "EXPIRED (Will auto-refresh)" if creds.is_expired else "VALID"
            print(f"      Token Expiry:{exp_str} [{status_text}]")
    else:
        print(f"      Status:      NOT LOGGED IN (Run 'python manage.py login')")

    print("-" * 60)
    print("  [2] Claude Code CLI (Subscription):")
    claude_bin = shutil.which("claude")
    print(f"      CLI Binary:  {'INSTALLED' if claude_bin else 'NOT FOUND'}")
    try:
        from bridge.account_pool import get_pool
        claude_pool = get_pool("claude-code")
        print(f"      Accounts:    {claude_pool.count()} total, {claude_pool.active_count()} active")
    except Exception:
        pass

    print("-" * 60)
    print("  [3] OpenAI Codex CLI (Subscription):")
    codex_bin = shutil.which("codex")
    print(f"      CLI Binary:  {'INSTALLED' if codex_bin else 'NOT FOUND'}")
    try:
        from bridge.account_pool import get_pool
        codex_pool = get_pool("codex")
        print(f"      Accounts:    {codex_pool.count()} total, {codex_pool.active_count()} active")
    except Exception:
        pass

    print("=" * 60)
    return 0 if running else 1


def cmd_login(args: argparse.Namespace) -> int:
    print("[*] Starting Google OAuth PKCE login flow for Antigravity...")
    auth_mgr = AntigravityAuthManager()
    try:
        creds = auth_mgr.login_interactive(open_browser=not args.no_browser)
        print("\n[+] Login successful!")
        print(f"    Account:    {creds.email}")
        print(f"    Project ID: {creds.project_id}")
        print(f"    Tokens:     {auth_mgr.token_file}")
        return 0
    except Exception as e:
        print(f"[-] Login failed: {e}")
        return 1


def _ensure_core_registrations() -> None:
    """Verify and ensure all core registrations for Antigravity are in place."""
    print("[*] Verifying core registrations for Antigravity (Dashboard, Models, OAuth)...")
    try:
        from hermes_cli.auth import PROVIDER_REGISTRY
        from hermes_cli.providers import HERMES_OVERLAYS
        from hermes_cli.models import _PROVIDER_MODELS, CANONICAL_PROVIDERS

        has_auth = "antigravity" in PROVIDER_REGISTRY
        has_overlay = "antigravity" in HERMES_OVERLAYS
        has_models = "antigravity" in _PROVIDER_MODELS
        has_canonical = any(p.slug == "antigravity" for p in CANONICAL_PROVIDERS)

        if has_auth and has_overlay and has_models and has_canonical:
            print("    [+] All core registries verified: Auth, Models, Overlays, and Catalog are ACTIVE.")
        else:
            print(f"    [!] Core status: Auth={has_auth}, Overlay={has_overlay}, Models={has_models}, Canonical={has_canonical}")
    except Exception as exc:
        print(f"    [!] Registry check notice: {exc}")


def cmd_install(args: argparse.Namespace) -> int:
    """Install provider plugin to ~/.hermes/plugins/model-providers/antigravity/ for upgrade survival."""
    hermes_dir = get_hermes_dir()
    dest_plugin_dir = hermes_dir / "plugins" / "model-providers" / "antigravity"
    src_plugin_dir = PLUGIN_ROOT / "plugin"
    dest_bridge_dir = hermes_dir / "bridge" / "antigravity" / "tools" / "antigravity_bridge"
    src_bridge_dir = PLUGIN_ROOT / "bridge"

    print(f"[*] Installing Antigravity provider plugin to {dest_plugin_dir}...")
    dest_plugin_dir.mkdir(parents=True, exist_ok=True)
    for item in src_plugin_dir.glob("*"):
        if item.is_file():
            shutil.copy2(item, dest_plugin_dir / item.name)
            print(f"    Copied {item.name}")

    print(f"[*] Copying bridge module to {dest_bridge_dir}...")
    if src_bridge_dir.is_dir():
        dest_bridge_dir.parent.mkdir(parents=True, exist_ok=True)
        if dest_bridge_dir.exists():
            shutil.rmtree(dest_bridge_dir, ignore_errors=True)
        shutil.copytree(src_bridge_dir, dest_bridge_dir)
        print("    Copied bridge runtime engine.")
    elif dest_bridge_dir.is_dir():
        # This manager is already running from the installed layout. The
        # installed runtime is its only source, so never remove it while
        # trying to perform an upgrade/setup operation.
        print("    Running from installed layout; retained existing bridge runtime engine.")
    else:
        print("[-] Bridge runtime source is unavailable; installation was not changed.")
        return 1

    # Also copy the manager script to ~/.hermes/bridge/antigravity/ unless it
    # is already the installed script (copying a file onto itself raises).
    manager_dest = hermes_dir / "bridge" / "antigravity" / "manage.py"
    if Path(__file__).resolve() != manager_dest.resolve():
        shutil.copy2(Path(__file__), manager_dest)
        print(f"    Copied management script to {manager_dest}")
    else:
        print("    Running installed management script; no copy needed.")

    _ensure_core_registrations()
    print("[+] Plugin & Bridge installed! It is now permanently persistent across Hermes upgrades.")
    return 0


DEFAULT_OPENAI_FALLBACK_MODEL = "gpt-5-codex"
DEFAULT_ANTHROPIC_FALLBACK_MODEL = "claude-sonnet-4-6"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_FALLBACK_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OLLAMA_FALLBACK_MODEL = "qwen2.5-coder:7b"
DEFAULT_FREE_TIER_ANTIGRAVITY_FALLBACKS = [
    "gemini-3.7-flash-medium",
    "gemini-3.5-flash",
]
DEFAULT_CLAUDE_CODE_CLI_MODEL = "sonnet"


def configure_claude_code_cli(hermes_dir: Path, *, model: str = DEFAULT_CLAUDE_CODE_CLI_MODEL, port: int = DEFAULT_BRIDGE_PORT) -> Path:
    """Select the local Claude Code subscription bridge as Hermes' primary model."""
    import yaml

    config_file = hermes_dir / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if config_file.exists():
        config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    config["model"] = {
        "provider": "claude-code-cli",
        "default": model,
        "base_url": f"http://127.0.0.1:{port}/v1/claude-code",
    }
    existing = config.get("fallback_providers")
    if isinstance(existing, list):
        config["fallback_providers"] = [
            item for item in existing
            if not (isinstance(item, dict) and item.get("provider") == "claude-code-cli")
        ]
    with open(config_file, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle, default_flow_style=False)
    return config_file


def cmd_setup_claude_code(args: argparse.Namespace) -> int:
    """Configure Hermes to call the authenticated local Claude Code CLI."""
    hermes_dir = get_hermes_dir()
    cmd_install(args)
    env_file = hermes_dir / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    if "CLAUDE_CODE_CLI_KEY=" not in env_content:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write("\n# Local Claude Code subscription bridge (not an Anthropic API key)\nCLAUDE_CODE_CLI_KEY=local-claude-code-bridge\n")
    model = getattr(args, "model", None) or DEFAULT_CLAUDE_CODE_CLI_MODEL
    port = getattr(args, "port", None) or DEFAULT_BRIDGE_PORT
    configure_claude_code_cli(hermes_dir, model=model, port=port)
    print(f"[+] Hermes now uses Claude Code CLI ({model}) at http://127.0.0.1:{port}/v1/claude-code")
    if not shutil.which("claude"):
        print("[!] Claude Code CLI was not found. Install it, then run `claude auth login`.")
    else:
        print("[*] Run `claude auth login` once to authenticate your Claude subscription before chatting.")
    return 0


DEFAULT_CODEX_CLI_MODEL = "gpt-6-astra"


def configure_codex_cli(
    hermes_dir: Path,
    *,
    model: str = DEFAULT_CODEX_CLI_MODEL,
    port: int = DEFAULT_BRIDGE_PORT,
) -> Path:
    """Select the local OpenAI Codex CLI subscription bridge as Hermes' primary model."""
    import yaml

    config_file = hermes_dir / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config: dict = {}
    if config_file.exists():
        config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    config["model"] = {
        "provider": "codex-cli",
        "default": model,
        "base_url": f"http://127.0.0.1:{port}/v1/codex",
    }
    existing = config.get("fallback_providers")
    if isinstance(existing, list):
        config["fallback_providers"] = [
            item for item in existing
            if not (isinstance(item, dict) and item.get("provider") == "codex-cli")
        ]
    with open(config_file, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle, default_flow_style=False)
    return config_file


def cmd_setup_codex(args: argparse.Namespace) -> int:
    """Configure Hermes to call the authenticated local OpenAI Codex CLI."""
    hermes_dir = get_hermes_dir()
    cmd_install(args)
    env_file = hermes_dir / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    if "CODEX_CLI_KEY=" not in env_content:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(
                "\n# Local OpenAI Codex subscription bridge (not an OpenAI API key)\nCODEX_CLI_KEY=local-codex-bridge\n"
            )
    model = getattr(args, "model", None) or DEFAULT_CODEX_CLI_MODEL
    port = getattr(args, "port", None) or DEFAULT_BRIDGE_PORT
    configure_codex_cli(hermes_dir, model=model, port=port)
    print(f"[+] Hermes now uses Codex CLI ({model}) at http://127.0.0.1:{port}/v1/codex")
    if not shutil.which("codex"):
        print("[!] Codex CLI was not found. Install it with `npm install -g @openai/codex`, then run `codex login`.")
    else:
        print("[*] Ensure you have run `codex login` once before chatting.")
    return 0


def cmd_accounts(args: argparse.Namespace) -> int:
    """List all accounts in the pool for a provider, with status and rate limit countdown."""
    provider = getattr(args, "provider", "codex")
    try:
        from bridge.account_pool import get_pool
    except ImportError:
        from tools.antigravity_bridge.account_pool import get_pool

    pool = get_pool(provider)
    status = pool.status_dict()
    accounts = status.get("accounts", [])
    print(
        f"\nAccount Pool: {provider.upper()} "
        f"(Total: {status['total_accounts']}, Active: {status['active_accounts']}, "
        f"Rate-Limited: {status.get('rate_limited_accounts', 0)})"
    )
    if not accounts:
        print(f"  No accounts registered yet. Run `python manage.py add-account {provider}` to add one.")
        return 0

    print("-" * 92)
    print(f"{'ID':<4} {'Name':<14} {'Status':<36} {'Reqs':<6} {'Fails':<6} {'Notes'}")
    print("-" * 92)
    for a in accounts:
        print(
            f"{a['id']:<4} {a['name']:<14} {a['status']:<36} "
            f"{a['total_requests']:<6} {a['total_failures']:<6} {a.get('notes', '')}"
        )
    print("-" * 92)
    if status.get("nearest_reset_seconds"):
        print(f"[*] Nearest rate-limit reset in {status['nearest_reset_seconds']}s")
    return 0


def cmd_add_account(args: argparse.Namespace) -> int:
    """Add a new account slot to the pool and show login instructions."""
    provider = getattr(args, "provider", "codex")
    name = getattr(args, "name", None)
    notes = getattr(args, "notes", "")
    try:
        from bridge.account_pool import get_pool
    except ImportError:
        from tools.antigravity_bridge.account_pool import get_pool

    pool = get_pool(provider)
    account = pool.add_account(name=name, notes=notes)
    print(f"\n[+] Created account slot #{account.id}: '{account.name}'")
    print(f"    Config Dir: {account.config_dir}")
    print("\nTo authenticate this account, run in your terminal:")
    print("-" * 65)
    print(pool.login_instructions(account).strip())
    print("-" * 65)
    return 0


def cmd_reset_limit(args: argparse.Namespace) -> int:
    """Clear rate limit cooldown for a specific account."""
    provider = getattr(args, "provider", "codex")
    account_id = getattr(args, "account_id", 1)
    try:
        from bridge.account_pool import get_pool
    except ImportError:
        from tools.antigravity_bridge.account_pool import get_pool

    pool = get_pool(provider)
    ok = pool.clear_rate_limit(account_id)
    if ok:
        print(f"[+] Cleared rate limit for {provider} account #{account_id}.")
    else:
        print(f"[-] Account #{account_id} not found in {provider} pool.")
    return 0



def apply_priority_fallback_config(
    config_data: dict,
    *,
    antigravity_model: str = "gemini-3.7-flash",
    antigravity_base_url: str | None = None,
    openai_model: str = DEFAULT_OPENAI_FALLBACK_MODEL,
    anthropic_model: str = DEFAULT_ANTHROPIC_FALLBACK_MODEL,
    set_primary: bool = True,
    groq_model: str | None = None,
    groq_base_url: str = DEFAULT_GROQ_BASE_URL,
    ollama_model: str | None = None,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    free_tier_only: bool = False,
) -> dict:
    """Set the recommended zero-touch failover chain:
    - Standard paid: antigravity -> openai-codex -> anthropic (-> groq) (-> local ollama)
    - 100% Zero-Cost Free Tier (when ``free_tier_only=True``):
      antigravity primary -> antigravity secondary models -> groq (cloud 0đ) -> ollama (local offline 0đ).

    Mutates and returns ``config_data`` (a parsed ``config.yaml`` dict).
    ``set_primary=False`` leaves ``model.provider``/``model.default`` untouched
    (useful when the user already has a different primary provider configured)
    while still appending the antigravity/openai-codex/anthropic fallback
    entries so a rate limit on the current primary automatically rotates
    through them.

    Never duplicates a ``(provider, model)`` pair already present in
    ``fallback_providers`` — existing unrelated entries are preserved.
    """
    port = DEFAULT_BRIDGE_PORT
    base_url = antigravity_base_url or f"http://127.0.0.1:{port}/v1"

    if set_primary:
        if not isinstance(config_data.get("model"), dict):
            config_data["model"] = {}
        config_data["model"]["provider"] = "antigravity"
        config_data["model"]["default"] = antigravity_model
        config_data["model"]["base_url"] = base_url

    if free_tier_only:
        free_antigravity_models = [
            m for m in DEFAULT_FREE_TIER_ANTIGRAVITY_FALLBACKS
            if m.lower() != antigravity_model.lower()
        ]
        priority_entries = [
            {"provider": "antigravity", "model": m}
            for m in free_antigravity_models
        ]
        if not set_primary:
            priority_entries.insert(0, {"provider": "antigravity", "model": antigravity_model})
        if groq_model is None:
            groq_model = DEFAULT_GROQ_FALLBACK_MODEL
        if ollama_model is None:
            ollama_model = DEFAULT_OLLAMA_FALLBACK_MODEL
    else:
        if set_primary:
            priority_entries = [
                {"provider": "openai-codex", "model": openai_model},
                {"provider": "anthropic", "model": anthropic_model},
            ]
        else:
            priority_entries = [
                {"provider": "antigravity", "model": antigravity_model},
                {"provider": "openai-codex", "model": openai_model},
                {"provider": "anthropic", "model": anthropic_model},
            ]

    existing = config_data.get("fallback_providers")
    chain = list(existing) if isinstance(existing, list) else []

    if free_tier_only:
        # Strip paid subscription providers (openai-codex, anthropic, claude-code-cli)
        chain = [
            entry
            for entry in chain
            if not (
                isinstance(entry, dict)
                and str(entry.get("provider") or "").strip().lower()
                in ("openai-codex", "anthropic", "claude-code-cli")
            )
        ]
        # When antigravity is primary, remove any antigravity fallback entry targeting the same primary model
        if set_primary:
            chain = [
                entry
                for entry in chain
                if not (
                    isinstance(entry, dict)
                    and str(entry.get("provider") or "").strip().lower() == "antigravity"
                    and str(entry.get("model") or "").strip().lower() == antigravity_model.lower()
                )
            ]
        seen_keys = {
            (str(e.get("provider") or "").strip().lower(), str(e.get("model") or "").strip().lower())
            for e in chain
            if isinstance(e, dict)
        }
        for entry in priority_entries:
            key = (entry["provider"].lower(), entry["model"].lower())
            if key in seen_keys:
                continue
            chain.append(entry)
            seen_keys.add(key)
    else:
        # A provider must never appear both as the primary and as a fallback.
        # That duplicate creates a pointless retry loop when setup/install is run
        # again after Antigravity has already been selected as primary.
        if set_primary:
            chain = [
                entry
                for entry in chain
                if not (
                    isinstance(entry, dict)
                    and str(entry.get("provider") or "").strip().lower() == "antigravity"
                )
            ]
        # Upsert by provider only (not (provider, model)): a future default-model
        # bump, or the user's own manual model choice for an already-present
        # provider, must UPDATE that single entry in place rather than appending
        # a second entry for the same provider. Whichever value the entry already
        # holds — including one the user hand-edited via `hermes fallback add` —
        # wins; we only add a NEW entry when the provider isn't present yet.
        seen_providers = {
            str(e.get("provider") or "").strip().lower()
            for e in chain
            if isinstance(e, dict)
        }
        for entry in priority_entries:
            key = entry["provider"].lower()
            if key in seen_providers:
                continue
            chain.append(entry)
            seen_providers.add(key)

    # "custom" is shared by every generic OpenAI-compatible endpoint (Groq,
    # Ollama, LM Studio, vLLM, llama.cpp) — dedupe each by (provider,
    # base_url), not by provider alone, or a pre-existing unrelated "custom"
    # entry (e.g. the user's own LM Studio fallback) would block one of
    # these, or one of these would clobber it.
    if groq_model:
        already_present = any(
            isinstance(e, dict)
            and str(e.get("provider") or "").strip().lower() == "custom"
            and str(e.get("base_url") or "").strip() == groq_base_url
            for e in chain
        )
        if not already_present:
            chain.append({
                "provider": "custom",
                "model": groq_model,
                "base_url": groq_base_url,
            })

    if ollama_model:
        already_present = any(
            isinstance(e, dict)
            and str(e.get("provider") or "").strip().lower() == "custom"
            and str(e.get("base_url") or "").strip() == ollama_base_url
            for e in chain
        )
        if not already_present:
            chain.append({
                "provider": "custom",
                "model": ollama_model,
                "base_url": ollama_base_url,
            })

    config_data["fallback_providers"] = chain
    config_data.pop("fallback_model", None)
    return config_data


def configure_priority_fallback_preserving_existing_primary(
    hermes_dir: Path,
    *,
    antigravity_model: str = "gemini-3.7-flash",
    port: int | None = None,
    openai_model: str = DEFAULT_OPENAI_FALLBACK_MODEL,
    anthropic_model: str = DEFAULT_ANTHROPIC_FALLBACK_MODEL,
    groq_model: str | None = None,
    groq_base_url: str = DEFAULT_GROQ_BASE_URL,
    ollama_model: str | None = None,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    free_tier_only: bool = False,
) -> Path:
    """Upgrade-safe wrapper for ``configure_priority_fallback``.

    Sets antigravity as the primary provider ONLY when ``config.yaml`` has no
    existing ``model.provider`` (a genuinely fresh install). If the user
    already configured a different primary provider — e.g. a prior install,
    or a manual ``hermes model`` choice — that primary is left untouched and
    antigravity is appended to the fallback chain instead, so re-running
    ``install.py`` on an upgrade never silently resets the primary provider.
    """
    import yaml

    config_file = hermes_dir / "config.yaml"
    existing_config: dict = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            existing_config = yaml.safe_load(f) or {}

    existing_provider = ""
    if isinstance(existing_config.get("model"), dict):
        existing_provider = str(existing_config["model"].get("provider") or "").strip()
    has_existing_primary = bool(existing_provider)

    return configure_priority_fallback(
        hermes_dir,
        antigravity_model=antigravity_model,
        port=port,
        openai_model=openai_model,
        anthropic_model=anthropic_model,
        set_primary=(not has_existing_primary or existing_provider.lower() == "antigravity"),
        groq_model=groq_model,
        groq_base_url=groq_base_url,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
        free_tier_only=free_tier_only,
    )


def configure_priority_fallback(
    hermes_dir: Path,
    *,
    antigravity_model: str = "gemini-3.7-flash",
    port: int | None = None,
    openai_model: str = DEFAULT_OPENAI_FALLBACK_MODEL,
    anthropic_model: str = DEFAULT_ANTHROPIC_FALLBACK_MODEL,
    set_primary: bool = True,
    groq_model: str | None = None,
    groq_base_url: str = DEFAULT_GROQ_BASE_URL,
    ollama_model: str | None = None,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    free_tier_only: bool = False,
) -> Path:
    """Load, update, and persist ``<hermes_dir>/config.yaml`` with the
    failover chain.

    Returns the path to the written config file.
    """
    import yaml

    config_file = hermes_dir / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_data: dict = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    base_url = f"http://127.0.0.1:{port or DEFAULT_BRIDGE_PORT}/v1"
    apply_priority_fallback_config(
        config_data,
        antigravity_model=antigravity_model,
        antigravity_base_url=base_url,
        openai_model=openai_model,
        anthropic_model=anthropic_model,
        set_primary=set_primary,
        groq_model=groq_model,
        groq_base_url=groq_base_url,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
        free_tier_only=free_tier_only,
    )

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    return config_file


def cmd_setup(args: argparse.Namespace) -> int:
    """Configure Hermes config.yaml and .env to use Antigravity, with
    automatic zero-touch cross-provider failover by default."""
    hermes_dir = get_hermes_dir()
    config_file = hermes_dir / "config.yaml"
    env_file = hermes_dir / ".env"

    cmd_install(args)

    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_content = ""
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            env_content = f.read()

    if "ANTIGRAVITY_API_KEY" not in env_content:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write("\n# Antigravity Local OAuth Bridge Key\nANTIGRAVITY_API_KEY=antigravity-local-token\n")
        print("[+] Added ANTIGRAVITY_API_KEY to ~/.hermes/.env")

    model_name = args.model or "gemini-3.7-flash"
    port = args.port or DEFAULT_BRIDGE_PORT

    if getattr(args, "no_fallback", False):
        base_url = f"http://127.0.0.1:{port}/v1"
        print(f"[*] Configuring Hermes (~/.hermes/config.yaml)...")
        try:
            import yaml
            config_data = {}
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

            if "model" not in config_data or not isinstance(config_data["model"], dict):
                config_data["model"] = {}

            config_data["model"]["default"] = model_name
            config_data["model"]["provider"] = "antigravity"
            config_data["model"]["base_url"] = base_url

            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False)
            print(f"[+] Hermes configured to use Antigravity:")
            print(f"    model.provider: antigravity")
            print(f"    model.default:  {model_name}")
            print(f"    model.base_url: {base_url}")
        except Exception as e:
            print(f"[-] Failed to update config.yaml: {e}")
            return 1
        return 0

    free_tier = getattr(args, "free_tier", False)
    if free_tier:
        groq_model = getattr(args, "groq_model", None) or DEFAULT_GROQ_FALLBACK_MODEL
        groq_base_url = getattr(args, "groq_base_url", None) or DEFAULT_GROQ_BASE_URL
        ollama_model = getattr(args, "ollama_model", None) or DEFAULT_OLLAMA_FALLBACK_MODEL
        ollama_base_url = getattr(args, "ollama_base_url", None) or DEFAULT_OLLAMA_BASE_URL
    else:
        groq_model = getattr(args, "groq_model", None)
        groq_base_url = getattr(args, "groq_base_url", None) or DEFAULT_GROQ_BASE_URL
        ollama_model = getattr(args, "ollama_model", None)
        ollama_base_url = getattr(args, "ollama_base_url", None) or DEFAULT_OLLAMA_BASE_URL

    as_fallback_only = getattr(args, "as_fallback_only", False)
    banner_label = "100% Zero-Cost Free Tier" if free_tier else "automatic failover"
    print(f"[*] Configuring Hermes (~/.hermes/config.yaml) with {banner_label}...")
    try:
        configure_priority_fallback(
            hermes_dir,
            antigravity_model=model_name,
            port=port,
            # `setup` is an explicit request to make Antigravity active. The
            # installer preserves an existing primary on upgrades; callers who
            # want that behavior here must opt in with --as-fallback-only.
            set_primary=not as_fallback_only,
            groq_model=groq_model,
            groq_base_url=groq_base_url,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
            free_tier_only=free_tier,
        )
        if free_tier:
            print("[+] Hermes configured with 100% Zero-Cost Free Tier failover chain:")
            hops = ["antigravity (unchanged primary)" if as_fallback_only else f"antigravity ({model_name})"]
            for m in DEFAULT_FREE_TIER_ANTIGRAVITY_FALLBACKS:
                if m.lower() != model_name.lower():
                    hops.append(f"antigravity   ({m})")
            hops.append(f"groq (cloud, custom)   ({groq_model} @ {groq_base_url})")
            hops.append(f"ollama (local, custom) ({ollama_model} @ {ollama_base_url})")
            if as_fallback_only:
                for i, hop in enumerate(hops, start=1):
                    print(f"    {i}. {hop}")
            else:
                print(f"    Primary:  {hops[0]} — {_pool_account_count()} Google account(s) rotate internally on rate limit")
                for i, hop in enumerate(hops[1:], start=1):
                    print(f"    Fallback {i}: {hop}")
            print("    [!] 100% Zero-Cost: No credit card or paid subscriptions required.")
            print("    [*] Groq Free Tier: Get free key at https://console.groq.com and set GROQ_API_KEY in ~/.hermes/.env")
            print(f"    [*] Ollama Offline: Pull '{ollama_model}' for local offline emergency fallback ('ollama pull {ollama_model}').")
            print("    Run 'hermes fallback list' to inspect or 'hermes fallback remove' to adjust.")
        else:
            print("[+] Hermes configured with zero-touch failover chain:")
            hops = ["antigravity (unchanged primary)" if as_fallback_only else f"antigravity ({model_name})"]
            hops.append(f"openai-codex  ({DEFAULT_OPENAI_FALLBACK_MODEL})")
            hops.append(f"anthropic     ({DEFAULT_ANTHROPIC_FALLBACK_MODEL})")
            if groq_model:
                hops.append(f"groq (cloud, custom)   ({groq_model} @ {groq_base_url})")
            if ollama_model:
                hops.append(f"ollama (local, custom) ({ollama_model} @ {ollama_base_url})")
            if as_fallback_only:
                for i, hop in enumerate(hops, start=1):
                    print(f"    {i}. {hop}")
            else:
                print(f"    Primary:  {hops[0]} — {_pool_account_count()} Google account(s) rotate internally on rate limit")
                for i, hop in enumerate(hops[1:], start=1):
                    print(f"    Fallback {i}: {hop}")
            if groq_model:
                print("    Groq is a fast/cheap CLOUD hop (still needs internet) — set GROQ_API_KEY in")
                print("    ~/.hermes/.env; Hermes derives it automatically from the api.groq.com host.")
            if ollama_model:
                print("    Ollama is a LAST-RESORT OFFLINE hop, tried after groq — a 7B local model is")
                print("    much less reliable at multi-step tool-calling than the cloud providers above;")
                print(f"    make sure 'ollama serve' is running and '{ollama_model}' is pulled")
                print(f"    ('ollama pull {ollama_model}').")
            print("    No manual action needed — Hermes rotates automatically on rate limit / quota / auth failure.")
            print("    Run 'hermes fallback list' to inspect or 'hermes fallback remove' to adjust.")
    except Exception as e:
        print(f"[-] Failed to update config.yaml: {e}")
        return 1

    return 0


def cmd_setup_free(args: argparse.Namespace) -> int:
    """Shortcut command to configure Hermes with 100% Zero-Cost Free Tier."""
    setattr(args, "free_tier", True)
    setattr(args, "no_fallback", False)
    if not hasattr(args, "groq_model") or getattr(args, "groq_model", None) is None:
        setattr(args, "groq_model", DEFAULT_GROQ_FALLBACK_MODEL)
    if not hasattr(args, "groq_base_url") or getattr(args, "groq_base_url", None) is None:
        setattr(args, "groq_base_url", DEFAULT_GROQ_BASE_URL)
    if not hasattr(args, "ollama_model") or getattr(args, "ollama_model", None) is None:
        setattr(args, "ollama_model", DEFAULT_OLLAMA_FALLBACK_MODEL)
    if not hasattr(args, "ollama_base_url") or getattr(args, "ollama_base_url", None) is None:
        setattr(args, "ollama_base_url", DEFAULT_OLLAMA_BASE_URL)
    return cmd_setup(args)


def _pool_account_count() -> int:
    """Best-effort count of stored Antigravity Google accounts, for the setup banner."""
    try:
        mgr = AntigravityAuthManager()
        return len(mgr.load_all_stored_credentials())
    except Exception:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Antigravity Local OAuth Bridge Manager for Hermes")
    subparsers = parser.add_subparsers(dest="action", required=True)

    p_start = subparsers.add_parser("start", help="Start the bridge server daemon")
    p_start.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT, help="Port to listen on")
    p_start.add_argument("--host", type=str, default=DEFAULT_BRIDGE_HOST, help="Host to bind")
    p_start.add_argument("--foreground", "-f", action="store_true", help="Run server in foreground")

    subparsers.add_parser("stop", help="Stop the bridge server")

    p_status = subparsers.add_parser("status", help="Show bridge and auth status")
    p_status.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    p_status.add_argument("--host", type=str, default=DEFAULT_BRIDGE_HOST)

    p_login = subparsers.add_parser("login", help="Log in with Google OAuth PKCE")
    p_login.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")

    subparsers.add_parser("install", help="Install provider plugin to ~/.hermes/ for upgrade persistence")

    p_setup_claude = subparsers.add_parser(
        "setup-claude-code", help="Use local Claude Code subscription CLI as the Hermes provider"
    )
    p_setup_claude.add_argument("--model", choices=("fable", "opus", "sonnet", "haiku"), default="sonnet")
    p_setup_claude.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)

    p_setup = subparsers.add_parser("setup", help="Auto-configure Hermes to use Antigravity")
    p_setup.add_argument("--model", type=str, default="gemini-3.7-flash", help="Default model name")
    p_setup.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    p_setup.add_argument(
        "--no-fallback",
        action="store_true",
        help="Set antigravity as the primary provider WITHOUT the automatic "
        "openai-codex/anthropic failover chain (legacy behavior).",
    )
    p_setup.add_argument(
        "--as-fallback-only",
        action="store_true",
        help="Do not change the current primary provider — only append "
        "antigravity, openai-codex, and anthropic to the fallback chain so "
        "the existing primary rotates through them automatically on failure.",
    )
    p_setup.add_argument(
        "--free-tier",
        action="store_true",
        help="Configure 100% Zero-Cost Free Tier failover chain (Google Antigravity -> Groq Cloud Free -> Ollama Local Offline), omitting paid providers.",
    )
    p_setup.add_argument(
        "--groq-model",
        type=str,
        default=None,
        help=f"Add a Groq Cloud model (default '{DEFAULT_GROQ_FALLBACK_MODEL}') to the "
        "fallback chain, right after openai-codex/anthropic — Groq is fast/cheap but "
        "still needs internet (it is NOT an offline fallback). Omit to leave it out "
        "(default). Requires GROQ_API_KEY in ~/.hermes/.env (Hermes derives it "
        "automatically from the api.groq.com host — no extra config needed).",
    )
    p_setup.add_argument(
        "--groq-base-url",
        type=str,
        default=DEFAULT_GROQ_BASE_URL,
        help=f"Base URL of the Groq OpenAI-compatible endpoint "
        f"(default: {DEFAULT_GROQ_BASE_URL}). Only used when --groq-model is set.",
    )
    p_setup.add_argument(
        "--ollama-model",
        type=str,
        default=None,
        help="Add a local Ollama model (e.g. 'qwen2.5:7b-instruct') as the LAST "
        "hop in the fallback chain, for offline/last-resort use when antigravity, "
        "openai-codex, anthropic, AND groq have all failed (or there is no network "
        "at all). Omit to leave it out (recommended default) — a 7B local model is "
        "not reliable enough for primary/early-hop tool-calling orchestration. "
        "Requires 'ollama serve' running locally with the model already pulled.",
    )
    p_setup.add_argument(
        "--ollama-base-url",
        type=str,
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"Base URL of the local Ollama OpenAI-compatible endpoint "
        f"(default: {DEFAULT_OLLAMA_BASE_URL}). Only used when --ollama-model is set.",
    )

    p_setup_free = subparsers.add_parser(
        "setup-free",
        help="Configure Hermes with 100% Zero-Cost Free Tier (Antigravity OAuth + Groq Cloud + Ollama)",
    )
    p_setup_free.add_argument("--model", type=str, default="gemini-3.7-flash", help="Default primary model")
    p_setup_free.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    p_setup_free.add_argument(
        "--as-fallback-only",
        action="store_true",
        help="Do not change current primary provider — only configure free tier in fallback chain.",
    )
    p_setup_free.add_argument(
        "--groq-model",
        type=str,
        default=DEFAULT_GROQ_FALLBACK_MODEL,
        help=f"Groq Cloud model (default: {DEFAULT_GROQ_FALLBACK_MODEL})",
    )
    p_setup_free.add_argument(
        "--groq-base-url",
        type=str,
        default=DEFAULT_GROQ_BASE_URL,
        help=f"Base URL of Groq endpoint (default: {DEFAULT_GROQ_BASE_URL})",
    )
    p_setup_free.add_argument(
        "--ollama-model",
        type=str,
        default=DEFAULT_OLLAMA_FALLBACK_MODEL,
        help=f"Ollama local model (default: {DEFAULT_OLLAMA_FALLBACK_MODEL})",
    )
    p_setup_free.add_argument(
        "--ollama-base-url",
        type=str,
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"Base URL of Ollama endpoint (default: {DEFAULT_OLLAMA_BASE_URL})",
    )

    p_setup_codex = subparsers.add_parser(
        "setup-codex", help="Configure Hermes to use the local OpenAI Codex CLI bridge"
    )
    p_setup_codex.add_argument("--model", type=str, default=DEFAULT_CODEX_CLI_MODEL)
    p_setup_codex.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)

    p_accounts = subparsers.add_parser(
        "accounts", help="List accounts in the pool with status and rate-limit countdown"
    )
    p_accounts.add_argument("provider", choices=["codex", "claude-code"], default="codex", nargs="?")

    p_add_account = subparsers.add_parser(
        "add-account", help="Add a new subscription account to the rotation pool"
    )
    p_add_account.add_argument("provider", choices=["codex", "claude-code"], default="codex", nargs="?")
    p_add_account.add_argument("--name", type=str, default=None, help="Optional name for the account")
    p_add_account.add_argument("--notes", type=str, default="", help="Optional notes")

    p_reset_limit = subparsers.add_parser(
        "reset-limit", help="Clear rate limit cooldown for an account"
    )
    p_reset_limit.add_argument("provider", choices=["codex", "claude-code"], default="codex", nargs="?")
    p_reset_limit.add_argument("account_id", type=int, default=1, nargs="?")

    args = parser.parse_args()

    handlers = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "login": cmd_login,
        "install": cmd_install,
        "setup": cmd_setup,
        "setup-free": cmd_setup_free,
        "setup-claude-code": cmd_setup_claude_code,
        "setup-codex": cmd_setup_codex,
        "accounts": cmd_accounts,
        "add-account": cmd_add_account,
        "reset-limit": cmd_reset_limit,
    }
    return handlers[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
