"""Tests for email_draft_stage / email_prepare_draft (docs/EMAIL_COMPOSE_
TOOL_PLAN_V2_GMAIL.md Faza B).

Handler-level tests monkeypatch app.tools.messaging.email.gmail_draft_adapter
so they never launch real Chrome — the real end-to-end Gmail flow was
verified manually (agent_reports/2026-07-13_email-faza-a-gmail-draft-adapter.md).
/tools/execute-level tests cover the permission gate (Computer Mode +
confirmation), which is what actually protects this tool.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.core.errors import AppError
from app.main import create_app
from app.services.email_draft_store import EmailDraftStore
from app.tools.messaging import email as email_tools


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def _approved_context(client: TestClient, tool_name: str, arguments: dict) -> tuple[dict, dict]:
    created = client.post(
        "/confirmations",
        json={"action_name": tool_name, "payload": arguments, "risk_level": "high", "tool_name": tool_name},
    )
    assert created.status_code == 200
    confirmation_id = created.json()["id"]
    approved = client.post(f"/confirmations/{confirmation_id}/approve")
    assert approved.status_code == 200
    return {"computer_mode": True, "confirmation_id": confirmation_id}, approved.json()["confirmation"]


# ---------------------------------------------------------------------------
# Handler-level tests (gmail_draft_adapter monkeypatched — no real Chrome)
# ---------------------------------------------------------------------------


def _handlers(tmp_path: Path) -> tuple[dict, EmailDraftStore]:
    store = EmailDraftStore()
    return email_tools.make_handlers(store, tmp_path), store


def test_email_draft_stage_returns_draft_id_and_safe_summary(tmp_path: Path) -> None:
    handlers, _store = _handlers(tmp_path)
    result = handlers["email_draft_stage"]({"to": "a@example.com", "subject": "Hi", "body": "Hello there"})
    assert result["draft_id"].startswith("draft_")
    assert result["to"] == "a@example.com"
    assert result["subject"] == "Hi"
    assert result["body_length"] == len("Hello there")
    assert "Hello there" not in str(result["artifact"])


@pytest.mark.parametrize(
    "arguments",
    [
        {"subject": "Hi", "body": "Hello"},  # missing to
        {"to": "a@example.com", "body": "Hello"},  # missing subject
        {"to": "a@example.com", "subject": "Hi"},  # missing body
        {"to": "", "subject": "Hi", "body": "Hello"},  # empty to
        {"to": "a@example.com", "subject": "Hi", "body": "   "},  # whitespace-only body
    ],
)
def test_email_draft_stage_rejects_missing_fields(tmp_path: Path, arguments: dict) -> None:
    handlers, _store = _handlers(tmp_path)
    with pytest.raises(ValueError):
        handlers["email_draft_stage"](arguments)


def test_email_draft_stage_rejects_cc_bcc(tmp_path: Path) -> None:
    handlers, _store = _handlers(tmp_path)
    with pytest.raises(ValueError):
        handlers["email_draft_stage"]({"to": "a@example.com", "subject": "Hi", "body": "Hello", "cc": "c@example.com"})


def test_email_prepare_draft_missing_draft_id_raises_value_error(tmp_path: Path) -> None:
    handlers, _store = _handlers(tmp_path)
    with pytest.raises(ValueError):
        handlers["email_prepare_draft"]({})


def test_email_prepare_draft_unknown_draft_id_raises_app_error(tmp_path: Path) -> None:
    handlers, _store = _handlers(tmp_path)
    with pytest.raises(AppError) as exc_info:
        handlers["email_prepare_draft"]({"draft_id": "draft_does_not_exist"})
    assert exc_info.value.code == "EMAIL_DRAFT_NOT_FOUND"


def test_email_prepare_draft_success_discards_draft_and_closes_chrome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handlers, store = _handlers(tmp_path)
    draft_id = store.stage(to="a@example.com", subject="Hi", body="Hello")

    fake_session = MagicMock()
    launch = MagicMock(return_value=fake_session)
    open_compose = MagicMock(return_value=999)
    close = MagicMock()
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "launch_isolated_chrome", launch)
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "open_compose", open_compose)
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "set_subject_field", MagicMock())
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "set_body_field", MagicMock())
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "set_recipient_field", MagicMock())
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "verify_draft_values", MagicMock(return_value=True))
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "close_isolated_chrome", close)

    result = handlers["email_prepare_draft"]({"draft_id": draft_id})

    assert result["ok"] is True
    assert result["sent"] is False
    assert result["verified"] is True
    launch.assert_called_once()
    open_compose.assert_called_once_with(fake_session)
    close.assert_called_once_with(fake_session)
    # One-shot: the draft must be gone regardless of outcome (S-04 principle).
    assert store.get(draft_id) is None


def test_email_prepare_draft_discards_draft_even_on_adapter_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handlers, store = _handlers(tmp_path)
    draft_id = store.stage(to="a@example.com", subject="Hi", body="Hello")

    fake_session = MagicMock()
    close = MagicMock()
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "launch_isolated_chrome", MagicMock(return_value=fake_session))
    monkeypatch.setattr(
        email_tools.gmail_draft_adapter,
        "open_compose",
        MagicMock(side_effect=AppError("GMAIL_NOT_LOGGED_IN", "not logged in", status_code=409)),
    )
    monkeypatch.setattr(email_tools.gmail_draft_adapter, "close_isolated_chrome", close)

    with pytest.raises(AppError) as exc_info:
        handlers["email_prepare_draft"]({"draft_id": draft_id})

    assert exc_info.value.code == "GMAIL_NOT_LOGGED_IN"
    close.assert_called_once_with(fake_session)
    assert store.get(draft_id) is None


# ---------------------------------------------------------------------------
# /tools/execute-level permission gate tests
# ---------------------------------------------------------------------------


def test_email_draft_stage_does_not_require_computer_mode_or_confirmation(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "email_draft_stage", "arguments": {"to": "a@example.com", "subject": "Hi", "body": "Hello"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["draft_id"].startswith("draft_")


def test_email_prepare_draft_fails_without_computer_mode(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "email_prepare_draft", "arguments": {"draft_id": "draft_x"}, "context": {"computer_mode": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "COMPUTER_MODE_REQUIRED"


def test_email_prepare_draft_fails_without_confirmation(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "email_prepare_draft", "arguments": {"draft_id": "draft_x"}, "context": {"computer_mode": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_email_prepare_draft_confirmation_payload_is_just_draft_id(client: TestClient) -> None:
    """The whole point of the two-tool split (email_draft_store.py's header
    comment) — the persisted confirmation payload must never carry actual
    email content, only the draft_id reference."""
    stage_response = client.post(
        "/tools/execute",
        json={
            "tool_name": "email_draft_stage",
            "arguments": {"to": "secret@example.com", "subject": "Confidential", "body": "sensitive body text"},
        },
    )
    draft_id = stage_response.json()["result"]["draft_id"]

    _context, confirmation = _approved_context(client, "email_prepare_draft", {"draft_id": draft_id})
    payload = confirmation["payload"]
    assert payload == {"draft_id": draft_id}
    assert "secret@example.com" not in str(payload)
    assert "sensitive body text" not in str(payload)
