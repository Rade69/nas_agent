"""GET /security/self-test — backend half of the Production Security
Self-Test (Security Gate 0). Returns per-check pass/fail results for
host binding, auth token, CORS, confirmation gating, and log redaction.
"""
from typing import Any

from fastapi import APIRouter, Request

from app.core.security_self_test import run_backend_self_test

router = APIRouter(tags=["security"])


@router.get("/security/self-test")
def get_security_self_test(request: Request) -> dict[str, Any]:
    """Backend half of the Security Gate 0 self-test. Electron calls this at
    startup (with the auth token, since it sits behind the same global
    require_local_token dependency as every other route) and combines the
    result with its own Electron-side checks before deciding whether to fail
    closed in a production build. See
    docs/SECURITY_HARDENING_PLAN.md section 18.
    """
    checks = run_backend_self_test(request.app, request.app.state.settings)
    return {"ok": all(check["passed"] for check in checks), "checks": checks}
