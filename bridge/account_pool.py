"""Account Pool Manager for CLI subscription providers with Rate Limit Cooldown & Auto-Failover.

Each provider (claude-code, codex) can have N accounts registered.
Accounts are stored under:
  {hermes_dir}/accounts/{provider}/account-{N}/

Account isolation is achieved via environment variables:
  - Codex CLI:       CODEX_HOME={account_dir}
  - Claude Code CLI: CLAUDE_HOME={account_dir}

Features:
  1. Round-robin rotation across active accounts
  2. Smart Rate Limit Detection & Cooldown:
     - Parses relative wait times ("wait 15m", "try again in 20 minutes")
     - Parses clock reset times ("until 3:15 PM", "resets at 18:30")
     - Sets default cooldowns (3600s for subscription quota, 60s for burst)
  3. Transparent Failover:
     - When an account hits 429, it enters cooldown and the client retries
       with the next active account transparently.
  4. State Tracking:
     - ACTIVE, RATE_LIMITED (with remaining seconds), AUTH_REQUIRED, SUSPENDED, DISABLED
  5. Persistence in {hermes_dir}/accounts/{provider}/registry.json
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROVIDER_ENV_VAR = {
    "codex": "CODEX_HOME",
    "claude-code": "CLAUDE_HOME",
}

# Max consecutive non-429 failures before an account is suspended
MAX_CONSECUTIVE_FAILURES = 3
# How long (seconds) a suspended account is skipped before retried
SUSPENSION_TTL_SECONDS = 300.0

# Default cooldown durations (seconds)
DEFAULT_BURST_RATE_LIMIT_COOLDOWN = 60.0       # 1 minute for burst rate limits
DEFAULT_QUOTA_RATE_LIMIT_COOLDOWN = 3600.0     # 1 hour for subscription message/usage caps


# ---------------------------------------------------------------------------
# Smart Cooldown Parsing
# ---------------------------------------------------------------------------


def extract_cooldown(detail: str) -> tuple[float, str]:
    """Parse CLI stderr/stdout to determine the best cooldown duration in seconds.

    Returns:
        (cooldown_seconds, reason_description)
    """
    d = (detail or "").lower()

    # 1. Check relative duration: 'in 15 minutes', 'wait 45s', 'try again in 2 hours'
    m_rel = re.search(
        r"(?:try again in|wait|in)\s+(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?)",
        d,
    )
    if m_rel:
        val = int(m_rel.group(1))
        unit = m_rel.group(2)
        if unit.startswith("s"):
            sec = float(val)
        elif unit.startswith("m"):
            sec = float(val * 60)
        else:
            sec = float(val * 3600)
        return max(5.0, sec), f"Cooldown {val} {unit}"

    # 2. Check clock reset time: 'until 3:15 pm', 'resets at 18:30', 'until 12:00am'
    m_clock = re.search(
        r"(?:until|resets?\s+(?:at|in))\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([ap]\.?m\.?)?",
        d,
    )
    if m_clock:
        hr = int(m_clock.group(1))
        minute = int(m_clock.group(2))
        ampm = m_clock.group(4)
        if ampm:
            ampm = ampm.replace(".", "")
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
        now = datetime.datetime.now()
        target = now.replace(hour=hr, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        diff = (target - now).total_seconds()
        return max(5.0, diff), f"Resets at {hr:02d}:{minute:02d}"

    # 3. Quota / usage cap exhaustion keywords (subscription limits)
    quota_keywords = [
        "usage limit", "message limit", "quota", "cap reached",
        "monthly limit", "plan limit", "reached your limit",
    ]
    if any(k in d for k in quota_keywords):
        return DEFAULT_QUOTA_RATE_LIMIT_COOLDOWN, "Subscription quota reached (default 1h cooldown)"

    # 4. Short burst rate limit fallback
    return DEFAULT_BURST_RATE_LIMIT_COOLDOWN, "Rate limit burst (default 60s cooldown)"


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------


@dataclass
class AccountEntry:
    id: int                           # 1-based numeric ID
    name: str                         # human name, e.g. "account-1"
    config_dir: str                   # absolute path to isolated config dir
    enabled: bool = True
    total_requests: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    suspended_until: float = 0.0      # epoch timestamp; 0 = not suspended

    # Rate-limit management
    rate_limited_until: float = 0.0   # epoch timestamp; 0 = not rate limited
    rate_limit_reason: str = ""
    rate_limit_count: int = 0

    # Auth status
    auth_valid: bool = True
    auth_error: str = ""

    added_at: float = field(default_factory=time.time)
    notes: str = ""

    @property
    def is_suspended(self) -> bool:
        return self.suspended_until > time.time()

    @property
    def is_rate_limited(self) -> bool:
        return self.rate_limited_until > time.time()

    @property
    def is_available(self) -> bool:
        """Available for immediate use."""
        return self.enabled and self.auth_valid and not self.is_rate_limited and not self.is_suspended

    @property
    def remaining_cooldown_seconds(self) -> int:
        now = time.time()
        if self.rate_limited_until > now:
            return max(0, int(self.rate_limited_until - now))
        if self.suspended_until > now:
            return max(0, int(self.suspended_until - now))
        return 0

    @property
    def status_string(self) -> str:
        if not self.enabled:
            return "DISABLED"
        if not self.auth_valid:
            return "AUTH_REQUIRED"
        if self.is_rate_limited:
            return f"RATE_LIMITED ({self.remaining_cooldown_seconds}s remaining)"
        if self.is_suspended:
            return f"SUSPENDED ({self.remaining_cooldown_seconds}s remaining)"
        return "ACTIVE"

    def suspend(self) -> None:
        self.suspended_until = time.time() + SUSPENSION_TTL_SECONDS
        logger.warning(
            "Account %s suspended for %.0fs after %d consecutive failures.",
            self.name, SUSPENSION_TTL_SECONDS, self.consecutive_failures,
        )

    def unsuspend(self) -> None:
        self.suspended_until = 0.0
        self.consecutive_failures = 0

    def set_rate_limit(self, cooldown_seconds: float, reason: str = "") -> None:
        self.rate_limited_until = time.time() + cooldown_seconds
        self.rate_limit_reason = reason
        self.rate_limit_count += 1
        logger.warning(
            "Account '%s' entered rate-limit cooldown for %.0fs (%s).",
            self.name, cooldown_seconds, reason,
        )

    def clear_rate_limit(self) -> None:
        self.rate_limited_until = 0.0
        self.rate_limit_reason = ""


def _entry_from_dict(d: dict) -> AccountEntry:
    return AccountEntry(
        id=d["id"],
        name=d["name"],
        config_dir=d["config_dir"],
        enabled=d.get("enabled", True),
        total_requests=d.get("total_requests", 0),
        total_failures=d.get("total_failures", 0),
        consecutive_failures=d.get("consecutive_failures", 0),
        suspended_until=d.get("suspended_until", 0.0),
        rate_limited_until=d.get("rate_limited_until", 0.0),
        rate_limit_reason=d.get("rate_limit_reason", ""),
        rate_limit_count=d.get("rate_limit_count", 0),
        auth_valid=d.get("auth_valid", True),
        auth_error=d.get("auth_error", ""),
        added_at=d.get("added_at", 0.0),
        notes=d.get("notes", ""),
    )


# ---------------------------------------------------------------------------
# Account Pool
# ---------------------------------------------------------------------------


class AccountPool:
    """Round-robin pool of subscription CLI accounts with smart rate-limit management."""

    def __init__(self, provider: str, hermes_dir: Optional[Path] = None) -> None:
        self.provider = provider
        self._lock = threading.RLock()
        self._rr_index = 0
        self._accounts: list[AccountEntry] = []
        self._registry_path = self._resolve_registry(hermes_dir)
        self._load()

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _resolve_registry(self, hermes_dir: Optional[Path]) -> Path:
        if hermes_dir is None:
            try:
                from bridge.auth import get_hermes_dir
            except ImportError:
                from tools.antigravity_bridge.auth import get_hermes_dir
            hermes_dir = get_hermes_dir()
        accounts_dir = hermes_dir / "accounts" / self.provider
        accounts_dir.mkdir(parents=True, exist_ok=True)
        return accounts_dir / "registry.json"

    def _account_config_dir(self, account_id: int) -> Path:
        return self._registry_path.parent / f"account-{account_id}"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._registry_path.is_file():
            return
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            self._accounts = [_entry_from_dict(e) for e in data.get("accounts", [])]
        except Exception as exc:
            logger.warning("Failed to load account pool registry %s: %s", self._registry_path, exc)

    def _save(self) -> None:
        try:
            payload = {
                "provider": self.provider,
                "updated_at": time.time(),
                "accounts": [asdict(a) for a in self._accounts],
            }
            content = json.dumps(payload, indent=2, ensure_ascii=False)
            tmp = self._registry_path.with_suffix(".tmp")
            tmp.write_text(content, encoding="utf-8")
            try:
                os.replace(tmp, self._registry_path)
            except OSError:
                time.sleep(0.01)
                try:
                    os.replace(tmp, self._registry_path)
                except OSError:
                    self._registry_path.write_text(content, encoding="utf-8")
                    with contextlib.suppress(OSError):
                        tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("Failed to save account pool registry: %s", exc)

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._accounts)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for a in self._accounts if a.is_available)

    def list_accounts(self) -> list[AccountEntry]:
        with self._lock:
            return list(self._accounts)

    def get_account(self, account_id: int) -> Optional[AccountEntry]:
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    return a
        return None

    def add_account(self, name: Optional[str] = None, notes: str = "") -> AccountEntry:
        """Register a new account slot, creating its isolated config dir."""
        with self._lock:
            existing_ids = {a.id for a in self._accounts}
            new_id = 1
            while new_id in existing_ids:
                new_id += 1

            auto_name = name or f"account-{new_id}"
            config_dir = self._account_config_dir(new_id)
            config_dir.mkdir(parents=True, exist_ok=True)

            # Seed existing global credentials for the first account slot so the user
            # does not have to log in again if already authenticated globally.
            if new_id == 1:
                self._seed_existing_credentials(config_dir)

            entry = AccountEntry(
                id=new_id,
                name=auto_name,
                config_dir=str(config_dir),
                added_at=time.time(),
                notes=notes,
            )
            self._accounts.append(entry)
            self._save()
            return entry

    def _seed_existing_credentials(self, target_dir: Path) -> None:
        """Seed the first account slot with the current user's active CLI credentials."""
        import shutil
        if self.provider == "codex":
            src = Path.home() / ".codex"
            if src.is_dir():
                for fname in ("auth.json", "config.toml"):
                    src_file = src / fname
                    if src_file.is_file():
                        with contextlib.suppress(Exception):
                            shutil.copy2(src_file, target_dir / fname)
                            logger.info("Auto-seeded existing Codex credentials to %s", target_dir)
        elif self.provider == "claude-code":
            for candidate in (Path.home() / ".claude", Path.home() / ".claude.json"):
                if candidate.is_file():
                    with contextlib.suppress(Exception):
                        shutil.copy2(candidate, target_dir / candidate.name)
                elif candidate.is_dir():
                    with contextlib.suppress(Exception):
                        shutil.copytree(candidate, target_dir / candidate.name, dirs_exist_ok=True)

    def remove_account(self, account_id: int) -> bool:
        """Disable an account by ID."""
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.enabled = False
                    self._save()
                    return True
        return False

    def enable_account(self, account_id: int) -> bool:
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.enabled = True
                    a.unsuspend()
                    a.clear_rate_limit()
                    a.auth_valid = True
                    self._save()
                    return True
        return False

    # ------------------------------------------------------------------
    # Rate limit and failure tracking
    # ------------------------------------------------------------------

    def record_rate_limit(
        self,
        account_id: int,
        detail: str = "",
        cooldown_seconds: Optional[float] = None,
    ) -> tuple[float, str]:
        """Mark an account as rate-limited, automatically calculating cooldown duration.

        Returns (cooldown_seconds, reason).
        """
        if cooldown_seconds is None:
            cooldown_seconds, reason = extract_cooldown(detail)
        else:
            reason = f"Explicit cooldown {cooldown_seconds:.0f}s"

        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.total_requests += 1
                    a.total_failures += 1
                    a.set_rate_limit(cooldown_seconds, reason)
                    self._save()
                    break
        return cooldown_seconds, reason

    def clear_rate_limit(self, account_id: int) -> bool:
        """Manually clear rate limit cooldown for an account."""
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.clear_rate_limit()
                    a.auth_valid = True
                    self._save()
                    logger.info("Cleared rate limit for account %s.", a.name)
                    return True
        return False

    def record_auth_error(self, account_id: int, error: str = "") -> None:
        """Mark an account as requiring authentication (HTTP 401)."""
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.auth_valid = False
                    a.auth_error = error[:256]
                    self._save()
                    logger.warning("Account %s marked AUTH_REQUIRED: %s", a.name, error)
                    return

    def record_success(self, account_id: int) -> None:
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.total_requests += 1
                    a.consecutive_failures = 0
                    if a.is_suspended:
                        a.unsuspend()
                    if a.is_rate_limited:
                        a.clear_rate_limit()
                    a.auth_valid = True
                    self._save()
                    return

    def record_failure(self, account_id: int) -> None:
        """Record general non-429 error (network, syntax, crash)."""
        with self._lock:
            for a in self._accounts:
                if a.id == account_id:
                    a.total_requests += 1
                    a.total_failures += 1
                    a.consecutive_failures += 1
                    if a.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        a.suspend()
                    self._save()
                    return

    # ------------------------------------------------------------------
    # Selection logic with Failover Support
    # ------------------------------------------------------------------

    def pick(self, exclude_ids: Optional[set[int]] = None) -> Optional[AccountEntry]:
        """Pick the next available account round-robin.

        *exclude_ids*: set of account IDs already tried in the current request turn.
        Returns None if no suitable account is found.
        """
        exclude_ids = exclude_ids or set()
        with self._lock:
            # Only consider enabled, non-excluded accounts
            candidates = [a for a in self._accounts if a.enabled and a.id not in exclude_ids]
            if not candidates:
                return None

            # Primary filter: completely available (not rate limited, not suspended, auth valid)
            available = [a for a in candidates if a.is_available]

            if not available:
                return None

            # Round-robin cursor
            self._rr_index = self._rr_index % len(available)
            chosen = available[self._rr_index]
            self._rr_index = (self._rr_index + 1) % len(available)
            return chosen

    def get_nearest_reset_seconds(self) -> Optional[int]:
        """If all accounts are rate-limited, return seconds until the earliest reset."""
        with self._lock:
            limited = [a for a in self._accounts if a.enabled and a.is_rate_limited]
            if not limited:
                return None
            earliest = min(limited, key=lambda a: a.rate_limited_until)
            now = time.time()
            return max(1, int(earliest.rate_limited_until - now))

    def env_for(self, account: Optional[AccountEntry]) -> dict[str, str]:
        """Return env var overrides to isolate this account's CLI config."""
        if not account:
            return {}
        env_var = PROVIDER_ENV_VAR.get(self.provider)
        if not env_var:
            return {}
        return {env_var: account.config_dir}

    # ------------------------------------------------------------------
    # Status report
    # ------------------------------------------------------------------

    def status_dict(self) -> dict:
        with self._lock:
            accounts_info = []
            for a in self._accounts:
                accounts_info.append({
                    "id": a.id,
                    "name": a.name,
                    "enabled": a.enabled,
                    "status": a.status_string,
                    "is_rate_limited": a.is_rate_limited,
                    "rate_limited_until": a.rate_limited_until if a.is_rate_limited else None,
                    "rate_limit_remaining_seconds": a.remaining_cooldown_seconds if a.is_rate_limited else 0,
                    "rate_limit_reason": a.rate_limit_reason if a.is_rate_limited else "",
                    "rate_limit_count": a.rate_limit_count,
                    "is_suspended": a.is_suspended,
                    "suspended_remaining_seconds": a.remaining_cooldown_seconds if a.is_suspended else 0,
                    "auth_valid": a.auth_valid,
                    "auth_error": a.auth_error if not a.auth_valid else "",
                    "consecutive_failures": a.consecutive_failures,
                    "total_requests": a.total_requests,
                    "total_failures": a.total_failures,
                    "config_dir": a.config_dir,
                    "notes": a.notes,
                })

            active_cnt = sum(1 for a in self._accounts if a.is_available)
            limited_cnt = sum(1 for a in self._accounts if a.enabled and a.is_rate_limited)

            return {
                "provider": self.provider,
                "total_accounts": len(self._accounts),
                "active_accounts": active_cnt,
                "rate_limited_accounts": limited_cnt,
                "nearest_reset_seconds": self.get_nearest_reset_seconds(),
                "accounts": accounts_info,
            }

    def login_instructions(self, account: AccountEntry) -> str:
        """Return shell instructions to log in to this account slot."""
        env_var = PROVIDER_ENV_VAR.get(self.provider, "?")
        config_dir = account.config_dir

        if self.provider == "codex":
            if os.name == "nt":
                return (
                    f'# Authenticate Codex account "{account.name}" (PowerShell)\n'
                    f'$env:{env_var} = "{config_dir}"\n'
                    f'codex login\n'
                    f'# Once login completes, Hermes can use this account.\n'
                )
            return (
                f'# Authenticate Codex account "{account.name}" (bash/zsh)\n'
                f'export {env_var}="{config_dir}"\n'
                f'codex login\n'
                f'# Once login completes, Hermes can use this account.\n'
            )
        if self.provider == "claude-code":
            if os.name == "nt":
                return (
                    f'# Authenticate Claude Code account "{account.name}" (PowerShell)\n'
                    f'$env:{env_var} = "{config_dir}"\n'
                    f'claude login\n'
                    f'# Once login completes, Hermes can use this account.\n'
                )
            return (
                f'# Authenticate Claude Code account "{account.name}" (bash/zsh)\n'
                f'export {env_var}="{config_dir}"\n'
                f'claude login\n'
                f'# Once login completes, Hermes can use this account.\n'
            )
        return f"Set {env_var}={config_dir} then log in."


# ---------------------------------------------------------------------------
# Singleton per-provider pools (lazy, process-lifetime)
# ---------------------------------------------------------------------------

_pools: dict[str, AccountPool] = {}
_pools_lock = threading.Lock()


def get_pool(provider: str) -> AccountPool:
    """Return (or create) the singleton AccountPool for *provider*."""
    with _pools_lock:
        if provider not in _pools:
            _pools[provider] = AccountPool(provider)
        return _pools[provider]
