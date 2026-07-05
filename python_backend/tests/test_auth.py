from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def unauthenticated_client(tmp_path, monkeypatch) -> TestClient:
    """No RICKY_LOCAL_TOKEN set — matches tests/dev-without-Electron per README."""
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


def test_no_token_configured_fails_open(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200


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
