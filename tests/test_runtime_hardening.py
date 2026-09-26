"""Behavioral regressions with synthetic accounts/providers; no credentials or LLM calls."""
from __future__ import annotations
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp.test_utils import TestClient, TestServer
from bridge.account_pool import AccountPool
from bridge.claude_code import ClaudeCodeCliClient, ClaudeCodeCliError
from bridge.codex import CodexCliClient, CodexCliError
from bridge.server import AntigravityBridgeServer

PAYLOAD = {"messages": [{"role": "user", "content": "synthetic test"}]}


def output(provider, structured):
    if provider == "claude-code":
        return json.dumps({"structured_output": structured})
    return json.dumps({"type": "item.completed", "item": {
        "type": "agent_message", "text": json.dumps(structured)}}) + "\n"


class CliHardeningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.seed = patch.object(AccountPool, "_seed_existing_credentials")
        self.seed.start()
        self.addCleanup(self.seed.stop)

    def client(self, provider, structured=None):
        if structured is None:
            structured = {"content": "OK", "tool_calls": []}
        runner = AsyncMock(return_value=(0, output(provider, structured), ""))
        cls = ClaudeCodeCliClient if provider == "claude-code" else CodexCliClient
        return cls(runner=runner, use_account_pool=False), runner

    async def test_success_stops_after_one_provider_attempt(self):
        for provider in ("claude-code", "codex"):
            with self.subTest(provider=provider):
                pool = AccountPool(provider, hermes_dir=Path(self.tmp.name))
                pool.add_account("first")
                pool.add_account("second")
                client, runner = self.client(provider)
                client._get_pool = lambda: pool
                response = await client.create_chat_completion(PAYLOAD)
                self.assertEqual(response["choices"][0]["message"]["content"], "OK")
                self.assertEqual(runner.await_count, 1, "Success must not consume another account/request")

    async def test_exhausted_pool_never_falls_back_to_global_credentials(self):
        for provider in ("claude-code", "codex"):
            with self.subTest(provider=provider):
                pool = AccountPool(provider, hermes_dir=Path(self.tmp.name))
                account = pool.add_account("limited")
                pool.record_rate_limit(account.id, "synthetic", cooldown_seconds=600)
                client, runner = self.client(provider)
                client._get_pool = lambda: pool
                with self.assertRaises((ClaudeCodeCliError, CodexCliError)) as caught:
                    await client.create_chat_completion(PAYLOAD)
                self.assertEqual(caught.exception.status_code, 429)
                runner.assert_not_awaited()

    async def test_empty_tool_allowlist_rejects_calls(self):
        for provider in ("claude-code", "codex"):
            with self.subTest(provider=provider):
                client, _ = self.client(provider, {"content": "", "tool_calls": [{"name": "shell", "arguments": {}}]})
                with self.assertRaises((ClaudeCodeCliError, CodexCliError)):
                    await client.create_chat_completion(PAYLOAD)

    async def test_nonobject_or_invalid_tool_arguments_are_rejected(self):
        for provider in ("claude-code", "codex"):
            for arguments in ([], "[]", "invalid", None, 1):
                with self.subTest(provider=provider, arguments=arguments):
                    client, _ = self.client(provider, {"content": "", "tool_calls": [{"name": "safe", "arguments": arguments}]})
                    with self.assertRaises((ClaudeCodeCliError, CodexCliError)):
                        await client.create_chat_completion(PAYLOAD | {"tools": [{"type": "function", "function": {"name": "safe"}}]})

    async def test_wrong_structured_content_is_rejected(self):
        for provider in ("claude-code", "codex"):
            with self.subTest(provider=provider):
                client, _ = self.client(provider, {"content": ["not text"], "tool_calls": []})
                with self.assertRaises((ClaudeCodeCliError, CodexCliError)):
                    await client.create_chat_completion(PAYLOAD)

    async def test_claude_prefix_is_stripped_and_mcp_disabled(self):
        client, runner = self.client("claude-code")
        await client.create_chat_completion(PAYLOAD | {"model": "claude-code/sonnet"})
        command = runner.await_args.args[0]
        self.assertEqual(command[command.index("--model") + 1], "sonnet")
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(command[command.index("--setting-sources") + 1], "")

    def test_claude_account_uses_official_config_variable(self):
        pool = AccountPool("claude-code", hermes_dir=Path(self.tmp.name))
        account = pool.add_account("synthetic")
        self.assertEqual(pool.env_for(account).get("CLAUDE_CONFIG_DIR"), account.config_dir)
        self.assertIn("claude auth login", pool.login_instructions(account))


class HttpHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict("os.environ", {"HERMES_BRIDGE_ADMIN_TOKEN": "", "HERMES_BRIDGE_API_KEY": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.bridge = AntigravityBridgeServer(auth_manager=MagicMock())
        await self.bridge.client.close()
        self.bridge.client = MagicMock()
        self.bridge.client.close = AsyncMock()
        self.bridge.client.create_chat_completion = AsyncMock(return_value={"choices": []})
        self.bridge.client.list_models = AsyncMock(return_value=[])
        self.http = TestClient(TestServer(self.bridge.app))
        await self.http.start_server()
        self.addAsyncCleanup(self.http.close)

    async def test_bad_payload_shapes_return_400(self):
        for data in ([], None, {"messages": "wrong"}, PAYLOAD | {"stream": "false"}):
            with self.subTest(data=data):
                response = await self.http.post("/v1/chat/completions", data=json.dumps(data), headers={"Content-Type": "application/json"})
                self.assertEqual(response.status, 400)
        self.bridge.client.create_chat_completion.assert_not_awaited()

    async def test_browser_origin_is_rejected(self):
        response = await self.http.post("/v1/chat/completions", json=PAYLOAD, headers={"Origin": "https://untrusted.invalid"})
        self.assertEqual(response.status, 403)
        self.bridge.client.create_chat_completion.assert_not_awaited()

    async def test_foreign_host_is_rejected(self):
        response = await self.http.get("/health", headers={"Host": "untrusted.invalid"})
        self.assertEqual(response.status, 403)

    async def test_http_admin_disabled_by_default(self):
        response = await self.http.get("/auth/status")
        self.assertEqual(response.status, 403)

    async def test_loopback_inference_remains_compatible(self):
        response = await self.http.post("/v1/chat/completions", json=PAYLOAD)
        self.assertEqual(response.status, 200)

    async def test_provider_exception_does_not_leak_secrets(self):
        self.bridge.client.create_chat_completion.side_effect = RuntimeError("secret-sentinel auth_token=private")
        response = await self.http.post("/v1/chat/completions", json=PAYLOAD)
        self.assertGreaterEqual(response.status, 500)
        self.assertNotIn("secret-sentinel", await response.text())

    def test_public_bind_is_rejected(self):
        with self.assertRaises(ValueError):
            AntigravityBridgeServer(host="0.0.0.0", auth_manager=MagicMock())


    async def test_admin_auth_and_invalid_json_never_mutate_pool(self):
        self.bridge.boundary.admin_token = 'a' * 40
        response = await self.http.post('/v1/accounts/codex', json={'name': 'test'})
        self.assertEqual(response.status, 401)
        with patch.object(self.bridge, '_get_pool_or_error') as lookup:
            for data in ('{', '[]', '{"name":"a","name":"b"}', '{"name":NaN}', '{"name":1e9999}'):
                response = await self.http.post('/v1/accounts/codex', data=data, headers={
                    'Content-Type': 'application/json', 'X-Hermes-Admin-Token': 'a' * 40})
                self.assertEqual(response.status, 400)
            lookup.assert_not_called()

    async def test_admin_unknown_provider_is_400_not_falsey_response_fallthrough(self):
        self.bridge.boundary.admin_token = 'a' * 40
        response = await self.http.get('/v1/accounts/not-a-provider', headers={'X-Hermes-Admin-Token': 'a' * 40})
        self.assertEqual(response.status, 400)

    async def test_local_api_key_is_required_but_never_forwarded_upstream(self):
        self.bridge.boundary.api_key = 'b' * 40
        response = await self.http.post('/v1/chat/completions', json=PAYLOAD)
        self.assertEqual(response.status, 401)
        response = await self.http.post('/v1/chat/completions', json=PAYLOAD, headers={'Authorization': 'Bearer ' + 'b' * 40})
        self.assertEqual(response.status, 200)
        self.assertEqual(self.bridge.client.create_chat_completion.await_args.kwargs['bearer_token'], '')

    async def test_body_limit_and_content_type(self):
        from bridge.http_security import MAX_BODY
        response = await self.http.post('/v1/chat/completions', data='x' * (MAX_BODY + 1), headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status, 413)
        response = await self.http.post('/v1/chat/completions', data=json.dumps(PAYLOAD), headers={'Content-Type': 'text/plain'})
        self.assertEqual(response.status, 415)
        self.bridge.client.create_chat_completion.assert_not_awaited()

    async def test_busy_bridge_preserves_health(self):
        from bridge.http_security import MAX_INFLIGHT
        self.bridge.boundary.active = MAX_INFLIGHT
        response = await self.http.post('/v1/chat/completions', json=PAYLOAD)
        self.assertEqual(response.status, 429)
        self.assertIn('Retry-After', response.headers)
        self.assertEqual((await self.http.get('/health')).status, 200)
        self.bridge.client.create_chat_completion.assert_not_awaited()

    async def test_midstream_failure_is_explicit_and_closes_generator(self):
        closed = []
        async def chunks(*args, **kwargs):
            try:
                yield 'data: {"choices":[]}\n\n'
                raise RuntimeError('private-secret-sentinel')
            finally:
                closed.append(True)
        self.bridge.client.stream_chat_completion = chunks
        response = await self.http.post('/v1/chat/completions', json=PAYLOAD | {'stream': True})
        body = await response.text()
        self.assertEqual(response.status, 200)
        self.assertIn('"error"', body)
        self.assertNotIn('private-secret-sentinel', body)
        self.assertNotIn('[DONE]', body)
        self.assertEqual(closed, [True])
        self.assertEqual(self.bridge.boundary.active, 0)

    async def test_invalid_tool_choice_fails_before_provider(self):
        for choice in ({'type': 'function', 'function': 'wrong'}, 3, 'other'):
            with self.subTest(choice=choice):
                response = await self.http.post('/v1/chat/completions', json=PAYLOAD | {'tool_choice': choice})
                self.assertEqual(response.status, 400)
        self.bridge.client.create_chat_completion.assert_not_awaited()


class ProcessLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_cancellation_reaps_direct_child(self):
        from bridge.claude_code import _run_cli as claude
        from bridge.codex import _run_cli as codex
        for runner in (claude, codex):
            process = MagicMock()
            process.wait = AsyncMock()
            started = asyncio.Event()
            async def communicate(_):
                started.set()
                await asyncio.Event().wait()
            process.communicate = communicate
            with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=process)):
                task = asyncio.create_task(runner(['synthetic-never-executed'], 'test'))
                await started.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                process.kill.assert_called_once()
                process.wait.assert_awaited_once()

    async def test_claude_does_not_inherit_paid_api_or_other_account_token(self):
        import os
        from bridge.claude_code import _run_cli
        process = MagicMock(returncode=0)
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(b'{}', b''))
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'synthetic-key', 'CLAUDE_CODE_OAUTH_TOKEN': 'synthetic-other-account'}):
            with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=process)) as spawn:
                await _run_cli(['not-executed'], 'test', {'CLAUDE_CONFIG_DIR': '/synthetic-account'})
                env = spawn.await_args.kwargs['env']
                self.assertNotIn('ANTHROPIC_API_KEY', env)
                self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN', env)
                self.assertEqual(env['CLAUDE_CONFIG_DIR'], '/synthetic-account')
                self.assertEqual(os.environ['ANTHROPIC_API_KEY'], 'synthetic-key')


class LaunchTests(unittest.TestCase):
    def test_launch_source_and_installed_layout_no_path_interpolation(self):
        import bridge.server as server
        for path, module, root in [
            ("/tmp/quote's workspace/bridge/server.py", 'bridge.server', "/tmp/quote's workspace"),
            ('/tmp/profile/bridge/antigravity/tools/antigravity_bridge/server.py', 'tools.antigravity_bridge.server', '/tmp/profile/bridge/antigravity')]:
            with self.subTest(path=path), patch.object(server, '__file__', path):
                argv, cwd = server.bridge_launch_command('127.0.0.1', 8100)
                self.assertIn(f'from {module} import run_server', argv[3])
                self.assertNotIn(root, argv[3])
                self.assertEqual(str(cwd), root)
                self.assertEqual(argv[-2:], ['127.0.0.1', '8100'])

    def test_invalid_bind_fails_before_spawn(self):
        import bridge.server as server
        with patch('subprocess.Popen') as spawn:
            for host in ('0.0.0.0', '192.168.1.1', "localhost';bad"):
                with self.assertRaises(ValueError):
                    server.ensure_claude_code_bridge_running(host=host)
            for port in (0, -1, True, '8100', 65536):
                with self.assertRaises(ValueError):
                    server.bridge_launch_command(port=port)
            spawn.assert_not_called()


class AccountPersistenceTests(unittest.TestCase):
    def test_corrupt_registry_fails_closed_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            registry = home / 'accounts/codex/registry.json'
            registry.parent.mkdir(parents=True)
            registry.write_text('{corrupt')
            with self.assertRaises(ValueError):
                AccountPool('codex', hermes_dir=home)
            self.assertEqual(registry.read_text(), '{corrupt')

    def test_failed_atomic_replace_preserves_committed_state(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(AccountPool, '_seed_existing_credentials'):
            pool = AccountPool('codex', hermes_dir=Path(directory))
            pool.add_account('first')
            original = pool._registry_path.read_bytes()
            with patch('bridge.account_pool.os.replace', side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):
                    pool.add_account('second')
            self.assertEqual(pool.count(), 1)
            self.assertEqual(pool._registry_path.read_bytes(), original)
            self.assertEqual(list(pool._registry_path.parent.glob('.registry-*.tmp')), [])

    def test_pool_singleton_is_profile_scoped(self):
        import bridge.account_pool as accounts
        with tempfile.TemporaryDirectory() as directory, patch.dict(accounts._pools, {}, clear=True):
            first, second = Path(directory) / 'one', Path(directory) / 'two'
            with patch('bridge.auth.get_hermes_dir', return_value=first):
                a = accounts.get_pool('codex')
            with patch('bridge.auth.get_hermes_dir', return_value=second):
                b = accounts.get_pool('codex')
            self.assertIsNot(a, b)
            self.assertNotEqual(a._registry_path, b._registry_path)
            with patch('bridge.auth.get_hermes_dir', return_value=first):
                self.assertIs(accounts.get_pool('codex'), a)
