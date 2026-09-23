"""Kiểm thử catalog model Antigravity được phát hiện động."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.client import AntigravityClient, map_model_name, parse_available_models


class ModelDiscoveryTests(unittest.TestCase):
    def test_keeps_selectable_new_models_and_skips_internal_models(self) -> None:
        payload = {
            "models": {
                "gemini-3.8-flash-tiered": {
                    "model": "MODEL_PLACEHOLDER_M322",
                    "apiProvider": "API_PROVIDER_GOOGLE_GEMINI",
                    "modelProvider": "MODEL_PROVIDER_GOOGLE",
                },
                "claude-opus-5-thinking": {
                    "displayName": "Claude Opus 5 (Thinking)",
                    "model": "MODEL_PLACEHOLDER_M500",
                    "apiProvider": "API_PROVIDER_ANTHROPIC_VERTEX",
                    "modelProvider": "MODEL_PROVIDER_ANTHROPIC",
                },
                "chat_internal": {"isInternal": True, "displayName": "Internal"},
                "not-selectable": {"displayName": "Hidden experiment"},
            },
            "agentModelSorts": [
                {"groups": [{"modelIds": ["claude-opus-5-thinking", "chat_internal"]}]}
            ],
            "tieredModelIds": {"flash": ["gemini-3.8-flash-tiered"]},
        }

        models = parse_available_models(payload)

        self.assertEqual(
            ["claude-opus-5-thinking", "gemini-3.8-flash-tiered"],
            [model["id"] for model in models],
        )
        self.assertEqual("Claude Opus 5 (Thinking)", models[0]["name"])
        self.assertEqual("gemini-3.8-flash-tiered", models[1]["code_assist_model"])

    def test_catalog_refresh_is_cached_for_the_ttl(self) -> None:
        payload = {
            "models": {"gemini-3.8-flash-tiered": {}},
            "tieredModelIds": {"flash": ["gemini-3.8-flash-tiered"]},
        }

        class FakeResponse:
            status_code = 200

            def json(self) -> dict:
                return payload

        class FakeHttp:
            calls = 0

            async def post(self, *args, **kwargs) -> FakeResponse:
                self.calls += 1
                return FakeResponse()

        class FakeAuth:
            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return [SimpleNamespace(access_token="token", project_id="project")]

        async def scenario() -> tuple[list[str], int]:
            client = AntigravityClient(FakeAuth())
            await client._http.aclose()
            fake_http = FakeHttp()
            client._http = fake_http
            first = await client.list_models()
            second = await client.list_models()
            self.assertEqual(first, second)
            return [model["id"] for model in second], fake_http.calls

        model_ids, calls = asyncio.run(scenario())
        self.assertIn("gemini-3.8-flash-tiered", model_ids)
        self.assertEqual(1, calls)

    def test_catalog_unions_models_discovered_by_each_account(self) -> None:
        payloads = {
            "project-a": {
                "models": {"gemini-3.8-flash-tiered": {}},
                "tieredModelIds": {"flash": ["gemini-3.8-flash-tiered"]},
            },
            "project-b": {
                "models": {"claude-opus-5-thinking": {}},
                "agentModelSorts": [{"groups": [{"modelIds": ["claude-opus-5-thinking"]}]}],
            },
        }

        class Response:
            status_code = 200

            def __init__(self, payload: dict) -> None:
                self.payload = payload

            def json(self) -> dict:
                return self.payload

        class FakeHttp:
            async def post(self, _url: str, *, json: dict, headers: dict) -> Response:
                return Response(payloads[json["project"]])

        class FakeAuth:
            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return [
                    SimpleNamespace(access_token="token-a", project_id="project-a"),
                    SimpleNamespace(access_token="token-b", project_id="project-b"),
                ]

        async def scenario() -> set[str]:
            client = AntigravityClient(FakeAuth())
            await client._http.aclose()
            client._http = FakeHttp()
            return {model["id"] for model in await client.list_models()}

        model_ids = asyncio.run(scenario())
        self.assertIn("gemini-3.8-flash-tiered", model_ids)
        self.assertIn("claude-opus-5-thinking", model_ids)

    def test_account_specific_model_entitlement_rotates_to_supporting_account(self) -> None:
        discovered_payload = {
            "models": {"claude-opus-5-thinking": {}},
            "agentModelSorts": [{"groups": [{"modelIds": ["claude-opus-5-thinking"]}]}],
        }

        class Response:
            def __init__(self, status_code: int, payload: dict | None = None) -> None:
                self.status_code = status_code
                self.payload = payload or {}
                self.headers: dict[str, str] = {}
                self.text = "model not supported" if status_code == 404 else ""

            def json(self) -> dict:
                return self.payload

        class FakeAuth:
            def __init__(self) -> None:
                self.marked: list[str] = []
                self.accounts = [
                    SimpleNamespace(access_token="token-a", project_id="project-a", email="a@example.com"),
                    SimpleNamespace(access_token="token-b", project_id="project-b", email="b@example.com"),
                ]

            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return self.accounts

            def mark_account_unavailable(self, creds: SimpleNamespace, *_args: object) -> None:
                self.marked.append(creds.project_id)

        class FakeHttp:
            async def post(self, url: str, *, json: dict, headers: dict) -> Response:
                project = json["project"]
                if url.endswith(":fetchAvailableModels"):
                    return Response(200, discovered_payload)
                if project == "project-a":
                    return Response(404)
                return Response(
                    200,
                    {"response": {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}},
                )

        async def scenario() -> tuple[str, list[str]]:
            auth = FakeAuth()
            client = AntigravityClient(auth)  # type: ignore[arg-type]
            await client._http.aclose()
            client._http = FakeHttp()  # type: ignore[assignment]
            result = await client.create_chat_completion(
                {
                    "model": "claude-opus-5-thinking",
                    "messages": [{"role": "user", "content": "ping"}],
                }
            )
            return result["choices"][0]["message"]["content"], auth.marked

        content, marked = asyncio.run(scenario())
        self.assertEqual("OK", content)
        self.assertEqual(["project-a"], marked)

    def test_invalid_discovery_payload_keeps_the_safe_catalog(self) -> None:
        class InvalidResponse:
            status_code = 200

            def json(self) -> dict:
                raise ValueError("invalid JSON")

        class FakeHttp:
            async def post(self, *args, **kwargs) -> InvalidResponse:
                return InvalidResponse()

        class FakeAuth:
            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return [SimpleNamespace(access_token="token", project_id="project")]

        async def scenario() -> list[str]:
            client = AntigravityClient(FakeAuth())
            await client._http.aclose()
            client._http = FakeHttp()
            return [model["id"] for model in await client.list_models()]

        self.assertIn("gemini-3.7-flash", asyncio.run(scenario()))

    def test_unknown_model_forces_discovery_while_catalog_is_warm(self) -> None:
        class FakeHttp:
            def __init__(self) -> None:
                self.calls = 0

            async def post(self, *_args: object, **_kwargs: object) -> object:
                self.calls += 1
                return type("Response", (), {"status_code": 200, "json": lambda self: {"models": {"gemini-3.9-flash": {}}, "tieredModelIds": {"flash": ["gemini-3.9-flash"]}}})()

        class FakeAuth:
            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return [SimpleNamespace(access_token="token", project_id="project")]

        async def scenario() -> int:
            client = AntigravityClient(FakeAuth())
            await client._http.aclose()
            fake_http = FakeHttp()
            client._http = fake_http  # type: ignore[assignment]
            client._model_catalog_refreshed_at = __import__("time").monotonic() - 11
            await client._refresh_catalog_for_unknown_model("gemini-3.9-flash")
            return fake_http.calls

        self.assertEqual(1, asyncio.run(scenario()))

    def test_unknown_model_is_discovered_before_completion(self) -> None:
        discovered_payload = {
            "models": {"gemini-3.8-flash-tiered": {}},
            "tieredModelIds": {"flash": ["gemini-3.8-flash-tiered"]},
        }

        class FakeAuth:
            def resolve_credential_candidates(self, **_kwargs: str) -> list[SimpleNamespace]:
                return [SimpleNamespace(access_token="token", project_id="project")]

        class Response:
            def __init__(self, status_code: int, payload: dict) -> None:
                self.status_code = status_code
                self._payload = payload
                self.headers: dict[str, str] = {}
                self.text = ""

            def json(self) -> dict:
                return self._payload

        class Http:
            def __init__(self) -> None:
                self.calls: list[tuple[str, dict]] = []

            async def post(self, url: str, *, json: dict, headers: dict) -> Response:
                self.calls.append((url, json))
                if url.endswith(":fetchAvailableModels"):
                    return Response(200, discovered_payload)
                return Response(
                    200,
                    {
                        "response": {
                            "candidates": [
                                {
                                    "content": {"parts": [{"text": "OK"}]},
                                    "finishReason": "STOP",
                                }
                            ]
                        }
                    },
                )

        async def run() -> None:
            client = AntigravityClient(FakeAuth())  # type: ignore[arg-type]
            await client._http.aclose()
            fake_http = Http()
            client._http = fake_http  # type: ignore[assignment]
            result = await client.create_chat_completion(
                {
                    "model": "gemini-3.8-flash-tiered",
                    "messages": [{"role": "user", "content": "ping"}],
                }
            )
            self.assertTrue(fake_http.calls[0][0].endswith(":fetchAvailableModels"))
            self.assertEqual(fake_http.calls[1][1]["model"], "gemini-3.8-flash-tiered")
            self.assertEqual(result["choices"][0]["message"]["content"], "OK")

        asyncio.run(run())

    def test_map_model_name_accepts_a_model_discovered_at_runtime(self) -> None:
        self.assertEqual(
            "claude-opus-5-thinking",
            map_model_name(
                "claude-opus-5-thinking",
                available_models={"claude-opus-5-thinking"},
            ),
        )


if __name__ == "__main__":
    unittest.main()
