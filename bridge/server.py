"""HTTP server and daemon runner for Antigravity Local Bridge.

Implements standard OpenAI API endpoints:
- GET  /v1/models                            (unified: Antigravity + Claude Code + Codex)
- POST /v1/chat/completions                  (smart routing by model prefix/name)
- GET  /health
- GET  /auth/status
- POST /auth/login

Provider-specific endpoints:
- GET  /v1/antigravity/models
- POST /v1/antigravity/chat/completions
- GET  /v1/claude-code/models
- POST /v1/claude-code/chat/completions
- GET  /v1/codex/models
- POST /v1/codex/chat/completions
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from aiohttp import web

from .http_security import BridgeBoundary, MAX_BODY, public_error, read_payload, require_loopback

try:
    from bridge.auth import (
        AntigravityAuthManager,
        get_hermes_dir,
    )
    from bridge.client import AntigravityClient
    from bridge.claude_code import ClaudeCodeCliClient, ClaudeCodeCliError
except ImportError:
    from tools.antigravity_bridge.auth import (
        AntigravityAuthManager,
        get_hermes_dir,
    )
    from tools.antigravity_bridge.client import AntigravityClient
    from tools.antigravity_bridge.claude_code import ClaudeCodeCliClient, ClaudeCodeCliError

try:
    from bridge.codex import CodexCliClient, CodexCliError, CODEX_MODEL_IDS, CODEX_MODEL_ALIASES
except ImportError:
    try:
        from tools.antigravity_bridge.codex import (  # type: ignore[import]
            CodexCliClient, CodexCliError, CODEX_MODEL_IDS, CODEX_MODEL_ALIASES,
        )
    except ImportError:
        CodexCliClient = None  # type: ignore[assignment,misc]
        CodexCliError = RuntimeError  # type: ignore[assignment,misc]
        CODEX_MODEL_IDS: set = set()
        CODEX_MODEL_ALIASES: dict = {}

logger = logging.getLogger(__name__)


def _upstream_status(exc: Exception) -> int:
    """Lấy mã HTTP thật từ UpstreamError; các lỗi khác đoán an toàn từ nội dung."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and 400 <= status < 600:
        return status
    text = str(exc)
    if "429" in text or "exhausted" in text.lower():
        return 429
    return 500


DEFAULT_BRIDGE_PORT = 8100
DEFAULT_BRIDGE_HOST = "127.0.0.1"


def get_bridge_dir() -> Path:
    bridge_dir = get_hermes_dir() / "bridge" / "antigravity"
    bridge_dir.mkdir(parents=True, exist_ok=True)
    return bridge_dir


def get_pid_file() -> Path:
    return get_bridge_dir() / "bridge.pid"


def get_log_file() -> Path:
    log_dir = get_hermes_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "antigravity_bridge.log"


class AntigravityBridgeServer:
    """Async HTTP Server exposing three AI CLI providers as OpenAI-compatible API.

    Providers:
      - Antigravity: Google Gemini/Claude via OAuth (primary, smart routing default)
      - Claude Code CLI: Claude Pro/Team subscription via `claude -p`
      - Codex CLI: ChatGPT/OpenAI subscription via `codex exec`
    """

    def __init__(
        self,
        host: str = DEFAULT_BRIDGE_HOST,
        port: int = DEFAULT_BRIDGE_PORT,
        auth_manager: Optional[AntigravityAuthManager] = None,
    ) -> None:
        self.boundary = BridgeBoundary(host)
        self.host = host
        self.port = port
        self.auth_manager = auth_manager or AntigravityAuthManager()
        self.client = AntigravityClient(self.auth_manager)
        self.claude_code_client = ClaudeCodeCliClient()
        self.codex_client = CodexCliClient() if CodexCliClient is not None else None
        self.app = web.Application(middlewares=[self.boundary.middleware], client_max_size=MAX_BODY)
        self.app.on_cleanup.append(self._close_clients)
        self._setup_routes()

    async def _close_clients(self, app) -> None:
        await self.client.close()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/auth/status", self.handle_auth_status)
        self.app.router.add_post("/auth/login", self.handle_auth_login)
        # Unified endpoints (smart routing)
        self.app.router.add_get("/v1/models", self.handle_list_models)
        self.app.router.add_post("/v1/chat/completions", self.handle_chat_completions)
        # Antigravity-specific endpoints
        self.app.router.add_get("/v1/antigravity/models", self.handle_antigravity_models)
        self.app.router.add_post("/v1/antigravity/chat/completions", self.handle_antigravity_completions)
        # Claude Code CLI endpoints
        self.app.router.add_get("/v1/claude-code/models", self.handle_claude_code_models)
        self.app.router.add_post("/v1/claude-code/chat/completions", self.handle_claude_code_completions)
        # Codex CLI endpoints (two aliases: /v1/codex and /v1/codex-cli)
        self.app.router.add_get("/v1/codex/models", self.handle_codex_models)
        self.app.router.add_post("/v1/codex/chat/completions", self.handle_codex_completions)
        self.app.router.add_get("/v1/codex-cli/models", self.handle_codex_models)
        self.app.router.add_post("/v1/codex-cli/chat/completions", self.handle_codex_completions)
        # Account pool management (multi-account rotation)
        self.app.router.add_get("/v1/accounts/{provider}", self.handle_list_accounts)
        self.app.router.add_post("/v1/accounts/{provider}", self.handle_add_account)
        self.app.router.add_delete("/v1/accounts/{provider}/{account_id}", self.handle_remove_account)
        self.app.router.add_patch("/v1/accounts/{provider}/{account_id}", self.handle_update_account)
        self.app.router.add_post("/v1/accounts/{provider}/{account_id}/clear-limit", self.handle_clear_limit)

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "ok",
            "bridge": "hermes-multi-provider",
            "version": "2.0.0",
            "providers": {
                "antigravity": "Google Gemini/Claude via OAuth",
                "claude-code-cli": "Claude subscription via `claude -p`",
                "codex-cli": "ChatGPT/OpenAI subscription via `codex exec`",
            },
            "endpoints": {
                "unified": ["/v1/models", "/v1/chat/completions"],
                "antigravity": ["/v1/antigravity/models", "/v1/antigravity/chat/completions"],
                "claude-code": ["/v1/claude-code/models", "/v1/claude-code/chat/completions"],
                "codex": ["/v1/codex/models", "/v1/codex/chat/completions"],
            },
            "timestamp": time.time(),
            "inference_auth": "api_key" if self.boundary.api_key else "loopback_only",
            "http_admin_enabled": bool(self.boundary.admin_token),
        })

    async def handle_auth_status(self, request: web.Request) -> web.Response:
        creds = self.auth_manager.load_stored_credentials() or self.auth_manager.discover_local_tokens()
        if not creds:
            return web.json_response({
                "logged_in": False,
                "email": "",
                "project_id": "",
                "expires_at": None,
                "message": "No credentials stored. Please log in.",
            })

        return web.json_response({
            "logged_in": True,
            "email": creds.email,
            "project_id": creds.project_id,
            "expires_at": creds.expires_at,
            "is_expired": creds.is_expired,
            "has_refresh_token": bool(creds.refresh_token),
            "source": creds.source,
        })

    async def handle_auth_login(self, request: web.Request) -> web.Response:
        try:
            creds = await asyncio.to_thread(self.auth_manager.login_pkce)
            return web.json_response({
                "ok": True,
                "email": creds.email,
                "project_id": creds.project_id,
            })
        except Exception as e:
            return web.json_response({"ok": False, "error": public_error(e)}, status=500)

    async def handle_list_models(self, request: web.Request) -> web.Response:
        """Unified model catalog: merges Antigravity + Claude Code + Codex models.

        Query params:
          ?refresh=1          force catalog refresh from upstream
          ?provider=antigravity|claude-code|codex  filter by provider
        """
        force_refresh = request.query.get("refresh") in {"1", "true", "yes"}
        provider_filter = request.query.get("provider", "").lower().strip()

        models: list[dict] = []
        ts = int(time.time())

        # --- Antigravity (Gemini + Claude via Google OAuth) ---
        if not provider_filter or provider_filter in {"antigravity", "google", "gemini"}:
            try:
                catalog = await self.client.list_models(force_refresh=force_refresh)
                for m in catalog:
                    models.append({
                        "id": m["id"],
                        "object": "model",
                        "created": ts,
                        "owned_by": "antigravity",
                        "permission": [],
                        "name": m.get("name", m["id"]),
                        "description": m.get("description", ""),
                        "provider": "antigravity",
                    })
            except Exception as exc:
                logger.warning("Antigravity model discovery failed: %s", type(exc).__name__)

        # --- Claude Code CLI ---
        if not provider_filter or provider_filter in {"claude-code", "claude", "claude-code-cli"}:
            try:
                claude_models = await self.claude_code_client.list_models(force_refresh=force_refresh)
                for m in claude_models:
                    models.append({
                        "id": m,
                        "object": "model",
                        "created": ts,
                        "owned_by": "claude-code-cli",
                        "permission": [],
                        "name": f"{m} (Claude Code CLI)",
                        "description": "Claude subscription model via `claude -p` CLI.",
                        "provider": "claude-code-cli",
                    })
            except Exception as exc:
                logger.warning("Claude Code model discovery failed: %s", type(exc).__name__)

        # --- Codex CLI ---
        if not provider_filter or provider_filter in {"codex", "codex-cli", "openai", "openai-codex"}:
            if self.codex_client is not None:
                try:
                    codex_models = await self.codex_client.list_models(force_refresh=force_refresh)
                    for m in codex_models:
                        models.append({
                            "id": m["id"],
                            "object": "model",
                            "created": ts,
                            "owned_by": "codex-cli",
                            "permission": [],
                            "name": m.get("name", m["id"]),
                            "description": m.get("description", ""),
                            "provider": "codex-cli",
                        })
                except Exception as exc:
                    logger.warning("Codex model discovery failed: %s", type(exc).__name__)

        return web.json_response({"object": "list", "data": models})

    # ------------------------------------------------------------------
    # Antigravity-only models endpoint
    # ------------------------------------------------------------------

    async def handle_antigravity_models(self, request: web.Request) -> web.Response:
        force_refresh = request.query.get("refresh") in {"1", "true", "yes"}
        try:
            catalog = await self.client.list_models(force_refresh=force_refresh)
        except Exception as exc:
            logger.error("Antigravity model catalog error: %s", type(exc).__name__)
            return web.json_response({"object": "list", "data": []})
        ts = int(time.time())
        return web.json_response({
            "object": "list",
            "data": [
                {
                    "id": m["id"],
                    "object": "model",
                    "created": ts,
                    "owned_by": "antigravity",
                    "permission": [],
                    "name": m.get("name", m["id"]),
                    "description": m.get("description", ""),
                }
                for m in catalog
            ],
        })

    # ------------------------------------------------------------------
    # Smart routing: /v1/chat/completions
    # ------------------------------------------------------------------

    def _route_model(self, model_id: str) -> str:
        """Return provider name for a given model ID: 'codex', 'claude-code', or 'antigravity'."""
        m = model_id.lower().strip()
        if m.startswith(("codex/", "codex-cli/")):
            return "codex"
        if m.startswith(("claude-code/", "claude-code-cli/")):
            return "claude-code"
        # Codex model IDs (also check aliases)
        if CODEX_MODEL_IDS and (m in CODEX_MODEL_IDS or m in CODEX_MODEL_ALIASES):
            return "codex"
        # Claude Code CLI aliases
        try:
            from bridge.claude_code import CLI_MODEL_ALIASES as _CLAUDE_ALIASES
        except ImportError:
            try:
                from tools.antigravity_bridge.claude_code import CLI_MODEL_ALIASES as _CLAUDE_ALIASES
            except ImportError:
                _CLAUDE_ALIASES = {}
        if m in _CLAUDE_ALIASES or m in {"fable", "sonnet", "opus", "haiku"}:
            return "claude-code"
        return "antigravity"

    async def handle_chat_completions(self, request: web.Request) -> web.StreamResponse:
        try:
            payload = await read_payload(request)
        except Exception as e:
            return web.json_response(
                {"error": {"message": f"Invalid JSON payload: {e}", "type": "invalid_request_error"}},
                status=400,
            )

        model_id = str(payload.get("model") or "gemini-3.7-flash")
        provider = self._route_model(model_id)

        if provider == "codex":
            logger.debug("Smart routing to Codex CLI for model=%s", model_id)
            return await self.handle_codex_completions(request, _payload=payload)
        if provider == "claude-code":
            logger.debug("Smart routing to Claude Code CLI for model=%s", model_id)
            return await self.handle_claude_code_completions(request, _payload=payload)

        # Default: Antigravity
        logger.debug("Smart routing to Antigravity for model=%s", model_id)
        return await self.handle_antigravity_completions(request, _payload=payload)

    # ------------------------------------------------------------------
    # Antigravity completions (formerly handle_chat_completions)
    # ------------------------------------------------------------------

    async def handle_antigravity_completions(
        self, request: web.Request, *, _payload: dict | None = None
    ) -> web.StreamResponse:
        if _payload is None:
            try:
                _payload = await read_payload(request)
            except Exception as e:
                return web.json_response(
                    {"error": {"message": f"Invalid JSON payload: {e}", "type": "invalid_request_error"}},
                    status=400,
                )

        payload = _payload
        auth_header = request.headers.get("Authorization") or ""
        bearer_token = ""
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:].strip()
            if bearer_token in {"dummy", "none", "token", "default", "antigravity"}:
                bearer_token = ""

        if self.boundary.api_key:
            bearer_token = ""
        is_stream = bool(payload.get("stream"))

        if is_stream:
            stream_gen = self.client.stream_chat_completion(payload, bearer_token=bearer_token)
            try:
                first_chunk = await stream_gen.__anext__()
            except Exception as e:
                with contextlib.suppress(Exception):
                    await stream_gen.aclose()
                logger.error("Error connecting to chat completion stream: %s", type(e).__name__)
                status_code = _upstream_status(e)
                err_type = "rate_limit_error" if status_code == 429 else "api_error"
                return web.json_response(
                    {"error": {"message": public_error(e), "type": err_type, "code": status_code}},
                    status=status_code,
                )

            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
            try:
                await response.prepare(request)
                await response.write(first_chunk.encode("utf-8"))
                try:
                    async for chunk_str in stream_gen:
                        await response.write(chunk_str.encode("utf-8"))
                except Exception as e:
                    logger.error("Error during chat completion stream: %s", type(e).__name__)
                    event = {"error": {"message": public_error(e), "type": "api_error"}}
                    await response.write(("data: " + json.dumps(event) + "\n\n").encode("utf-8"))
                await response.write_eof()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                logger.debug("Client disconnected during streaming: %s", e)
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.debug("Client connection lost during streaming: %s", e)
                else:
                    logger.error("Unexpected error during streaming: %s", type(e).__name__)
            finally:
                with contextlib.suppress(Exception):
                    await stream_gen.aclose()
            return response
        else:
            try:
                result = await self.client.create_chat_completion(payload, bearer_token=bearer_token)
                return web.json_response(result)
            except Exception as e:
                logger.error("Error during chat completion: %s", type(e).__name__)
                status_code = _upstream_status(e)
                err_type = "rate_limit_error" if status_code == 429 else "api_error"
                return web.json_response(
                    {"error": {"message": public_error(e), "type": err_type, "code": status_code}},
                    status=status_code,
                )

    # ------------------------------------------------------------------
    # Claude Code CLI handlers
    # ------------------------------------------------------------------

    async def handle_claude_code_models(self, request: web.Request) -> web.Response:
        force_refresh = request.query.get("refresh") in {"1", "true", "yes"}
        models = await self.claude_code_client.list_models(force_refresh=force_refresh)
        return web.json_response({
            "object": "list",
            "data": [
                {
                    "id": model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "claude-code-cli",
                    "permission": [],
                }
                for model in models
            ],
        })

    async def handle_claude_code_completions(
        self, request: web.Request, *, _payload: dict | None = None
    ) -> web.StreamResponse:
        if _payload is None:
            try:
                _payload = await read_payload(request)
            except Exception as exc:
                return web.json_response(
                    {"error": {"message": f"Invalid JSON payload: {exc}", "type": "invalid_request_error"}},
                    status=400,
                )
        try:
            result = await self.claude_code_client.create_chat_completion(_payload)
        except Exception as exc:
            logger.error("Claude Code CLI completion failed: %s", type(exc).__name__)
            status_code = _upstream_status(exc)
            err_type = "rate_limit_error" if status_code == 429 else "api_error"
            return web.json_response(
                {"error": {"message": public_error(exc), "type": err_type, "code": status_code}},
                status=status_code,
            )
        if not _payload.get("stream"):
            return web.json_response(result)

        choice = result["choices"][0]
        delta = dict(choice["message"])
        response = web.StreamResponse(
            status=200,
            headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
        )
        await response.prepare(request)
        chunk = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": result["created"],
            "model": result["model"],
            "choices": [{"index": 0, "delta": delta, "finish_reason": choice["finish_reason"]}],
        }
        await response.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
        await response.write(b"data: [DONE]\n\n")
        await response.write_eof()
        return response

    # ------------------------------------------------------------------
    # Codex CLI handlers
    # ------------------------------------------------------------------

    async def handle_codex_models(self, request: web.Request) -> web.Response:
        if self.codex_client is None:
            return web.json_response(
                {"error": {"message": "Codex CLI module is not available.", "type": "api_error"}},
                status=503,
            )
        force_refresh = request.query.get("refresh") in {"1", "true", "yes"}
        models = await self.codex_client.list_models(force_refresh=force_refresh)
        return web.json_response({
            "object": "list",
            "data": [
                {
                    "id": m["id"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "codex-cli",
                    "permission": [],
                    "name": m.get("name", m["id"]),
                    "description": m.get("description", ""),
                }
                for m in models
            ],
        })

    async def handle_codex_completions(
        self, request: web.Request, *, _payload: dict | None = None
    ) -> web.Response:
        if self.codex_client is None:
            return web.json_response(
                {"error": {"message": "Codex CLI module is not available.", "type": "api_error"}},
                status=503,
            )
        if _payload is None:
            try:
                _payload = await read_payload(request)
            except Exception as exc:
                return web.json_response(
                    {"error": {"message": f"Invalid JSON payload: {exc}", "type": "invalid_request_error"}},
                    status=400,
                )
        try:
            result = await self.codex_client.create_chat_completion(_payload)
        except Exception as exc:
            logger.error("Codex CLI completion failed: %s", type(exc).__name__)
            status_code = _upstream_status(exc)
            err_type = "rate_limit_error" if status_code == 429 else "api_error"
            return web.json_response(
                {"error": {"message": public_error(exc), "type": err_type, "code": status_code}},
                status=status_code,
            )
        if not _payload.get("stream"):
            return web.json_response(result)

        # Simulate SSE for clients that request stream=true (Codex CLI is non-streaming)
        choice = result["choices"][0]
        delta = dict(choice["message"])
        response = web.StreamResponse(
            status=200,
            headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
        )
        await response.prepare(request)
        chunk = {
            "id": result["id"],
            "object": "chat.completion.chunk",
            "created": result["created"],
            "model": result["model"],
            "choices": [{"index": 0, "delta": delta, "finish_reason": choice["finish_reason"]}],
        }
        await response.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
        await response.write(b"data: [DONE]\n\n")
        await response.write_eof()
        return response

    # ------------------------------------------------------------------
    # Account pool management API
    # ------------------------------------------------------------------

    def _get_pool_or_error(self, provider: str):
        valid = {"codex", "claude-code"}
        if provider not in valid:
            return None, web.json_response(
                {"error": f"Unknown provider '{provider}'. Valid providers: {sorted(valid)}"},
                status=400,
            )
        try:
            from bridge.account_pool import get_pool
        except ImportError:
            try:
                from tools.antigravity_bridge.account_pool import get_pool
            except ImportError:
                return None, web.json_response(
                    {"error": "AccountPool module is not available."}, status=503
                )
        return get_pool(provider), None

    async def handle_list_accounts(self, request: web.Request) -> web.Response:
        provider = request.match_info["provider"]
        pool, err = self._get_pool_or_error(provider)
        if err is not None:
            return err
        return web.json_response(pool.status_dict())

    async def handle_add_account(self, request: web.Request) -> web.Response:
        provider = request.match_info["provider"]
        pool, err = self._get_pool_or_error(provider)
        if err is not None:
            return err
        try:
            body = await read_payload(request)
        except Exception:
            return web.json_response({"error": "Invalid JSON object"}, status=400)
        if (not isinstance(body, dict) or set(body) - {"name", "notes"}
                or any(not isinstance(v, str) or len(v) > 2000 for v in body.values())):
            return web.json_response({"error": "Invalid account fields"}, status=400)
        name = body.get("name") or None
        notes = body.get("notes", "")
        account = pool.add_account(name=name, notes=notes)
        instructions = pool.login_instructions(account)
        return web.json_response({
            "id": account.id,
            "name": account.name,
            "config_dir": account.config_dir,
            "login_instructions": instructions,
            "message": (
                f"Account '{account.name}' registered. "
                f"Run the login_instructions in your terminal to authenticate."
            ),
        }, status=201)

    async def handle_remove_account(self, request: web.Request) -> web.Response:
        provider = request.match_info["provider"]
        pool, err = self._get_pool_or_error(provider)
        if err is not None:
            return err
        try:
            account_id = int(request.match_info["account_id"])
        except ValueError:
            return web.json_response({"error": "account_id must be an integer."}, status=400)
        ok = pool.remove_account(account_id)
        if not ok:
            return web.json_response({"error": f"Account {account_id} not found."}, status=404)
        return web.json_response({"ok": True, "message": f"Account {account_id} disabled."})

    async def handle_update_account(self, request: web.Request) -> web.Response:
        provider = request.match_info["provider"]
        pool, err = self._get_pool_or_error(provider)
        if err is not None:
            return err
        try:
            account_id = int(request.match_info["account_id"])
        except ValueError:
            return web.json_response({"error": "account_id must be an integer."}, status=400)
        try:
            body = await read_payload(request)
        except Exception:
            return web.json_response({"error": "Invalid JSON object"}, status=400)
        if body.get("enabled") is True:
            ok = pool.enable_account(account_id)
            if not ok:
                return web.json_response({"error": f"Account {account_id} not found."}, status=404)
            return web.json_response({"ok": True, "message": f"Account {account_id} enabled."})
        return web.json_response({"error": "Unsupported patch operation."}, status=400)

    async def handle_clear_limit(self, request: web.Request) -> web.Response:
        """Manually clear rate-limit cooldown for an account."""
        provider = request.match_info["provider"]
        pool, err = self._get_pool_or_error(provider)
        if err is not None:
            return err
        try:
            account_id = int(request.match_info["account_id"])
        except ValueError:
            return web.json_response({"error": "account_id must be an integer."}, status=400)
        ok = pool.clear_rate_limit(account_id)
        if not ok:
            return web.json_response({"error": f"Account {account_id} not found."}, status=404)
        return web.json_response({"ok": True, "message": f"Rate limit cleared for account {account_id}."})

    async def start(self) -> web.AppRunner:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        try:
            await site.start()
        except BaseException:
            await runner.cleanup()
            raise
        logger.info("Hermes Multi-Provider Bridge listening on http://%s:%s", self.host, self.port)
        return runner


def run_server(host: str = DEFAULT_BRIDGE_HOST, port: int = DEFAULT_BRIDGE_PORT) -> None:
    """Run the bridge server in the foreground."""
    server = AntigravityBridgeServer(host=host, port=port)
    web.run_app(server.app, host=host, port=port)


def bridge_launch_command(host=DEFAULT_BRIDGE_HOST, port=DEFAULT_BRIDGE_PORT):
    """Return argv/cwd for either supported layout; never interpolate user paths into Python."""
    require_loopback(host)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Bridge port must be an integer in 1..65535")
    source = Path(__file__).resolve()
    if source.parent.name == "bridge":
        module, root = "bridge.server", source.parents[1]
    else:
        module, root = "tools.antigravity_bridge.server", source.parents[2]
    code = f"import sys; from {module} import run_server; run_server(host=sys.argv[1], port=int(sys.argv[2]))"
    return [sys.executable, "-u", "-c", code, host, str(port)], root


def is_server_running(host: str = DEFAULT_BRIDGE_HOST, port: int = DEFAULT_BRIDGE_PORT) -> bool:
    """Bounded direct-loopback health check, without proxies or redirects."""
    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        bridge_launch_command(host, port)  # Validate before constructing the URL.
        authority = f"[{host}]" if ":" in host else host
        req = urllib.request.Request(f"http://{authority}:{port}/health")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(req, timeout=1.0) as resp:
            raw = resp.read(16385)
        if len(raw) > 16384:
            return False
        data = json.loads(raw.decode("utf-8"))
        return isinstance(data, dict) and data.get("status") == "ok" and data.get("bridge") in {"antigravity", "hermes-multi-provider"}
    except Exception:
        return False


def _ensure_bridge_running(
    host: str = DEFAULT_BRIDGE_HOST,
    port: int = DEFAULT_BRIDGE_PORT,
    timeout: float = 3.0,
    *,
    require_antigravity_credentials: bool,
) -> bool:
    """Ensure the shared bridge server is running, spawning a daemon if not."""
    cmd, package_root = bridge_launch_command(host, port)
    if is_server_running(host=host, port=port):
        return True

    import subprocess
    import sys
    import time

    if require_antigravity_credentials:
        try:
            mgr = AntigravityAuthManager()
            if not mgr.load_all_stored_credentials():
                return False
        except Exception:
            return False


    try:
        if sys.platform == "win32":
            subprocess.Popen(
                cmd,
                cwd=str(package_root),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        else:
            subprocess.Popen(
                cmd,
                cwd=str(package_root),
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.2)
            if is_server_running(host=host, port=port):
                logger.info("Hermes Bridge auto-started on http://%s:%s", host, port)
                return True
        return is_server_running(host=host, port=port)
    except Exception as e:
        logger.warning("Failed to auto-spawn Hermes Bridge: %s", type(e).__name__)
        return False


def ensure_antigravity_bridge_running(
    host: str = DEFAULT_BRIDGE_HOST, port: int = DEFAULT_BRIDGE_PORT, timeout: float = 3.0
) -> bool:
    return _ensure_bridge_running(
        host, port, timeout, require_antigravity_credentials=True
    )


def ensure_claude_code_bridge_running(
    host: str = DEFAULT_BRIDGE_HOST, port: int = DEFAULT_BRIDGE_PORT, timeout: float = 3.0
) -> bool:
    """Start the local bridge for Claude Code without requiring Google OAuth."""
    return _ensure_bridge_running(
        host, port, timeout, require_antigravity_credentials=False
    )


def ensure_codex_bridge_running(
    host: str = DEFAULT_BRIDGE_HOST, port: int = DEFAULT_BRIDGE_PORT, timeout: float = 3.0
) -> bool:
    """Start the local bridge for Codex CLI without requiring Google OAuth."""
    return _ensure_bridge_running(
        host, port, timeout, require_antigravity_credentials=False
    )
