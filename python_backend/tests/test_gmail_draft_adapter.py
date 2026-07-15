"""Tests for GmailDraftAdapter (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md Faza A).

Mocks the CDP layer (a fake session with a scripted .call() response queue)
so these run without a real Chrome/Gmail login — that end-to-end path was
verified manually against live Gmail (agent_reports/2026-07-13_email-faza-a-
gmail-draft-adapter.md documents the manual run and its exact results).
These tests cover the adapter's own decision logic: fail-closed cases,
error codes, and the field-lookup/verification contract.
"""
from __future__ import annotations

from typing import Any, Callable

import pytest

from app.core.errors import AppError
from app.services import gmail_draft_adapter as adapter


class FakeSession:
    """Duck-types GmailSession's .call() with a scripted response queue —
    the adapter's free functions only ever touch session.call(), never the
    dataclass fields directly, so this needs no real subprocess/WebSocket."""

    def __init__(self, responder: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        self._responder = responder
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        self.calls.append((method, params))
        return self._responder(method, params)


def _eval_url(url: str):
    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "Runtime.evaluate" and params.get("expression") == "location.href":
            return {"result": {"value": url}}
        return {}

    return responder


def test_is_logged_in_true_for_gmail_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(_eval_url("https://mail.google.com/mail/u/0/#inbox"))
    assert adapter.is_logged_in(session) is True  # type: ignore[arg-type]


def test_is_logged_in_false_for_accounts_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(_eval_url("https://accounts.google.com/signin/v2/identifier"))
    assert adapter.is_logged_in(session) is False  # type: ignore[arg-type]


def test_open_compose_raises_when_not_logged_in(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession(_eval_url("https://accounts.google.com/signin"))
    with pytest.raises(AppError) as exc_info:
        adapter.open_compose(session)  # type: ignore[arg-type]
    assert exc_info.value.code == "GMAIL_NOT_LOGGED_IN"


def test_open_compose_raises_when_no_dialog_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter.time, "sleep", lambda _s: None)
    monkeypatch.setattr(adapter.time, "monotonic", _fake_monotonic_advancing_past_deadline())

    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "Runtime.evaluate" and params.get("expression") == "location.href":
            return {"result": {"value": "https://mail.google.com/mail/u/0/#inbox?compose=new"}}
        if method == "Page.navigate":
            return {}
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelectorAll":
            return {"nodeIds": []}
        return {}

    session = FakeSession(responder)
    with pytest.raises(AppError) as exc_info:
        adapter.open_compose(session)  # type: ignore[arg-type]
    assert exc_info.value.code == "GMAIL_COMPOSE_NOT_FOUND"


def test_open_compose_fails_closed_on_multiple_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter.time, "sleep", lambda _s: None)

    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "Runtime.evaluate" and params.get("expression") == "location.href":
            return {"result": {"value": "https://mail.google.com/mail/u/0/#inbox?compose=new"}}
        if method == "Page.navigate":
            return {}
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelectorAll":
            return {"nodeIds": [10, 20]}
        return {}

    session = FakeSession(responder)
    with pytest.raises(AppError) as exc_info:
        adapter.open_compose(session)  # type: ignore[arg-type]
    assert exc_info.value.code == "GMAIL_MULTIPLE_COMPOSE_DIALOGS"


def test_open_compose_returns_dialog_node_id_for_exactly_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter.time, "sleep", lambda _s: None)

    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "Runtime.evaluate" and params.get("expression") == "location.href":
            return {"result": {"value": "https://mail.google.com/mail/u/0/#inbox?compose=new"}}
        if method == "Page.navigate":
            return {}
        if method == "DOM.getDocument":
            return {"root": {"nodeId": 1}}
        if method == "DOM.querySelectorAll":
            return {"nodeIds": [42]}
        if method == "DOM.querySelector":
            return {"nodeId": 42}
        return {}

    session = FakeSession(responder)
    dialog_id = adapter.open_compose(session)  # type: ignore[arg-type]
    assert dialog_id == 42


def test_set_recipient_field_rejects_cc_bcc_as_unsupported() -> None:
    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "DOM.resolveNode":
            return {"object": {"objectId": "obj-1"}}
        if method == "Runtime.callFunctionOn":
            return {"result": {"objectId": "field-1"}}
        if method == "DOM.requestNode":
            return {"nodeId": 99}
        return {}

    session = FakeSession(responder)
    with pytest.raises(AppError) as exc_info:
        adapter.set_recipient_field(session, dialog_node_id=1, to="a@example.com", cc="b@example.com")  # type: ignore[arg-type]
    assert exc_info.value.code == "GMAIL_CC_BCC_NOT_SUPPORTED"


def test_find_in_dialog_raises_field_not_found_when_no_match() -> None:
    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "DOM.resolveNode":
            return {"object": {"objectId": "obj-1"}}
        if method == "Runtime.callFunctionOn":
            return {"result": {}}  # no objectId => selector matched nothing
        return {}

    session = FakeSession(responder)
    with pytest.raises(AppError) as exc_info:
        adapter._find_in_dialog(session, dialog_node_id=1, selector='input[name="subjectbox"]')  # type: ignore[arg-type]
    assert exc_info.value.code == "GMAIL_FIELD_NOT_FOUND"


def test_verify_draft_values_true_when_matching() -> None:
    # Reads happen in a fixed order (subject then recipient) — a simple
    # queue is enough to give each read call its expected live value.
    read_values = iter(["Test Subject", "someone@example.com"])

    def responder(method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "DOM.resolveNode":
            return {"object": {"objectId": "obj-1"}}
        if method == "Runtime.callFunctionOn":
            fn = params.get("functionDeclaration", "")
            if "querySelector(" in fn:
                return {"result": {"objectId": "field-1"}}
            return {"result": {"value": next(read_values)}}
        if method == "DOM.requestNode":
            return {"nodeId": 55}
        return {}

    session = FakeSession(responder)
    assert (
        adapter.verify_draft_values(session, dialog_node_id=1, expected_subject="Test Subject", expected_to="someone@example.com")  # type: ignore[arg-type]
        is True
    )


def test_free_port_returns_bindable_port() -> None:
    port = adapter._free_port()
    assert 1024 < port < 65536


def test_find_chrome_raises_when_no_candidate_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "CHROME_CANDIDATES", [adapter.Path(r"C:\definitely\not\a\real\path\chrome.exe")])
    with pytest.raises(AppError) as exc_info:
        adapter._find_chrome()
    assert exc_info.value.code == "CHROME_NOT_FOUND"


def _fake_monotonic_advancing_past_deadline() -> Callable[[], float]:
    """Returns a fake time.monotonic() that strictly increases every call.

    A version that jumps to one fixed huge value and then holds there is a
    trap: any deadline computed *after* that jump (e.g. a later polling
    loop's own `time.monotonic() + budget`) is measured against that same
    huge value, so `now < deadline` stays permanently true and the loop
    spins forever with sleep() mocked to a no-op — this happened during
    manual test-writing (172s of CPU burn before it was caught). Advancing
    by a fixed step on every call guarantees any deadline is eventually
    exceeded, no matter how many loops/deadlines are chained in one call."""
    state = {"t": 0.0}

    def fake() -> float:
        state["t"] += 2.0
        return state["t"]

    return fake
