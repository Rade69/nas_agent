"""Email draft tool handlers (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md Faza B).

Two tools, deliberately split — see app/services/email_draft_store.py's
header for why: email_draft_stage (low risk, no confirmation) takes the
real to/subject/body/cc/bcc and stores them in memory only, returning a
draft_id + a safe summary. email_prepare_draft (high risk, confirmed,
requires Computer Mode) takes ONLY draft_id, so the confirmation payload
persisted by the existing generic confirmation bridge is never more than a
random reference — never the actual email content.

email_prepare_draft is the one that actually drives GmailDraftAdapter
(Faza A) — opens the isolated Chrome profile, fills the fields, verifies,
and closes. It never clicks Send (see gmail_draft_adapter.py's module
docstring for the structural guarantee).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.services import gmail_draft_adapter
from app.services.email_draft_store import EmailDraftStore, draft_to_safe_summary


def make_handlers(draft_store: EmailDraftStore, data_dir: Path) -> dict[str, Any]:
    def email_draft_stage(arguments: dict[str, Any]) -> dict[str, Any]:
        to = str(arguments.get("to") or "").strip()
        subject = str(arguments.get("subject") or "").strip()
        body = str(arguments.get("body") or "")
        cc = arguments.get("cc")
        bcc = arguments.get("bcc")

        if not to:
            raise ValueError("email_draft_stage requires a non-empty 'to' argument.")
        if not subject:
            raise ValueError("email_draft_stage requires a non-empty 'subject' argument.")
        if not body.strip():
            raise ValueError("email_draft_stage requires a non-empty 'body' argument.")
        # Faza A limitation (agent_reports/2026-07-13_email-faza-a-gmail-draft-
        # adapter.md): GmailDraftAdapter.set_recipient_field rejects cc/bcc —
        # fail here, at staging time, rather than let the model/user get all
        # the way to an approved confirmation that would then fail.
        if cc or bcc:
            raise ValueError("Cc/Bcc are not supported yet — send this email without Cc/Bcc for now.")

        draft_id = draft_store.stage(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        draft = draft_store.get(draft_id)
        assert draft is not None  # just stored it under the same lock-protected call
        summary = draft_to_safe_summary(draft)

        return {
            "draft_id": draft_id,
            **summary,
            "artifact": {
                "title": "Email Draft",
                "kind": "text",
                "content": (
                    f"Prima: {summary['to']}\n"
                    f"Predmet: {summary['subject']}\n"
                    f"Tijelo: {summary['body_length']} znakova"
                ),
            },
        }

    def email_prepare_draft(arguments: dict[str, Any]) -> dict[str, Any]:
        draft_id = str(arguments.get("draft_id") or "")
        if not draft_id:
            raise ValueError("email_prepare_draft requires 'draft_id' from a prior email_draft_stage call.")

        draft = draft_store.get(draft_id)
        if draft is None:
            raise AppError(
                "EMAIL_DRAFT_NOT_FOUND",
                f"Draft '{draft_id}' was not found or has expired (drafts last a few minutes) — stage it again.",
                status_code=404,
            )

        session = gmail_draft_adapter.launch_isolated_chrome(data_dir)
        try:
            dialog_id = gmail_draft_adapter.open_compose(session)
            gmail_draft_adapter.set_subject_field(session, dialog_id, draft.subject)
            gmail_draft_adapter.set_body_field(session, dialog_id, draft.body)
            gmail_draft_adapter.set_recipient_field(session, dialog_id, draft.to)
            verified = gmail_draft_adapter.verify_draft_values(session, dialog_id, draft.subject, draft.to)
        finally:
            gmail_draft_adapter.close_isolated_chrome(session)
            # One-shot regardless of outcome — a failed attempt must be
            # re-staged, never silently retried against the same draft_id
            # (matches the confirmation layer's own single-use rule, S-04).
            draft_store.discard(draft_id)

        return {
            "ok": True,
            "sent": False,
            "verified": verified,
            "artifact": {
                "title": "Email Draft Ready",
                "kind": "text",
                "content": "Draft je popunjen u posebnom Chrome prozoru. Pregledaj ga i pošalji ručno.",
            },
        }

    return {
        "email_draft_stage": email_draft_stage,
        "email_prepare_draft": email_prepare_draft,
    }
