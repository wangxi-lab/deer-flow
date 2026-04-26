"""Password-auth middleware for the Gateway API."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

PASSWORD_AUTH_COOKIE = "deerflow_auth"


def _load_root_env() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env", override=False)


def is_password_auth_enabled() -> bool:
    _load_root_env()
    enabled = os.getenv("DEERFLOW_AUTH_ENABLED", "").strip().lower()
    if enabled == "false":
        return False
    return enabled == "true" or bool(os.getenv("DEERFLOW_AUTH_PASSWORD"))


def is_password_auth_configured() -> bool:
    _load_root_env()
    return bool(os.getenv("DEERFLOW_AUTH_PASSWORD"))


def _get_signing_secret() -> str:
    _load_root_env()
    return (
        os.getenv("DEERFLOW_AUTH_SECRET")
        or os.getenv("BETTER_AUTH_SECRET")
        or os.getenv("AUTH_SECRET")
        or os.getenv("DEERFLOW_AUTH_PASSWORD")
        or "deerflow-local-password-auth-secret"
    )


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * ((4 - (len(value) % 4)) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _base64_url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _sign(payload: str) -> str:
    digest = hmac.new(
        _get_signing_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _base64_url_encode(digest)


def verify_password_auth_session(cookie_value: str | None) -> dict[str, Any] | None:
    if not cookie_value:
        return None

    try:
        payload, signature = cookie_value.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(payload)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        data = json.loads(_base64_url_decode(payload).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("sub"), str):
        return None
    if not isinstance(data.get("exp"), int | float):
        return None
    if float(data["exp"]) <= time.time():
        return None
    return data


class PasswordAuthMiddleware(BaseHTTPMiddleware):
    """Require the DeerFlow password-auth cookie for Gateway API requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not is_password_auth_enabled():
            return await call_next(request)

        if request.method == "OPTIONS" or request.url.path == "/health":
            return await call_next(request)

        if not is_password_auth_configured():
            return JSONResponse(
                {
                    "ok": False,
                    "error": "AUTH_NOT_CONFIGURED",
                    "message": "Set DEERFLOW_AUTH_PASSWORD before enabling password auth.",
                },
                status_code=401,
            )

        session = verify_password_auth_session(request.cookies.get(PASSWORD_AUTH_COOKIE))
        if not session:
            return JSONResponse(
                {
                    "ok": False,
                    "error": "UNAUTHORIZED",
                    "message": "Please sign in to access DeerFlow Gateway APIs.",
                },
                status_code=401,
            )

        request.state.auth_user = session["sub"]
        return await call_next(request)
