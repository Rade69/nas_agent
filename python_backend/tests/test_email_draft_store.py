"""Tests for the in-memory email draft store (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_
GMAIL.md Faza B) — TTL expiry, safe-summary redaction (never the body)."""
from __future__ import annotations

from app.services.email_draft_store import EmailDraftStore, draft_to_safe_summary


def test_stage_and_get_roundtrip() -> None:
    store = EmailDraftStore()
    draft_id = store.stage(to="a@example.com", subject="Hi", body="Hello there")
    draft = store.get(draft_id)
    assert draft is not None
    assert draft.to == "a@example.com"
    assert draft.subject == "Hi"
    assert draft.body == "Hello there"


def test_get_unknown_id_returns_none() -> None:
    store = EmailDraftStore()
    assert store.get("draft_does_not_exist") is None


def test_discard_removes_draft() -> None:
    store = EmailDraftStore()
    draft_id = store.stage(to="a@example.com", subject="Hi", body="Hello")
    store.discard(draft_id)
    assert store.get(draft_id) is None


def test_draft_ids_are_unique() -> None:
    store = EmailDraftStore()
    ids = {store.stage(to="a@example.com", subject="S", body="B") for _ in range(20)}
    assert len(ids) == 20


def test_expired_draft_is_not_returned() -> None:
    store = EmailDraftStore(ttl_seconds=0)
    draft_id = store.stage(to="a@example.com", subject="Hi", body="Hello")
    # created_at uses time.monotonic() at stage time; ttl_seconds=0 means
    # any elapsed wall-clock time, however small, is already "expired".
    import time

    time.sleep(0.01)
    assert store.get(draft_id) is None


def test_safe_summary_never_includes_body_text() -> None:
    store = EmailDraftStore()
    draft_id = store.stage(to="a@example.com", subject="Confidential subject", body="secret body content")
    draft = store.get(draft_id)
    assert draft is not None
    summary = draft_to_safe_summary(draft)
    assert "secret body content" not in str(summary)
    assert summary["body_length"] == len("secret body content")
    assert summary["to"] == "a@example.com"
    assert summary["subject"] == "Confidential subject"


def test_safe_summary_reports_has_cc_has_bcc() -> None:
    store = EmailDraftStore()
    draft_id = store.stage(to="a@example.com", subject="S", body="B", cc="c@example.com")
    draft = store.get(draft_id)
    assert draft is not None
    summary = draft_to_safe_summary(draft)
    assert summary["has_cc"] is True
    assert summary["has_bcc"] is False
