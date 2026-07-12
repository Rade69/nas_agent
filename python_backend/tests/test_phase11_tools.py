from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def test_note_add_creates_note_and_artifact(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={
            "tool_name": "note_add",
            "arguments": {"text": "Remember the milk", "tags": ["shopping"]},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tool_name"] == "note_add"
    assert body["result"]["note"]["text"] == "Remember the milk"
    assert body["result"]["note"]["tags"] == ["shopping"]
    assert body["result"]["artifact"]["kind"] == "notes"


def test_note_add_requires_text(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "note_add", "arguments": {"text": ""}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error"]["code"] == "INVALID_ARGUMENTS"


def test_note_search_finds_by_text(client: TestClient) -> None:
    client.post(
        "/tools/execute",
        json={"tool_name": "note_add", "arguments": {"text": "buy milk", "tags": ["errands"]}},
    )
    client.post(
        "/tools/execute",
        json={"tool_name": "note_add", "arguments": {"text": "call mom", "tags": ["family"]}},
    )
    response = client.post(
        "/tools/execute",
        json={"tool_name": "note_search", "arguments": {"query": "milk"}},
    )
    assert response.status_code == 200
    body = response.json()["result"]
    assert len(body["notes"]) == 1
    assert body["notes"][0]["text"] == "buy milk"


def test_note_list_returns_recent(client: TestClient) -> None:
    for index in range(3):
        client.post(
            "/tools/execute",
            json={"tool_name": "note_add", "arguments": {"text": f"note {index}"}},
        )
    response = client.post(
        "/tools/execute",
        json={"tool_name": "note_list", "arguments": {"limit": 10}},
    )
    assert response.status_code == 200
    notes = response.json()["result"]["notes"]
    assert len(notes) == 3


def test_records_create_and_search(client: TestClient) -> None:
    create = client.post(
        "/tools/execute",
        json={
            "tool_name": "records_create",
            "arguments": {
                "collection": "tasks",
                "title": "Setup CI",
                "fields": {"priority": "high", "owner": "ricky"},
            },
        },
    )
    assert create.status_code == 200
    assert create.json()["ok"] is True
    record = create.json()["result"]["record"]
    assert record["collection"] == "tasks"
    assert record["fields"]["priority"] == "high"

    search = client.post(
        "/tools/execute",
        json={"tool_name": "records_search", "arguments": {"collection": "tasks", "query": "CI"}},
    )
    assert search.status_code == 200
    results = search.json()["result"]["records"]
    assert len(results) == 1
    assert results[0]["title"] == "Setup CI"


def test_records_update_merges_fields(client: TestClient) -> None:
    create = client.post(
        "/tools/execute",
        json={
            "tool_name": "records_create",
            "arguments": {"collection": "x", "title": "Rec", "fields": {"a": 1}},
        },
    )
    record_id = create.json()["result"]["record"]["id"]
    update = client.post(
        "/tools/execute",
        json={
            "tool_name": "records_update",
            "arguments": {"id": record_id, "fields": {"b": 2}},
        },
    )
    assert update.status_code == 200
    fields = update.json()["result"]["record"]["fields"]
    assert fields == {"a": 1, "b": 2}


def test_records_delete_requires_confirmation_id(client: TestClient) -> None:
    """records_delete is critical risk — FAZA 10 permission engine gates it
    behind an approved confirmation_id (not the legacy `confirmed: true` arg).
    """
    create = client.post(
        "/tools/execute",
        json={"tool_name": "records_create", "arguments": {"collection": "x", "title": "Rec"}},
    )
    record_id = create.json()["result"]["record"]["id"]

    # 1) Without confirmation_id → CONFIRMATION_REQUIRED (FAZA 10 permission engine).
    no_confirm = client.post(
        "/tools/execute",
        json={"tool_name": "records_delete", "arguments": {"id": record_id, "confirmed": True}},
    )
    assert no_confirm.status_code == 200
    body = no_confirm.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"

    # 2) With an approved confirmation_id bound to this tool/payload → succeeds.
    # FAZA 10 permission engine binds confirmation to (tool_name, payload_hash),
    # so the confirmation payload must match the submitted arguments exactly.
    delete_arguments = {"id": record_id, "confirmed": True}
    confirmation = client.post(
        "/confirmations",
        json={
            "action_name": "records_delete",
            "payload": delete_arguments,
            "risk_level": "critical",
            "tool_name": "records_delete",
        },
    )
    assert confirmation.status_code == 200
    confirmation_id = confirmation.json()["id"]

    client.post(f"/confirmations/{confirmation_id}/approve")

    with_confirm = client.post(
        "/tools/execute",
        json={
            "tool_name": "records_delete",
            "arguments": {"id": record_id, "confirmed": True},
            "context": {"confirmation_id": confirmation_id, "computer_mode": False},
        },
    )
    assert with_confirm.status_code == 200
    assert with_confirm.json()["ok"] is True
    assert with_confirm.json()["result"]["deleted"] is True


def test_artifact_create_emits_event(client: TestClient) -> None:
    create = client.post(
        "/tools/execute",
        json={
            "tool_name": "artifact_create",
            "arguments": {"title": "Demo", "kind": "markdown", "content": "# Hello"},
        },
    )
    assert create.status_code == 200
    artifact_id = create.json()["result"]["artifact_id"]

    # Event bridge: artifact.created event should be in /events stream.
    events = client.get("/events").json()["events"]
    types = [event["type"] for event in events]
    assert "artifact.created" in types
    assert "backend.ready" in types

    fetched = client.post(
        "/tools/execute",
        json={"tool_name": "artifact_get", "arguments": {"id": artifact_id}},
    )
    assert fetched.status_code == 200
    assert fetched.json()["result"]["artifact"]["title"] == "Demo"


def test_artifact_list_returns_recent(client: TestClient) -> None:
    for index in range(3):
        client.post(
            "/tools/execute",
            json={
                "tool_name": "artifact_create",
                "arguments": {"title": f"Art {index}", "kind": "text", "content": str(index)},
            },
        )
    response = client.post(
        "/tools/execute",
        json={"tool_name": "artifact_list", "arguments": {"limit": 10}},
    )
    assert response.status_code == 200
    artifacts = response.json()["result"]["artifacts"]
    assert len(artifacts) == 3


def test_screen_snapshot_requires_computer_mode(client: TestClient) -> None:
    # Without computer_mode, the FAZA 10 permission engine should reject
    # screen_snapshot (requires_computer_mode=True) before any Pillow code runs.
    response = client.post(
        "/tools/execute",
        json={"tool_name": "screen_snapshot", "arguments": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    # Permission engine returns COMPUTER_MODE_REQUIRED (FAZA 10).
    assert body["error"]["code"] == "COMPUTER_MODE_REQUIRED"


def test_ui_inspect_requires_computer_mode(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "ui_inspect", "arguments": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "COMPUTER_MODE_REQUIRED"


def test_tools_list_includes_phase11_tools(client: TestClient) -> None:
    response = client.get("/tools")
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    expected = {
        "echo",
        "note_add",
        "note_search",
        "note_list",
        "records_create",
        "records_search",
        "records_update",
        "records_delete",
        "artifact_create",
        "artifact_get",
        "artifact_list",
        "artifact_show",
        "screen_snapshot",
        "ui_inspect",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_events_endpoint_returns_cursor(client: TestClient) -> None:
    # Trigger an event by creating an artifact.
    client.post(
        "/tools/execute",
        json={"tool_name": "artifact_create", "arguments": {"title": "X", "kind": "text", "content": "x"}},
    )
    response = client.get("/events")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert "next_cursor" in body
    # backend.ready is emitted at app startup.
    types = [event["type"] for event in body["events"]]
    assert "backend.ready" in types
