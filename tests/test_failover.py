"""Behavior tests for Antigravity multi-account failover."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import types
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import httpx

ROOT = Path(__file__).resolve().parents[1]

# Load source files under their installed package identity without executing
# bridge/__init__.py, which intentionally imports the installed layout.
tools_pkg = types.ModuleType("tools")
tools_pkg.__path__ = []
bridge_pkg = types.ModuleType("tools.antigravity_bridge")
bridge_pkg.__path__ = [str(ROOT / "bridge")]
sys.modules.setdefault("tools", tools_pkg)
sys.modules.setdefault("tools.antigravity_bridge", bridge_pkg)


def load_bridge_module(name: str):
    qualified = f"tools.antigravity_bridge.{name}"
    spec = importlib.util.spec_from_file_location(qualified, ROOT / "bridge" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


bridge_auth = load_bridge_module("auth")
bridge_client = load_bridge_module("client")
AntigravityClient = bridge_client.AntigravityClient


class FakeAuthManager:
    def __init__(self) -> None:
        self.accounts = [
            bridge_auth.AntigravityCredentials(
                access_token="token-a", email="a@example.com", project_id="project-a"
            ),
            bridge_auth.AntigravityCredentials(
                access_token="token-b", email="b@example.com", project_id="project-b"
            ),
        ]
        self.marked: list[tuple[str, int]] = []

    def resolve_valid_credentials(self, bearer_token: str = ""):
        return self.accounts[0]

    def resolve_credential_candidates(self, bearer_token: str = ""):
        return list(self.accounts)

    def mark_account_unavailable(
        self, creds: bridge_auth.AntigravityCredentials, status_code: int, retry_after=None
    ) -> None:
        self.marked.append((creds.email, status_code))


class MultiAccountFailoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_nonstream_model_fallback_tries_claude_before_rotating_account(
        self,
    ) -> None:
        # gemini-3.7-flash hits a rate limit on account #1's Gemini quota;
        # the SAME account still has Claude quota available. The in-account
        # model fallback should try claude-sonnet-4-6 on the same account
        # BEFORE rotating to a different Google account.
        auth = FakeAuthManager()
        seen: list[tuple[str, str]] = []  # (token, requested-model-in-body)

        primary_model = bridge_client.map_model_name("gemini-3.7-flash")
        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            body = json.loads(request.content)
            model = body.get("model", "")
            seen.append((token, model))
            if token == "token-a" and model == primary_model:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "60"},
                    json={"error": {"message": "RESOURCE_EXHAUSTED"}},
                )
            if token == "token-a" and model == "claude-sonnet-4-6":
                return httpx.Response(
                    200,
                    json={
                        "response": {
                            "candidates": [
                                {"content": {"parts": [{"text": "SAME_ACCOUNT_CLAUDE_OK"}]}}
                            ]
                        }
                    },
                )
            raise AssertionError(f"unexpected request: token={token} model={model}")

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.7-flash",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await client.close()

        self.assertEqual(
            result["choices"][0]["message"]["content"], "SAME_ACCOUNT_CLAUDE_OK"
        )
        self.assertEqual(
            seen, [( "token-a", primary_model), ("token-a", "claude-sonnet-4-6")]
        )
        # The account was NOT cooled down / rotated away from — it still had
        # usable Claude quota, so mark_account_unavailable must not fire.
        self.assertEqual(auth.marked, [])

    async def test_nonstream_429_rotates_to_next_account(self) -> None:
        auth = FakeAuthManager()
        seen_tokens: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            seen_tokens.append(token)
            if token == "token-a":
                return httpx.Response(
                    429,
                    headers={"Retry-After": "60"},
                    json={"error": {"message": "RESOURCE_EXHAUSTED"}},
                )
            return httpx.Response(
                200,
                json={
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "SECOND_ACCOUNT_OK"}]}}
                        ]
                    }
                },
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.7-flash",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await client.close()

        self.assertEqual(
            result["choices"][0]["message"]["content"], "SECOND_ACCOUNT_OK"
        )
        self.assertEqual(seen_tokens, ["token-a", "token-a", "token-b"])
        self.assertEqual(auth.marked, [("a@example.com", 429)])

    async def test_nonstream_401_rotates_to_next_account(self) -> None:
        auth = FakeAuthManager()
        seen_tokens: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            seen_tokens.append(token)
            if token == "token-a":
                return httpx.Response(401, json={"error": "invalid_token"})
            return httpx.Response(
                200,
                json={
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "AUTH_FAILOVER_OK"}]}}
                        ]
                    }
                },
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.7-flash",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await client.close()

        self.assertEqual(
            result["choices"][0]["message"]["content"], "AUTH_FAILOVER_OK"
        )
        self.assertEqual(seen_tokens, ["token-a", "token-a", "token-b"])
        self.assertEqual(auth.marked, [("a@example.com", 401)])

    async def test_nonstream_primary_5xx_tries_fallback_with_same_account(self) -> None:
        auth = FakeAuthManager()
        seen_requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            seen_requests.append((request.url.host, token))
            if request.url.host == "daily-cloudcode-pa.googleapis.com":
                return httpx.Response(503, json={"error": "temporarily unavailable"})
            return httpx.Response(
                200,
                json={
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "FALLBACK_OK"}]}}
                        ]
                    }
                },
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.7-flash",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await client.close()

        self.assertEqual(result["choices"][0]["message"]["content"], "FALLBACK_OK")
        self.assertEqual(
            seen_requests,
            [
                ("daily-cloudcode-pa.googleapis.com", "token-a"),
                ("cloudcode-pa.googleapis.com", "token-a"),
            ],
        )
        self.assertEqual(auth.marked, [])

    async def test_resource_exhausted_body_rotates_to_next_account(self) -> None:
        auth = FakeAuthManager()
        seen_tokens: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            seen_tokens.append(token)
            if token == "token-a":
                return httpx.Response(
                    400, json={"error": {"status": "RESOURCE_EXHAUSTED"}}
                )
            return httpx.Response(
                200,
                json={
                    "response": {
                        "candidates": [
                            {"content": {"parts": [{"text": "QUOTA_FAILOVER_OK"}]}}
                        ]
                    }
                },
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.7-flash",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )
        finally:
            await client.close()

        self.assertEqual(
            result["choices"][0]["message"]["content"], "QUOTA_FAILOVER_OK"
        )
        self.assertEqual(seen_tokens, ["token-a", "token-a", "token-b"])
        self.assertEqual(auth.marked, [("a@example.com", 400)])

    async def test_stream_429_rotates_before_yielding(self) -> None:
        auth = FakeAuthManager()
        seen_tokens: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            token = request.headers["Authorization"].removeprefix("Bearer ")
            seen_tokens.append(token)
            if token == "token-a":
                return httpx.Response(
                    429,
                    headers={"Retry-After": "60"},
                    json={"error": {"message": "RESOURCE_EXHAUSTED"}},
                )
            event = {
                "response": {
                    "candidates": [
                        {"content": {"parts": [{"text": "SECOND_STREAM_OK"}]}}
                    ]
                }
            }
            body = f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n"
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=body.encode(),
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            chunks = [
                chunk
                async for chunk in client.stream_chat_completion(
                    {
                        "model": "gemini-3.7-flash",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": True,
                    }
                )
            ]
        finally:
            await client.close()

        self.assertIn("SECOND_STREAM_OK", "".join(chunks))
        self.assertEqual(seen_tokens, ["token-a", "token-b"])
        self.assertEqual(auth.marked, [("a@example.com", 429)])

    async def test_stream_5xx_rotates_accounts_without_cooldown(self) -> None:
        # 5xx là lỗi phía Google: thử tài khoản kế tiếp (không cooldown),
        # hết tài khoản mới báo lỗi — đồng bộ với đường non-stream.
        auth = FakeAuthManager()
        seen_tokens: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_tokens.append(
                request.headers["Authorization"].removeprefix("Bearer ")
            )
            return httpx.Response(503, json={"error": "temporarily unavailable"})

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with self.assertRaisesRegex(
                RuntimeError, "streaming failed with HTTP 503"
            ):
                async for _ in client.stream_chat_completion(
                    {
                        "model": "gemini-3.7-flash",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": True,
                    }
                ):
                    pass
        finally:
            await client.close()

        self.assertEqual(seen_tokens, ["token-a", "token-b"])
        self.assertEqual(auth.marked, [])

    async def test_stream_tool_call_finish_reason_is_not_overwritten_by_synthetic_stop(
        self,
    ) -> None:
        # Bug đã sửa: sau khi Gemini gửi finishReason="STOP" kèm functionCall
        # (dịch sang finish_reason="tool_calls"), bridge từng LUÔN nối thêm một
        # chunk rỗng finish_reason="stop" ở cuối stream — ghi đè lên tín hiệu
        # tool_calls thật, khiến client OpenAI-compat tưởng hội thoại đã xong
        # và bỏ qua lệnh gọi tool.
        auth = FakeAuthManager()

        def handler(request: httpx.Request) -> httpx.Response:
            event = {
                "response": {
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "search",
                                            "args": {"q": "hermes"},
                                        }
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
            body = f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n"
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=body.encode(),
            )

        client = AntigravityClient(auth)
        await client._http.aclose()
        client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            chunks = [
                chunk
                async for chunk in client.stream_chat_completion(
                    {
                        "model": "gemini-3.7-flash",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": True,
                    }
                )
            ]
        finally:
            await client.close()

        finish_reasons = [
            json.loads(c[len("data: "):])["choices"][0]["finish_reason"]
            for c in chunks
            if c.startswith("data: {")
        ]
        self.assertEqual(finish_reasons, [None, "tool_calls"])


class AccountPoolTests(unittest.TestCase):
    def test_custom_auth_file_never_writes_global_auth_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_file = root / "isolated" / "tokens.json"
            fake_global = root / "global"
            fake_home = root / "home"
            manager = bridge_auth.AntigravityAuthManager(auth_file=custom_file)
            creds = bridge_auth.AntigravityCredentials(
                access_token="test-token",
                refresh_token="test-refresh",
                email="isolated@example.com",
                project_id="test-project",
            )

            with mock.patch.object(
                bridge_auth, "get_hermes_dir", return_value=fake_global
            ), mock.patch.object(bridge_auth.Path, "home", return_value=fake_home):
                manager.save_credentials(creds)

            self.assertTrue(custom_file.is_file())
            self.assertFalse((fake_global / "auth.json").exists())
            self.assertFalse((fake_home / ".hermes" / "auth.json").exists())

    def test_concurrent_cooldowns_for_two_accounts_both_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            first = bridge_auth.AntigravityCredentials(
                access_token="token-a", email="a@example.com", project_id="project-a"
            )
            second = bridge_auth.AntigravityCredentials(
                access_token="token-b", email="b@example.com", project_id="project-b"
            )
            accounts = {
                first.email: first.to_dict(),
                second.email: second.to_dict(),
            }
            for index in range(1000):
                filler = bridge_auth.AntigravityCredentials(
                    access_token=f"filler-token-{index}",
                    email=f"filler-{index}@example.com",
                    project_id=f"filler-project-{index}",
                )
                accounts[filler.email] = filler.to_dict()
            initial = first.to_dict()
            initial["accounts"] = accounts
            token_file.write_text(json.dumps(initial), encoding="utf-8")

            start = threading.Barrier(3)
            errors: list[BaseException] = []

            def mark(creds, status_code: int) -> None:
                try:
                    start.wait()
                    manager.mark_account_unavailable(creds, status_code)
                except BaseException as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=mark, args=(first, 401)),
                threading.Thread(target=mark, args=(second, 429)),
            ]
            for thread in threads:
                thread.start()
            start.wait()
            for thread in threads:
                thread.join(timeout=5)

            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            stored = json.loads(token_file.read_text(encoding="utf-8"))["accounts"]
            self.assertEqual(stored[first.email]["last_failure_status"], 401)
            self.assertGreater(stored[first.email]["unavailable_until"], 0)
            self.assertEqual(stored[second.email]["last_failure_status"], 429)
            self.assertGreater(stored[second.email]["unavailable_until"], 0)

    def test_cooldown_persists_and_excludes_rate_limited_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            first = bridge_auth.AntigravityCredentials(
                access_token="token-a", email="a@example.com", project_id="project-a"
            )
            second = bridge_auth.AntigravityCredentials(
                access_token="token-b", email="b@example.com", project_id="project-b"
            )
            manager.save_credentials(first)
            manager.save_credentials(second)

            with self.assertLogs(bridge_auth.logger, level="WARNING"):
                manager.mark_account_unavailable(first, 429, retry_after="60")

            reloaded = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            candidates = reloaded.resolve_credential_candidates()
            self.assertEqual([c.email for c in candidates], ["b@example.com"])
            stored = json.loads(token_file.read_text(encoding="utf-8"))
            limited = stored["accounts"]["a@example.com"]
            self.assertEqual(limited["last_failure_status"], 429)
            self.assertGreater(limited["unavailable_until"], 0)

    def test_refresh_failure_cools_account_and_uses_next(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            first = bridge_auth.AntigravityCredentials(
                access_token="expired-token",
                refresh_token="bad-refresh",
                expires_at=1,
                email="a@example.com",
                project_id="project-a",
            )
            second = bridge_auth.AntigravityCredentials(
                access_token="token-b",
                expires_at=0,
                email="b@example.com",
                project_id="project-b",
            )
            manager.save_credentials(first)
            manager.save_credentials(second)

            def fail_refresh(_creds):
                # Google từ chối refresh token (invalid_grant) = HTTPError 400
                raise urllib.error.HTTPError(
                    "https://oauth2.googleapis.com/token", 400, "invalid_grant", {}, None
                )

            manager.refresh_access_token = fail_refresh
            with self.assertLogs(bridge_auth.logger, level="WARNING") as captured:
                candidates = manager.resolve_credential_candidates()

            self.assertEqual([c.email for c in candidates], ["b@example.com"])
            stored = json.loads(token_file.read_text(encoding="utf-8"))
            failed = stored["accounts"]["a@example.com"]
            self.assertEqual(failed["last_failure_status"], 401)
            self.assertNotIn("expired-token", "\n".join(captured.output))
            self.assertNotIn("bad-refresh", "\n".join(captured.output))

    def test_transient_refresh_error_skips_without_cooldown(self) -> None:
        # Lỗi mạng tạm thời khi refresh KHÔNG được cooldown tài khoản —
        # đây chính là bug "chạy ~1h thì chết cả pool" (token hết hạn sau 1h,
        # một nhịp mạng chập chờn từng làm nguội mọi tài khoản 5 phút).
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            first = bridge_auth.AntigravityCredentials(
                access_token="expired-token",
                refresh_token="refresh-a",
                expires_at=1,
                email="a@example.com",
                project_id="project-a",
            )
            second = bridge_auth.AntigravityCredentials(
                access_token="token-b",
                expires_at=0,
                email="b@example.com",
                project_id="project-b",
            )
            manager.save_credentials(first)
            manager.save_credentials(second)

            def fail_refresh(_creds):
                raise TimeoutError("network timed out")

            manager.refresh_access_token = fail_refresh
            with self.assertLogs(bridge_auth.logger, level="WARNING"):
                candidates = manager.resolve_credential_candidates()

            self.assertEqual([c.email for c in candidates], ["b@example.com"])
            stored = json.loads(token_file.read_text(encoding="utf-8"))
            skipped = stored["accounts"]["a@example.com"]
            # Không cooldown: tài khoản sẵn sàng thử lại ngay lượt sau
            self.assertEqual(skipped.get("unavailable_until", 0), 0)

    def test_all_cooled_accounts_report_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            accounts = [
                bridge_auth.AntigravityCredentials(
                    access_token=f"token-{name}",
                    email=f"{name}@example.com",
                    project_id=f"project-{name}",
                )
                for name in ("a", "b")
            ]
            with self.assertLogs(bridge_auth.logger, level="WARNING"):
                for account in accounts:
                    manager.save_credentials(account)
                    manager.mark_account_unavailable(account, 429, retry_after="60")

            with self.assertRaisesRegex(
                RuntimeError, "All Antigravity OAuth accounts are unavailable"
            ):
                manager.resolve_credential_candidates()

    def test_bearer_token_prioritizes_matching_available_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "antigravity_tokens.json"
            manager = bridge_auth.AntigravityAuthManager(auth_file=token_file)
            for name in ("a", "b"):
                manager.save_credentials(
                    bridge_auth.AntigravityCredentials(
                        access_token=f"token-{name}",
                        email=f"{name}@example.com",
                        project_id=f"project-{name}",
                    )
                )

            candidates = manager.resolve_credential_candidates(
                bearer_token="token-b"
            )
            self.assertEqual(
                [candidate.email for candidate in candidates],
                ["b@example.com", "a@example.com"],
            )


if __name__ == "__main__":
    unittest.main()
