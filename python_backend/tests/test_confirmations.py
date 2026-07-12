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


def test_create_confirmation_returns_pending(client: TestClient) -> None:
    response = client.post(
        "/confirmations",
        json={
            "action_name": "computer_type_text",
            "payload": {"text": "Hello"},
            "risk_level": "high",
            "summary": "Type greeting into active window",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["action_name"] == "computer_type_text"
    assert body["risk_level"] == "high"
    assert body["payload"] == {"text": "Hello"}
    assert body["resolved_at"] is None
    assert body["id"].startswith("confirm_")


def test_approve_confirmation_transitions_status(client: TestClient) -> None:
    create = client.post(
        "/confirmations",
        json={"action_name": "open_app", "payload": {"app": "calc.exe"}, "risk_level": "medium"},
    )
    confirmation_id = create.json()["id"]

    response = client.post(f"/confirmations/{confirmation_id}/approve")
    assert response.status_code == 200
    body = response.json()["confirmation"]
    assert body["status"] == "approved"
    assert body["resolved_at"] is not None


def test_reject_confirmation_transitions_status(client: TestClient) -> None:
    create = client.post(
        "/confirmations",
        json={"action_name": "delete_file", "payload": {"path": "/tmp/x"}, "risk_level": "critical"},
    )
    confirmation_id = create.json()["id"]

    response = client.post(f"/confirmations/{confirmation_id}/reject")
    assert response.status_code == 200
    assert response.json()["confirmation"]["status"] == "rejected"


def test_approve_unknown_confirmation_returns_404(client: TestClient) -> None:
    response = client.post("/confirmations/confirm_does_not_exist/approve")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONFIRMATION_NOT_FOUND"


def test_list_pending_confirmations(client: TestClient) -> None:
    for index in range(3):
        client.post(
            "/confirmations",
            json={"action_name": f"action_{index}", "payload": {}, "risk_level": "low"},
        )
    response = client.get("/confirmations/pending")
    assert response.status_code == 200
    items = response.json()["confirmations"]
    assert len(items) == 3
    assert all(item["status"] == "pending" for item in items)


def test_resolved_confirmation_leaves_pending_list(client: TestClient) -> None:
    create = client.post(
        "/confirmations",
        json={"action_name": "open_app", "payload": {}, "risk_level": "medium"},
    )
    confirmation_id = create.json()["id"]
    client.post(f"/confirmations/{confirmation_id}/approve")

    pending = client.get("/confirmations/pending").json()["confirmations"]
    assert all(item["id"] != confirmation_id for item in pending)


def test_double_approve_is_idempotent(client: TestClient) -> None:
    create = client.post(
        "/confirmations",
        json={"action_name": "open_app", "payload": {}, "risk_level": "medium"},
    )
    confirmation_id = create.json()["id"]
    first = client.post(f"/confirmations/{confirmation_id}/approve").json()["confirmation"]
    second = client.post(f"/confirmations/{confirmation_id}/approve").json()["confirmation"]
    assert first["status"] == "approved"
    assert second["status"] == "approved"


def test_confirmation_can_reference_plan(client: TestClient) -> None:
    plan = client.post("/plans", json={"title": "Demo", "steps": [{"title": "Step 1"}]}).json()
    response = client.post(
        "/confirmations",
        json={
            "action_name": "run_plan",
            "payload": {},
            "risk_level": "medium",
            "plan_id": plan["id"],
            "summary": "Approve plan execution",
        },
    )
    assert response.status_code == 200
    assert response.json()["plan_id"] == plan["id"]
