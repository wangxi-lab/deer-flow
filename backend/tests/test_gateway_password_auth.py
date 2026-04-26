import json
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.gateway.auth import (
    PASSWORD_AUTH_COOKIE,
    PasswordAuthMiddleware,
    _base64_url_encode,
    _sign,
    verify_password_auth_session,
)


async def _ok(_request):
    return JSONResponse({"ok": True})


def _client() -> TestClient:
    app = Starlette(routes=[Route("/api/models", _ok), Route("/health", _ok)])
    app.add_middleware(PasswordAuthMiddleware)
    return TestClient(app)


def _session_cookie(username: str = "admin") -> str:
    payload = _base64_url_encode(
        json.dumps({"sub": username, "exp": int(time.time()) + 3600}).encode("utf-8")
    )
    return f"{payload}.{_sign(payload)}"


def test_gateway_password_auth_disabled_allows_requests(monkeypatch):
    monkeypatch.setenv("DEERFLOW_AUTH_ENABLED", "false")
    monkeypatch.setenv("DEERFLOW_AUTH_PASSWORD", "secret")

    response = _client().get("/api/models")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_gateway_password_auth_blocks_missing_cookie(monkeypatch):
    monkeypatch.setenv("DEERFLOW_AUTH_ENABLED", "true")
    monkeypatch.setenv("DEERFLOW_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-signing-secret")

    response = _client().get("/api/models")

    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_gateway_password_auth_allows_valid_cookie(monkeypatch):
    monkeypatch.setenv("DEERFLOW_AUTH_ENABLED", "true")
    monkeypatch.setenv("DEERFLOW_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-signing-secret")

    response = _client().get(
        "/api/models",
        cookies={PASSWORD_AUTH_COOKIE: _session_cookie("deerflow")},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_verify_password_auth_session_rejects_expired_cookie(monkeypatch):
    monkeypatch.setenv("BETTER_AUTH_SECRET", "test-signing-secret")
    payload = _base64_url_encode(
        json.dumps({"sub": "deerflow", "exp": int(time.time()) - 1}).encode("utf-8")
    )

    assert verify_password_auth_session(f"{payload}.{_sign(payload)}") is None
