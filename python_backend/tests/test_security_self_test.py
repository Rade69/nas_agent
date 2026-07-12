from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.security_self_test import run_backend_self_test
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
def auto_token_client(tmp_path, monkeypatch) -> TestClient:
    """No RICKY_LOCAL_TOKEN / OPENAI_API_KEY / EXA_API_KEY env — matches
    dev-without-Electron.

    Security Gate 1 fix (2026-07-12, docs/PROJECT_OVERVIEW.md section 4.7):
    local_token is no longer None here — get_settings() auto-generates one
    (app/core/config.py's _resolve_local_token()) — so this scenario now
    needs a real Authorization header like any other client. The auth
    dependency itself is overridden below purely so this fixture can be used
    for non-auth assertions (see test_self_test_passes_auth_check_even_without_env_token);
    the actual auth enforcement for this scenario is covered separately in
    tests/test_auth.py's test_no_env_token_still_fails_closed.
    """
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("EXA_API_KEY", "")
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
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


def test_self_test_passes_auth_check_even_without_env_token(auto_token_client: TestClient) -> None:
    """Regression test for the Security Gate 1 fix: dev-without-Electron used
    to report backend_auth_token_configured=False (and, as a side effect,
    log_redaction_enabled=False too, since local_token was the only secret
    this scenario ever had to redact). Both now pass, because
    get_settings() auto-generates a real token instead of leaving it unset."""
    response = auto_token_client.get("/security/self-test")
    assert response.status_code == 200
    body = response.json()
    checks = {check["name"]: check["passed"] for check in body["checks"]}
    assert checks["backend_auth_token_configured"] is True
    assert checks["log_redaction_enabled"] is True


def test_self_test_requires_auth_like_every_other_route(hardened_client: TestClient) -> None:
    response = hardened_client.get("/security/self-test")
    assert response.status_code == 401


def test_check_logic_reports_missing_token_and_redaction_for_bare_settings() -> None:
    """Unit-level coverage of the check functions themselves, independent of
    get_settings()'s auto-generation — confirms backend_auth_token_configured
    and log_redaction_enabled still correctly report False for a Settings
    object that genuinely has no token at all. Not reachable through the
    normal create_app() path anymore since the Security Gate 1 fix, but keeps
    the check logic itself honest for any future caller that builds Settings
    directly."""
    bare_settings = Settings(local_token=None, openai_api_key=None, exa_api_key=None)
    configure_logging(
        secrets=[bare_settings.openai_api_key, bare_settings.local_token, bare_settings.exa_api_key]
    )
    app = FastAPI()
    checks = {c["name"]: c["passed"] for c in run_backend_self_test(app, bare_settings)}
    assert checks["backend_auth_token_configured"] is False
    assert checks["log_redaction_enabled"] is False
