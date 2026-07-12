from __future__ import annotations

from fastapi import Header, Request

from app.core.errors import AppError


async def require_local_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Enforce the local session token on every request (Security PR-1,
    hardened to always fail-closed 2026-07-12 — Security Gate 1 fix).

    SECURITY_HARDENING_PLAN.md section 6: Electron generates a short-lived
    local_session_token and passes it to every backend request as
    `Authorization: Bearer <token>`. This closes the last open item on
    Security Gate 0's backend localhost/auth requirement — until now the
    backend bound to 127.0.0.1 but accepted any local request unauthenticated.

    Always fail-closed. `app.core.config.get_settings()` guarantees
    `settings.local_token` is populated — Electron's own launch path sets
    RICKY_LOCAL_TOKEN, and the dev-without-Electron path (`uvicorn
    app.main:app` per README) auto-generates and persists its own token. This
    used to fail open when local_token was unset, which meant any local
    process — including a malicious webpage's fetch() to 127.0.0.1 — could
    call tools unauthenticated on that path; see
    docs/PROJECT_OVERVIEW.md section 4.7.
    """
    settings = request.app.state.settings
    expected = settings.local_token

    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Missing local session token.", status_code=401)

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise AppError("UNAUTHORIZED", "Invalid local session token.", status_code=401)
