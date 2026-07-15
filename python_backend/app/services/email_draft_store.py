"""Short-lived, in-memory email draft store (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md
section 4.6).

Why this exists: the generic confirmation bridge (src/lib/realtime.ts's
executeFunctionCalls, off-limits this session — see agent_reports/2026-07-13_
email-faza-b-prepare-draft-tool.md) persists a confirmed tool's raw call
arguments into the confirmations SQLite table via ConfirmationService.propose()
(app/services/confirmation_service.py). If email_prepare_draft's schema took
to/subject/body directly (as plan section 4.1's illustrative snippet shows),
that content would end up in a persistent, plaintext table — exactly what
the security review (section 4.4) flags. Splitting into two tools closes
this without touching the confirmation bridge: email_draft_stage (low risk,
no confirmation) stores the real content here, in memory only, and returns
a draft_id; email_prepare_draft (high risk, confirmed) takes ONLY draft_id
as its argument, so the confirmation payload that gets persisted is never
more than a random reference.

Deliberately process-local (a plain dict, no SQLite) — a draft is meant to
survive minutes, not restarts, and never being written to disk is the point.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4

DEFAULT_TTL_SECONDS = 300  # 5 minutes, per plan section 4.6 ("2-5 minuta")


@dataclass
class EmailDraft:
    to: str
    subject: str
    body: str
    cc: str | None
    bcc: str | None
    created_at: float = field(default_factory=time.monotonic)


class EmailDraftStore:
    """Process-local, thread-safe TTL store. One instance is shared across
    requests via app.state (see app/main.py), matching how other singleton
    services (ConfirmationService, ToolRegistry) are wired."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl_seconds = ttl_seconds
        self._drafts: dict[str, EmailDraft] = {}
        self._lock = Lock()

    def stage(self, *, to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None) -> str:
        draft_id = f"draft_{uuid4().hex[:16]}"
        with self._lock:
            self._expire_locked()
            self._drafts[draft_id] = EmailDraft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return draft_id

    def get(self, draft_id: str) -> EmailDraft | None:
        with self._lock:
            self._expire_locked()
            return self._drafts.get(draft_id)

    def discard(self, draft_id: str) -> None:
        with self._lock:
            self._drafts.pop(draft_id, None)

    def _expire_locked(self) -> None:
        """Caller must hold self._lock."""
        now = time.monotonic()
        expired = [key for key, draft in self._drafts.items() if now - draft.created_at > self._ttl_seconds]
        for key in expired:
            del self._drafts[key]


def draft_to_safe_summary(draft: EmailDraft) -> dict[str, Any]:
    """Fields safe to return to the model / show in a tool result — never
    the body itself (review section 6.3 "Minimalni action receipt")."""
    return {
        "to": draft.to,
        "subject": draft.subject,
        "body_length": len(draft.body),
        "has_cc": bool(draft.cc),
        "has_bcc": bool(draft.bcc),
    }
