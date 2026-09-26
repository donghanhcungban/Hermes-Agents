"""Local HTTP boundary. Admin is opt-in; inference stays compatible on loopback.

This is not isolation from other processes running as the same OS user. Use an
OS sandbox for untrusted clients. Never expose this bridge through a public proxy.
"""
from __future__ import annotations
import asyncio
import hmac
import ipaddress
import os
from urllib.parse import urlsplit
from aiohttp import web
from .protocol import strict_json, validate_chat

MAX_BODY = 2 * 1024 * 1024
MAX_INFLIGHT = 8


def is_loopback(host):
    if host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or bool(getattr(ip, "ipv4_mapped", None) and ip.ipv4_mapped.is_loopback)
    except (ValueError, TypeError):
        return False


def require_loopback(host):
    if not is_loopback(host):
        raise ValueError("Bridge must bind to a loopback address; public/LAN binding is disabled")


def public_error(exc):
    status = getattr(exc, "status_code", 500)
    return {
        401: "Provider authentication failed; check the provider login locally.",
        403: "Provider denied the request.",
        429: "Provider rate limit reached; retry after the configured cooldown.",
        503: "Provider unavailable; check the local CLI and account status.",
        504: "Provider timed out.",
    }.get(status, "Provider request failed; inspect local configuration. Raw provider errors are not exposed.")


def error(status, message):
    response = web.json_response({"error": {"message": message, "type": "bridge_error", "code": status}}, status=status)
    response.headers["Cache-Control"] = "no-store"
    if status == 429:
        response.headers["Retry-After"] = "1"
    return response


def _token(name):
    token = os.environ.get(name, "")
    if token and (len(token) < 32 or len(token) > 512 or not token.isascii() or any(c.isspace() for c in token)):
        raise ValueError(f"{name} must be a random ASCII token of 32..512 characters without whitespace")
    return token


def _matches(actual, expected):
    return isinstance(actual, str) and hmac.compare_digest(actual.encode("utf-8"), expected.encode("utf-8"))


class BridgeBoundary:
    def __init__(self, host):
        require_loopback(host)
        self.api_key = _token("HERMES_BRIDGE_API_KEY")
        self.admin_token = _token("HERMES_BRIDGE_ADMIN_TOKEN")
        self.active = 0

        @web.middleware
        async def middleware(request, handler):
            return await self.handle(request, handler)
        self.middleware = middleware

    async def handle(self, request, handler):
        try:
            authority = urlsplit("http://" + request.host)
            valid_host = (
                is_loopback(authority.hostname) and not authority.username and not authority.password
                and not authority.path and not authority.query and not authority.fragment
            )
        except ValueError:
            valid_host = False
        if not valid_host or not is_loopback(request.remote):
            return error(403, "Only direct loopback clients are allowed")
        if ("Origin" in request.headers or request.headers.get("Sec-Fetch-Site", "none") != "none"
                or any(h in request.headers for h in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host"))):
            return error(403, "Browser and forwarded requests are not accepted")
        admin = request.path.startswith(("/auth/", "/v1/accounts/"))
        if admin:
            if not self.admin_token:
                return error(403, "HTTP account administration is disabled; use the local management CLI")
            if not _matches(request.headers.get("X-Hermes-Admin-Token", ""), self.admin_token):
                return error(401, "An administrative token is required")
        elif self.api_key and request.path != "/health":
            if not _matches(request.headers.get("Authorization", ""), "Bearer " + self.api_key):
                return error(401, "A local bridge API key is required")
        if request.method == "OPTIONS":
            return error(403, "Browser preflight is not supported")
        if request.path == "/health":
            return await handler(request)
        if self.active >= MAX_INFLIGHT:
            return error(429, "Bridge is busy; retry later")
        self.active += 1
        try:
            if request.method in {"POST", "PATCH"}:
                if request.content_type != "application/json":
                    return error(415, "Content-Type must be application/json")
                raw = await asyncio.wait_for(request.read(), timeout=15)
                try:
                    payload = strict_json(raw.decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("JSON payload must be an object")
                    if request.path.endswith("/chat/completions"):
                        validate_chat(payload)
                except (ValueError, TypeError, UnicodeError, RecursionError):
                    return error(400, "Invalid JSON payload or unsupported message/tool shape")
                request["bridge_payload"] = payload
            return await handler(request)
        except web.HTTPException as exc:
            return error(exc.status, exc.reason)
        except TimeoutError:
            response = error(408, "Request body timed out")
            response.force_close()
            return response
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            raise
        except Exception:
            return error(500, "Bridge operation failed; details are not exposed")
        finally:
            self.active -= 1


async def read_payload(request):
    """Reuse the validated JSON object rather than parsing the body twice."""
    if "bridge_payload" in request:
        return request["bridge_payload"]
    return strict_json(await request.text())
