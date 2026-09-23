"""Tests for the priority fallback chain auto-configuration in manage.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_manage_module():
    # manage.py does `from bridge.auth import ...` which in turn (bridge/__init__.py)
    # does `from tools.antigravity_bridge.auth import ...` — the installed-layout
    # identity. Register the source tree under that identity first so both
    # import paths inside manage.py / bridge/__init__.py resolve without needing
    # an actual install.
    if "tools.antigravity_bridge" not in sys.modules:
        tools_pkg = types.ModuleType("tools")
        tools_pkg.__path__ = []
        bridge_pkg = types.ModuleType("tools.antigravity_bridge")
        bridge_pkg.__path__ = [str(ROOT / "bridge")]
        sys.modules.setdefault("tools", tools_pkg)
        sys.modules["tools.antigravity_bridge"] = bridge_pkg

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    spec = importlib.util.spec_from_file_location("antigravity_manage", ROOT / "manage.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manage = load_manage_module()


class BuildPriorityFallbackChainTests(unittest.TestCase):
    def test_orders_antigravity_first_then_openai_then_anthropic(self) -> None:
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            openai_model="gpt-5-codex",
            anthropic_model="claude-sonnet-4-6",
        )

        self.assertEqual(result["model"]["provider"], "antigravity")
        self.assertEqual(result["model"]["default"], "gemini-3.7-flash")
        self.assertEqual(
            result["fallback_providers"],
            [
                {"provider": "openai-codex", "model": "gpt-5-codex"},
                {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            ],
        )

    def test_does_not_duplicate_existing_fallback_entries(self) -> None:
        config = {
            "fallback_providers": [
                {"provider": "openai-codex", "model": "gpt-5-codex"},
                {"provider": "openrouter", "model": "anthropic/claude-sonnet-4"},
            ]
        }
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            openai_model="gpt-5-codex",
            anthropic_model="claude-sonnet-4-6",
        )

        providers = [entry["provider"] for entry in result["fallback_providers"]]
        self.assertEqual(providers.count("openai-codex"), 1)
        # A pre-existing unrelated fallback entry (openrouter) is preserved,
        # not clobbered by the priority chain.
        self.assertIn("openrouter", providers)
        self.assertIn("anthropic", providers)

    def test_does_not_overwrite_primary_when_user_opts_out(self) -> None:
        config = {"model": {"provider": "custom", "default": "my-model"}}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            openai_model="gpt-5-codex",
            anthropic_model="claude-sonnet-4-6",
            set_primary=False,
        )

        self.assertEqual(result["model"]["provider"], "custom")
        self.assertEqual(
            [e["provider"] for e in result["fallback_providers"]],
            ["antigravity", "openai-codex", "anthropic"],
        )

    def test_dedupes_by_provider_when_provider_already_present(self) -> None:
        # Reviewer finding: the dedup key must be provider-only, not
        # (provider, model) — otherwise a version bump to the default
        # fallback model would append a SECOND entry for the same provider
        # instead of leaving the existing one alone, growing the chain with
        # stale duplicate-provider entries over time.
        config = {
            "fallback_providers": [
                {"provider": "openai-codex", "model": "gpt-5-codex-OLD"},
            ]
        }
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            openai_model="gpt-5-codex-NEW",
            anthropic_model="claude-sonnet-4-6",
        )

        openai_entries = [
            e for e in result["fallback_providers"] if e["provider"] == "openai-codex"
        ]
        self.assertEqual(len(openai_entries), 1)

    def test_preserves_manually_customized_model_for_existing_provider(self) -> None:
        # A user who manually picked a different model for an already-present
        # fallback provider (via `hermes fallback add`) must not have that
        # choice silently overwritten by re-running install/setup.
        config = {
            "fallback_providers": [
                {"provider": "openai-codex", "model": "user-picked-model"},
            ]
        }
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            openai_model="gpt-5-codex",
            anthropic_model="claude-sonnet-4-6",
        )

        openai_entries = [
            e for e in result["fallback_providers"] if e["provider"] == "openai-codex"
        ]
        self.assertEqual(len(openai_entries), 1)
        self.assertEqual(openai_entries[0]["model"], "user-picked-model")


class InstallPreservesExistingPrimaryTests(unittest.TestCase):
    def test_configure_priority_fallback_default_does_not_clobber_existing_primary(
        self,
    ) -> None:
        # Reviewer finding: re-running install.py on an upgrade must not
        # silently reset a user's already-configured primary provider back to
        # antigravity. install.py now only sets the primary the FIRST time
        # (no existing `model.provider` in config.yaml); on any subsequent
        # run it behaves like --as-fallback-only automatically.
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp)
            import yaml

            config_file = hermes_dir / "config.yaml"
            config_file.write_text(
                yaml.dump({"model": {"provider": "openrouter", "default": "some-model"}}),
                encoding="utf-8",
            )

            manage.configure_priority_fallback_preserving_existing_primary(hermes_dir)

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(data["model"]["provider"], "openrouter")
            self.assertEqual(data["model"]["default"], "some-model")
            self.assertEqual(
                [e["provider"] for e in data["fallback_providers"]],
                ["antigravity", "openai-codex", "anthropic"],
            )

    def test_sets_antigravity_as_primary_on_a_fresh_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp)
            manage.configure_priority_fallback_preserving_existing_primary(hermes_dir)

            import yaml

            data = yaml.safe_load((hermes_dir / "config.yaml").read_text(encoding="utf-8"))
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(
                [e["provider"] for e in data["fallback_providers"]],
                ["openai-codex", "anthropic"],
            )


    def test_reinstall_with_antigravity_primary_does_not_add_it_as_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp)
            import yaml

            config_file = hermes_dir / "config.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "model": {"provider": "antigravity", "default": "gemini-3.7-flash"},
                        "fallback_providers": [
                            {"provider": "antigravity", "model": "gemini-3.7-flash"}
                        ],
                    }
                ),
                encoding="utf-8",
            )

            manage.configure_priority_fallback_preserving_existing_primary(hermes_dir)

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(
                [e["provider"] for e in data["fallback_providers"]],
                ["openai-codex", "anthropic"],
            )


class ConfigurePriorityFallbackIntegrationTests(unittest.TestCase):
    def test_writes_yaml_config_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hermes_dir = Path(tmp)
            manage.configure_priority_fallback(hermes_dir)

            config_file = hermes_dir / "config.yaml"
            self.assertTrue(config_file.is_file())

            import yaml

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            self.assertEqual(data["model"]["provider"], "antigravity")
            self.assertEqual(
                [e["provider"] for e in data["fallback_providers"]],
                ["openai-codex", "anthropic"],
            )


class OllamaLastResortFallbackTests(unittest.TestCase):
    def test_omitted_by_default(self) -> None:
        # Recommended default: no --ollama-model given means no local hop at
        # all — a 7B local model must be an explicit opt-in, never silently
        # inserted into the chain.
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
        )
        providers = [e["provider"] for e in result["fallback_providers"]]
        self.assertNotIn("custom", providers)

    def test_appended_last_via_hermes_custom_provider_alias(self) -> None:
        # Hermes has no built-in "ollama" provider: hermes_cli/auth.py aliases
        # "ollama" -> "custom" (a generic OpenAI-compatible endpoint) and
        # hermes_cli/runtime_provider.py auto-fills api_key="no-key-required"
        # for a keyless "custom" entry, so this entry needs an explicit
        # base_url and no API key — matching Ollama's unauthenticated local
        # server. It must land AFTER antigravity/openai-codex/anthropic:
        # small local models are a last-resort, not an early hop.
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            ollama_model="qwen2.5:7b-instruct",
        )
        self.assertEqual(
            result["fallback_providers"],
            [
                {"provider": "openai-codex", "model": "gpt-5-codex"},
                {"provider": "anthropic", "model": "claude-sonnet-4-6"},
                {
                    "provider": "custom",
                    "model": "qwen2.5:7b-instruct",
                    "base_url": manage.DEFAULT_OLLAMA_BASE_URL,
                },
            ],
        )

    def test_does_not_duplicate_or_clobber_an_unrelated_custom_entry(self) -> None:
        # "custom" is shared by every generic local server (LM Studio, vLLM,
        # llama.cpp too) — dedupe must key on (provider, base_url), not
        # provider alone, or the user's own unrelated custom fallback (e.g.
        # LM Studio on a different port) would be blocked or overwritten.
        config = {
            "fallback_providers": [
                {
                    "provider": "custom",
                    "model": "my-lmstudio-model",
                    "base_url": "http://127.0.0.1:1234/v1",
                }
            ]
        }
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            ollama_model="qwen2.5:7b-instruct",
        )
        custom_entries = [
            e for e in result["fallback_providers"] if e["provider"] == "custom"
        ]
        self.assertEqual(len(custom_entries), 2)
        self.assertIn(
            {
                "provider": "custom",
                "model": "my-lmstudio-model",
                "base_url": "http://127.0.0.1:1234/v1",
            },
            custom_entries,
        )
        self.assertIn(
            {
                "provider": "custom",
                "model": "qwen2.5:7b-instruct",
                "base_url": manage.DEFAULT_OLLAMA_BASE_URL,
            },
            custom_entries,
        )

    def test_rerun_with_same_ollama_model_does_not_duplicate(self) -> None:
        config = {}
        manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            ollama_model="qwen2.5:7b-instruct",
        )
        # Second run against the already-written config (e.g. re-running
        # `manage.py setup --ollama-model ...`).
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            ollama_model="qwen2.5:7b-instruct",
        )
        custom_entries = [
            e for e in result["fallback_providers"] if e["provider"] == "custom"
        ]
        self.assertEqual(len(custom_entries), 1)


class GroqCloudFallbackTests(unittest.TestCase):
    def test_omitted_by_default(self) -> None:
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
        )
        providers = [e["provider"] for e in result["fallback_providers"]]
        self.assertNotIn("custom", providers)

    def test_inserted_between_anthropic_and_ollama_with_no_api_key_field(self) -> None:
        # Groq needs internet (unlike Ollama), so it belongs between the
        # cloud providers and the true offline last resort. Like Ollama,
        # Hermes has no built-in "groq" provider — it derives GROQ_API_KEY
        # from the api.groq.com host for a keyless "custom" entry (per
        # hermes_cli/runtime_provider.py's _host_derived_api_key), so the
        # written config must never itself carry an api_key/secret.
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            groq_model="llama-3.3-70b-versatile",
            ollama_model="qwen2.5:7b-instruct",
        )
        self.assertEqual(
            result["fallback_providers"],
            [
                {"provider": "openai-codex", "model": "gpt-5-codex"},
                {"provider": "anthropic", "model": "claude-sonnet-4-6"},
                {
                    "provider": "custom",
                    "model": "llama-3.3-70b-versatile",
                    "base_url": manage.DEFAULT_GROQ_BASE_URL,
                },
                {
                    "provider": "custom",
                    "model": "qwen2.5:7b-instruct",
                    "base_url": manage.DEFAULT_OLLAMA_BASE_URL,
                },
            ],
        )
        for entry in result["fallback_providers"]:
            self.assertNotIn("api_key", entry)

    def test_rerun_with_same_groq_model_does_not_duplicate(self) -> None:
        config = {}
        manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            groq_model="llama-3.3-70b-versatile",
        )
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            groq_model="llama-3.3-70b-versatile",
        )
        custom_entries = [
            e for e in result["fallback_providers"] if e["provider"] == "custom"
        ]
        self.assertEqual(len(custom_entries), 1)


class ZeroCostFreeTierFallbackTests(unittest.TestCase):
    def test_free_tier_builds_zero_cost_chain(self) -> None:
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            free_tier_only=True,
        )

        self.assertEqual(result["model"]["provider"], "antigravity")
        self.assertEqual(result["model"]["default"], "gemini-3.7-flash")

        fallback_chain = result["fallback_providers"]
        providers = [e["provider"] for e in fallback_chain]
        self.assertNotIn("openai-codex", providers)
        self.assertNotIn("anthropic", providers)
        self.assertNotIn("claude-code-cli", providers)

        self.assertEqual(
            fallback_chain,
            [
                {"provider": "antigravity", "model": "gemini-3.7-flash-medium"},
                {"provider": "antigravity", "model": "gemini-3.5-flash"},
                {
                    "provider": "custom",
                    "model": "llama-3.3-70b-versatile",
                    "base_url": manage.DEFAULT_GROQ_BASE_URL,
                },
                {
                    "provider": "custom",
                    "model": "qwen2.5-coder:7b",
                    "base_url": manage.DEFAULT_OLLAMA_BASE_URL,
                },
            ],
        )

    def test_free_tier_strips_existing_paid_providers(self) -> None:
        config = {
            "fallback_providers": [
                {"provider": "openai-codex", "model": "gpt-5-codex"},
                {"provider": "anthropic", "model": "claude-sonnet-4-6"},
                {"provider": "claude-code-cli", "model": "sonnet"},
            ]
        }
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            free_tier_only=True,
        )

        providers = [e["provider"] for e in result["fallback_providers"]]
        self.assertNotIn("openai-codex", providers)
        self.assertNotIn("anthropic", providers)
        self.assertNotIn("claude-code-cli", providers)

    def test_free_tier_rerun_does_not_duplicate(self) -> None:
        config = {}
        manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            free_tier_only=True,
        )
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_base_url="http://127.0.0.1:8100/v1",
            free_tier_only=True,
        )

        chain = result["fallback_providers"]
        self.assertEqual(len(chain), 4)

    def test_free_tier_custom_primary_model_filters_self(self) -> None:
        config = {}
        result = manage.apply_priority_fallback_config(
            config,
            antigravity_model="gemini-3.7-flash-medium",
            antigravity_base_url="http://127.0.0.1:8100/v1",
            free_tier_only=True,
        )

        models = [e.get("model") for e in result["fallback_providers"]]
        self.assertNotIn("gemini-3.7-flash-medium", models)
        self.assertIn("gemini-3.5-flash", models)


if __name__ == "__main__":
    unittest.main()
