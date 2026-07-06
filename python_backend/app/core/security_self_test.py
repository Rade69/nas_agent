"""Backend-side Security Gate 0 self-test (docs/SECURITY_HARDENING_PLAN.md
section 18, "Production Security Self-Test").

This only covers the checks that are knowable from inside the Python process
(host binding, auth token presence, CORS config, critical-tool confirmation
gating, log redaction). The Electron-side checks (webPreferences, preload
surface, devtools/remote debugging) live in
electron/core/securitySelfTest.cjs, which calls GET /security/self-test and
combines both halves before deciding whether to fail closed.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import is_redaction_enabled


def run_backend_self_test(app: FastAPI, settings: Settings) -> list[dict[str, Any]]:
    return [
        _check(
            "backend_host_is_loopback",
            settings.host == "127.0.0.1",
            f"host={settings.host!r}",
        ),
        _check(
            "backend_auth_token_configured",
            bool(settings.local_token),
            "RICKY_LOCAL_TOKEN is set" if settings.local_token else "RICKY_LOCAL_TOKEN is missing",
        ),
        _check(
            "no_cors_wildcard",
            _no_cors_wildcard(app),
            "no CORSMiddleware with allow_origins=['*']",
        ),
        _check(
            "critical_tools_require_confirmation",
            _critical_tools_gated(app),
            "every risk=critical tool declares requires_confirmation=True",
        ),
        _check(
            "log_redaction_enabled",
            is_redaction_enabled(),
            "root logger has a SecretRedactionFilter attached",
        ),
    ]


def _no_cors_wildcard(app: FastAPI) -> bool:
    for middleware in app.user_middleware:
        if middleware.cls.__name__ != "CORSMiddleware":
            continue
        allow_origins = (middleware.kwargs or {}).get("allow_origins")
        if allow_origins in (["*"], "*"):
            return False
    return True


def _critical_tools_gated(app: FastAPI) -> bool:
    registry = getattr(app.state, "tool_registry", None)
    if registry is None:
        return True
    for tool in registry.list():
        if tool.risk == "critical" and not tool.requires_confirmation:
            return False
    return True


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}
