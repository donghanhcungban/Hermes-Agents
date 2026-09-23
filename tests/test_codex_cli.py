"""Tests for the OpenAI Codex CLI bridge adapter and multi-account rate limit management."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.account_pool import (
    AccountEntry,
    AccountPool,
    extract_cooldown,
)
from bridge.codex import (
    CODEX_MODEL_ALIASES,
    CODEX_SUPPORTED_MODELS,
    CodexCliClient,
    CodexCliError,
    _build_prompt,
    _extract_text_from_jsonl,
    _output_schema,
)


class CooldownExtractionTests(unittest.TestCase):
    def test_parses_relative_minutes(self) -> None:
        sec, reason = extract_cooldown("Rate limit reached. Try again in 20 minutes.")
        self.assertEqual(sec, 1200.0)
        self.assertIn("20", reason)

    def test_parses_relative_seconds(self) -> None:
        sec, reason = extract_cooldown("Please wait 45s before trying again.")
        self.assertEqual(sec, 45.0)

    def test_parses_subscription_quota_keywords(self) -> None:
        sec, reason = extract_cooldown("You have reached your usage limit for GPT-4o.")
        self.assertEqual(sec, 3600.0)
        self.assertIn("quota", reason.lower())

    def test_burst_rate_limit_fallback(self) -> None:
        sec, reason = extract_cooldown("429 Too Many Requests")
        self.assertEqual(sec, 60.0)


class AccountPoolRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.pool = AccountPool("codex", hermes_dir=self.tmp_dir)

    def test_add_and_list_accounts(self) -> None:
        a1 = self.pool.add_account("primary")
        a2 = self.pool.add_account("backup")
        self.assertEqual(self.pool.count(), 2)
        self.assertEqual(a1.id, 1)
        self.assertEqual(a2.id, 2)

    def test_record_rate_limit_and_cooldown(self) -> None:
        a1 = self.pool.add_account("primary")
        self.assertTrue(a1.is_available)

        # Trigger rate limit
        self.pool.record_rate_limit(a1.id, "Try again in 10 minutes", cooldown_seconds=600.0)
        self.assertTrue(a1.is_rate_limited)
        self.assertFalse(a1.is_available)
        self.assertIn("RATE_LIMITED", a1.status_string)

        # Clear rate limit
        self.pool.clear_rate_limit(a1.id)
        self.assertFalse(a1.is_rate_limited)
        self.assertTrue(a1.is_available)

    def test_pick_skips_rate_limited_account(self) -> None:
        a1 = self.pool.add_account("limited")
        a2 = self.pool.add_account("healthy")

        self.pool.record_rate_limit(a1.id, "429 limit", cooldown_seconds=300.0)

        # Should consistently pick a2 since a1 is in cooldown
        chosen1 = self.pool.pick()
        chosen2 = self.pool.pick()
        self.assertIsNotNone(chosen1)
        self.assertIsNotNone(chosen2)
        self.assertEqual(chosen1.id, a2.id)
        self.assertEqual(chosen2.id, a2.id)

    def test_pick_with_exclude_ids(self) -> None:
        a1 = self.pool.add_account("acc1")
        a2 = self.pool.add_account("acc2")

        chosen = self.pool.pick(exclude_ids={a1.id})
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.id, a2.id)


class CodexCliClientTests(unittest.TestCase):
    def test_catalog_has_required_models(self) -> None:
        model_ids = {m["id"] for m in CODEX_SUPPORTED_MODELS}
        self.assertIn("gpt-6-astra", model_ids)
        self.assertIn("o3-mini", model_ids)
        self.assertIn("gpt-4o", model_ids)

    def test_extract_text_from_jsonl(self) -> None:
        jsonl = (
            '{"type": "item.completed", "item": {"type": "agent_message", "text": "{\\"content\\": \\"Hello!\\"}"}}\n'
        )
        text = _extract_text_from_jsonl(jsonl)
        self.assertEqual(text, '{"content": "Hello!"}')

    def test_returns_openai_content_from_structured_cli_result(self) -> None:
        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            self.assertIn("Xin chào", prompt)
            jsonl = (
                '{"type": "item.completed", "item": {"type": "agent_message", '
                '"text": "{\\"content\\": \\"Chào bạn từ Codex!\\", \\"tool_calls\\": []}"}}\n'
            )
            return 0, jsonl, ""

        client = CodexCliClient(runner=runner, use_account_pool=False)
        response = asyncio.run(
            client.create_chat_completion(
                {"model": "gpt-6-astra", "messages": [{"role": "user", "content": "Xin chào"}]}
            )
        )
        self.assertEqual(response["choices"][0]["message"]["content"], "Chào bạn từ Codex!")
        self.assertEqual(response["choices"][0]["finish_reason"], "stop")

    def test_transparent_failover_on_429(self) -> None:
        """When account 1 hits 429 rate limit, client should transparently retry with account 2."""
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        pool = AccountPool("codex", hermes_dir=tmp_dir)
        a1 = pool.add_account("account-1")
        a2 = pool.add_account("account-2")

        calls_per_env: list[str] = []

        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            codex_home = (extra_env or {}).get("CODEX_HOME", "")
            calls_per_env.append(codex_home)

            if "account-1" in codex_home:
                # Account 1 fails with rate limit
                return 1, "", "Rate limit reached. Try again in 15 minutes."

            # Account 2 succeeds
            jsonl = (
                '{"type": "item.completed", "item": {"type": "agent_message", '
                '"text": "{\\"content\\": \\"Thành công từ account-2!\\", \\"tool_calls\\": []}"}}\n'
            )
            return 0, jsonl, ""

        client = CodexCliClient(runner=runner, use_account_pool=True)
        # Patch client's _get_pool to return our test pool
        client._get_pool = lambda: pool

        response = asyncio.run(
            client.create_chat_completion(
                {"model": "gpt-6-astra", "messages": [{"role": "user", "content": "test failover"}]}
            )
        )

        # Verified: account 1 was tried first, then account 2
        self.assertEqual(len(calls_per_env), 2)
        self.assertIn("account-1", calls_per_env[0])
        self.assertIn("account-2", calls_per_env[1])

        # Response came from account 2 seamlessly
        self.assertEqual(response["choices"][0]["message"]["content"], "Thành công từ account-2!")

        # Account 1 is now in cooldown
        self.assertTrue(a1.is_rate_limited)
        # Account 2 is healthy
        self.assertFalse(a2.is_rate_limited)

    def test_all_accounts_rate_limited_raises_429_with_hint(self) -> None:
        """When all accounts are rate-limited, raise 429 with nearest reset info."""
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        pool = AccountPool("codex", hermes_dir=tmp_dir)
        pool.add_account("account-1")

        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            return 1, "", "Rate limit reached. Try again in 10 minutes."

        client = CodexCliClient(runner=runner, use_account_pool=True)
        client._get_pool = lambda: pool

        with self.assertRaises(CodexCliError) as ctx:
            asyncio.run(
                client.create_chat_completion(
                    {"model": "gpt-6-astra", "messages": [{"role": "user", "content": "test"}]}
                )
            )

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("rate-limited", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
