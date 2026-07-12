from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def auto_token_client(tmp_path, monkeypatch) -> TestClient:
    """No RICKY_LOCAL_TOKEN set — matches dev-without-Electron per README.

    Security Gate 1 fix (2026-07-12, docs/PROJECT_OVERVIEW.md section 4.7):
    this path used to fail open (any unauthenticated request was let through).
    Now get_settings() auto-generates its own per-process token instead — see
    app/core/config.py's _resolve_local_token() — so auth is still enforced.
    """
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def authenticated_client(tmp_path, monkeypatch) -> TestClient:
    """RICKY_LOCAL_TOKEN set — matches the real Electron-launched path."""
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RICKY_LOCAL_TOKEN", "test-token-abc123")
    app = create_app()
    return TestClient(app)


def test_no_env_token_still_fails_closed(auto_token_client: TestClient) -> None:
    response = auto_token_client.get("/health")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_no_env_token_auto_generates_and_persists_one(tmp_path, monkeypatch) -> None:
    """The core Security Gate 1 regression test: even with no Electron and no
    RICKY_LOCAL_TOKEN, a real per-process token exists, is written to a file
    a developer can read, and actually authenticates requests."""
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    app = create_app()
    client = TestClient(app)

    token_file = tmp_path / "dev_local_token.txt"
    assert token_file.exists()
    token = token_file.read_text(encoding="utf-8").strip()
    assert token == app.state.settings.local_token
    assert len(token) > 20

    response = client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_configured_token_blocks_missing_header(authenticated_client: TestClient) -> None:
    response = authenticated_client.get("/health")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_configured_token_blocks_wrong_token(authenticated_client: TestClient) -> None:
    response = authenticated_client.get(
        "/health", headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_configured_token_blocks_malformed_header(authenticated_client: TestClient) -> None:
    response = authenticated_client.get(
        "/health", headers={"Authorization": "test-token-abc123"}
    )
    assert response.status_code == 401


def test_configured_token_allows_correct_token(authenticated_client: TestClient) -> None:
    response = authenticated_client.get(
        "/health", headers={"Authorization": "Bearer test-token-abc123"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_configured_token_protects_tools_endpoint_too(authenticated_client: TestClient) -> None:
    unauthorized = authenticated_client.get("/tools")
    assert unauthorized.status_code == 401

    authorized = authenticated_client.get(
        "/tools", headers={"Authorization": "Bearer test-token-abc123"}
    )
    assert authorized.status_code == 200
