from __future__ import annotations

from fastapi import Header, Request

from app.core.errors import AppError


async def require_local_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    """Enforce the local session token on every request (Security PR-1).

    SECURITY_HARDENING_PLAN.md section 6: Electron generates a short-lived
    local_session_token and passes it to every backend request as
    `Authorization: Bearer <token>`. This closes the last open item on
    Security Gate 0's backend localhost/auth requirement — until now the
    backend bound to 127.0.0.1 but accepted any local request unauthenticated.

    Fails open only when the server itself has no configured token (local_token
    is None) — that only happens when running standalone for tests or direct
    `uvicorn` dev use per the README; the real Electron-launched path always
    sets RICKY_LOCAL_TOKEN before spawning the backend, so that path is always
    enforced.
    """
    settings = request.app.state.settings
    expected = settings.local_token
    if not expected:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Missing local session token.", status_code=401)

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise AppError("UNAUTHORIZED", "Invalid local session token.", status_code=401)
