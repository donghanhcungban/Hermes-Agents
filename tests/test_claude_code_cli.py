"""Tests for the Claude Code subscription CLI bridge."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.claude_code import (
    CLI_MODEL_ALIASES,
    ClaudeCodeCliClient,
    ClaudeCodeCliError,
    discover_models_from_help,
)


class ClaudeCodeCliClientTests(unittest.TestCase):
    def test_discovers_new_aliases_and_full_model_ids_from_cli_help(self) -> None:
        help_text = """
          --model <model>  Provide an alias (e.g. 'fable', 'opus', or 'sonnet')
                           or a full name (e.g. 'claude-fable-5' or 'claude-opus-5').
          --verbose        Show verbose output
        """

        self.assertEqual(
            {"claude-fable-5", "claude-opus-5", "fable", "haiku", "opus", "sonnet"},
            set(discover_models_from_help(help_text)),
        )

    def test_supports_the_four_configured_claude_code_model_aliases(self) -> None:
        self.assertEqual(
            {"fable", "opus", "sonnet", "haiku"},
            {CLI_MODEL_ALIASES[name] for name in ("fable", "opus", "sonnet", "haiku")},
        )

    def test_returns_openai_content_from_structured_cli_result(self) -> None:
        observed: list[list[str]] = []

        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            observed.append(command)
            self.assertIn("Xin chào", prompt)
            return 0, json.dumps(
                {"structured_output": {"content": "Chào bạn!", "tool_calls": []}}
            ), ""

        client = ClaudeCodeCliClient(runner=runner)
        response = asyncio.run(
            client.create_chat_completion(
                {"model": "sonnet", "messages": [{"role": "user", "content": "Xin chào"}]}
            )
        )

        self.assertEqual(response["choices"][0]["message"]["content"], "Chào bạn!")
        self.assertEqual(response["choices"][0]["finish_reason"], "stop")
        self.assertIn("--tools", observed[0])
        self.assertNotIn("--bare", observed[0])
        self.assertIn("", observed[0])
        self.assertIn("--no-session-persistence", observed[0])

    def test_returns_openai_tool_call_without_executing_claude_tools(self) -> None:
        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            self.assertIn("get_weather", prompt)
            return 0, json.dumps(
                {
                    "structured_output": {
                        "content": "",
                        "tool_calls": [{"name": "get_weather", "arguments": {"city": "Hà Nội"}}],
                    }
                }
            ), ""

        client = ClaudeCodeCliClient(runner=runner)
        response = asyncio.run(
            client.create_chat_completion(
                {
                    "model": "sonnet",
                    "messages": [{"role": "user", "content": "Thời tiết ở Hà Nội?"}],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "description": "Lấy thời tiết theo thành phố",
                                "parameters": {"type": "object"},
                            },
                        }
                    ],
                }
            )
        )

        message = response["choices"][0]["message"]
        self.assertEqual(response["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(message["tool_calls"][0]["function"]["name"], "get_weather")
        self.assertEqual(json.loads(message["tool_calls"][0]["function"]["arguments"]), {"city": "Hà Nội"})

    def test_rejects_tool_not_offered_by_hermes(self) -> None:
        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            return 0, json.dumps(
                {"structured_output": {"content": "", "tool_calls": [{"name": "shell", "arguments": {}}]}}
            ), ""

        client = ClaudeCodeCliClient(runner=runner)
        with self.assertRaisesRegex(ClaudeCodeCliError, "not offered"):
            asyncio.run(
                client.create_chat_completion(
                    {
                        "messages": [{"role": "user", "content": "Hi"}],
                        "tools": [{"type": "function", "function": {"name": "safe_tool"}}],
                    }
                )
            )

    def test_reports_missing_claude_cli(self) -> None:
        async def runner(command: list[str], prompt: str, extra_env: dict | None = None) -> tuple[int, str, str]:
            raise FileNotFoundError(command[0])

        client = ClaudeCodeCliClient(runner=runner)
        with self.assertRaisesRegex(ClaudeCodeCliError, "not found"):
            asyncio.run(
                client.create_chat_completion(
                    {"messages": [{"role": "user", "content": "Hi"}]}
                )
            )


if __name__ == "__main__":
    unittest.main()

