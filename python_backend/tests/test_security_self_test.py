from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def hardened_client(tmp_path, monkeypatch) -> TestClient:
    """All Gate 0 backend prerequisites configured — the happy path."""
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RICKY_LOCAL_TOKEN", "test-token-abc123")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def unconfigured_client(tmp_path, monkeypatch) -> TestClient:
    """No local token and no secrets — matches dev-without-Electron."""
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("EXA_API_KEY", "")
    app = create_app()
    return TestClient(app)


def test_self_test_passes_when_fully_configured(hardened_client: TestClient) -> None:
    response = hardened_client.get(
        "/security/self-test", headers={"Authorization": "Bearer test-token-abc123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    names = {check["name"] for check in body["checks"]}
    assert names == {
        "backend_host_is_loopback",
        "backend_auth_token_configured",
        "no_cors_wildcard",
        "critical_tools_require_confirmation",
        "log_redaction_enabled",
    }
    assert all(check["passed"] for check in body["checks"])


def test_self_test_reports_missing_token_and_missing_redaction(
    unconfigured_client: TestClient,
) -> None:
    response = unconfigured_client.get("/security/self-test")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    failed = {check["name"] for check in body["checks"] if not check["passed"]}
    assert "backend_auth_token_configured" in failed
    assert "log_redaction_enabled" in failed
    # Unrelated checks still pass — one missing prerequisite doesn't mask others.
    passed = {check["name"] for check in body["checks"] if check["passed"]}
    assert "backend_host_is_loopback" in passed
    assert "no_cors_wildcard" in passed
    assert "critical_tools_require_confirmation" in passed


def test_self_test_requires_auth_like_every_other_route(hardened_client: TestClient) -> None:
    response = hardened_client.get("/security/self-test")
    assert response.status_code == 401
