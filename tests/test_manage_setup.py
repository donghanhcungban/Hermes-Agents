"""Behavior tests for the `manage.py setup` command."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_manage_module():
    if "tools.antigravity_bridge" not in sys.modules:
        tools_pkg = types.ModuleType("tools")
        tools_pkg.__path__ = []
        bridge_pkg = types.ModuleType("tools.antigravity_bridge")
        bridge_pkg.__path__ = [str(ROOT / "bridge")]
        sys.modules.setdefault("tools", tools_pkg)
        sys.modules["tools.antigravity_bridge"] = bridge_pkg

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    spec = importlib.util.spec_from_file_location("antigravity_manage_setup", ROOT / "manage.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manage = load_manage_module()


class SetupCommandTests(unittest.TestCase):
    def test_setup_sets_antigravity_as_primary_even_with_existing_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp) / "hermes"
            hermes_dir.mkdir()
            import yaml

            config_file = hermes_dir / "config.yaml"
            config_file.write_text(
                yaml.dump({"model": {"provider": "openai-codex", "default": "other"}}),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                model="gemini-3.7-flash",
                port=8100,
                no_fallback=False,
                as_fallback_only=False,
            )

            with (
                mock.patch.object(manage, "get_hermes_dir", return_value=hermes_dir),
                mock.patch.object(manage, "cmd_install", return_value=0),
                mock.patch.object(manage, "_pool_account_count", return_value=3),
            ):
                result = manage.cmd_setup(args)

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(data["model"]["default"], "gemini-3.7-flash")
            self.assertEqual(
                [entry["provider"] for entry in data["fallback_providers"]],
                ["openai-codex", "anthropic"],
            )

    def test_setup_with_free_tier_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp) / "hermes"
            hermes_dir.mkdir()
            import yaml

            config_file = hermes_dir / "config.yaml"
            args = SimpleNamespace(
                model="gemini-3.7-flash",
                port=8100,
                no_fallback=False,
                as_fallback_only=False,
                free_tier=True,
                groq_model=None,
                ollama_model=None,
            )

            with (
                mock.patch.object(manage, "get_hermes_dir", return_value=hermes_dir),
                mock.patch.object(manage, "cmd_install", return_value=0),
                mock.patch.object(manage, "_pool_account_count", return_value=2),
            ):
                result = manage.cmd_setup(args)

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(len(data["fallback_providers"]), 4)
            providers = [e["provider"] for e in data["fallback_providers"]]
            self.assertNotIn("openai-codex", providers)
            self.assertNotIn("anthropic", providers)

    def test_cmd_setup_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp) / "hermes"
            hermes_dir.mkdir()
            import yaml

            config_file = hermes_dir / "config.yaml"
            args = SimpleNamespace(
                model="gemini-3.7-flash",
                port=8100,
                as_fallback_only=False,
            )

            with (
                mock.patch.object(manage, "get_hermes_dir", return_value=hermes_dir),
                mock.patch.object(manage, "cmd_install", return_value=0),
                mock.patch.object(manage, "_pool_account_count", return_value=1),
            ):
                result = manage.cmd_setup_free(args)

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(
                [e["provider"] for e in data["fallback_providers"]],
                ["antigravity", "antigravity", "custom", "custom"],
            )


if __name__ == "__main__":
    unittest.main()
