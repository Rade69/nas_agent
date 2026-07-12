"""Root pytest conftest.

Security Gate 1 fix (2026-07-12, docs/PROJECT_OVERVIEW.md section 4.7):
app/core/auth.py used to fail open when no RICKY_LOCAL_TOKEN was configured,
which is exactly the case for the shared `app.main.app` singleton most of
this test suite imports directly (`from app.main import app`) — those tests
exercise business logic, not auth, and never sent an Authorization header.
Now that auth always fails closed, that singleton needs an explicit
dependency override so the ~200 existing tests built against it don't all
have to learn about tokens. Auth enforcement itself is covered by
tests/test_auth.py and tests/test_security_self_test.py, which build their
own app instances via create_app() and are untouched by this override —
FastAPI's dependency_overrides is per-app-instance, not global.
"""
from __future__ import annotations

from app.core.auth import require_local_token
from app.main import app as _shared_app

_shared_app.dependency_overrides[require_local_token] = lambda: None
