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


def test_create_plan_with_steps(client: TestClient) -> None:
    response = client.post(
        "/plans",
        json={
            "title": "Open app and type",
            "summary": "Open Notepad and type a greeting",
            "steps": [
                {"title": "Open Notepad", "details": {"app": "notepad.exe"}},
                {"title": "Type greeting", "details": {"text": "Hello"}},
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("plan_")
    assert body["status"] == "proposed"
    assert len(body["steps"]) == 2
    assert body["steps"][0]["step_index"] == 0
    assert body["steps"][0]["status"] == "pending"
    assert body["steps"][1]["title"] == "Type greeting"


def test_list_plans(client: TestClient) -> None:
    client.post("/plans", json={"title": "Plan A", "steps": [{"title": "A1"}]})
    client.post("/plans", json={"title": "Plan B", "steps": [{"title": "B1"}]})

    response = client.get("/plans")
    assert response.status_code == 200
    titles = [plan["title"] for plan in response.json()["plans"]]
    assert "Plan A" in titles
    assert "Plan B" in titles


def test_get_plan_returns_steps(client: TestClient) -> None:
    create = client.post(
        "/plans",
        json={"title": "Demo", "steps": [{"title": "Step 1"}, {"title": "Step 2"}]},
    )
    plan_id = create.json()["id"]

    response = client.get(f"/plans/{plan_id}")
    assert response.status_code == 200
    assert len(response.json()["steps"]) == 2


def test_update_plan_status(client: TestClient) -> None:
    create = client.post("/plans", json={"title": "Demo", "steps": [{"title": "Step 1"}]})
    plan_id = create.json()["id"]

    response = client.patch(f"/plans/{plan_id}", json={"status": "approved"})
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_update_plan_step_status(client: TestClient) -> None:
    create = client.post(
        "/plans",
        json={"title": "Demo", "steps": [{"title": "Step 1"}, {"title": "Step 2"}]},
    )
    plan_id = create.json()["id"]
    step_id = create.json()["steps"][0]["id"]

    response = client.patch(
        f"/plans/{plan_id}/steps/{step_id}",
        json={"status": "completed"},
    )
    assert response.status_code == 200
    steps = response.json()["steps"]
    assert next(s for s in steps if s["id"] == step_id)["status"] == "completed"


def test_get_unknown_plan_returns_404(client: TestClient) -> None:
    response = client.get("/plans/plan_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PLAN_NOT_FOUND"


def test_update_unknown_step_returns_404(client: TestClient) -> None:
    create = client.post("/plans", json={"title": "Demo", "steps": [{"title": "Step 1"}]})
    plan_id = create.json()["id"]

    response = client.patch(
        f"/plans/{plan_id}/steps/step_does_not_exist",
        json={"status": "completed"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PLAN_STEP_NOT_FOUND"
