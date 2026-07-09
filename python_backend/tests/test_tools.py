from fastapi.testclient import TestClient

from app.main import app


def test_tools_lists_echo_tool() -> None:
    client = TestClient(app)
    response = client.get("/tools")

    assert response.status_code == 200
    body = response.json()
    assert body["tools"][0]["name"] == "echo"
    assert body["tools"][0]["risk"] == "low"
    assert body["tools"][0]["implemented_by"] == "python"


def test_execute_echo_tool() -> None:
    client = TestClient(app)
    response = client.post(
        "/tools/execute",
        json={
            "tool_name": "echo",
            "arguments": {"text": "hello"},
            "context": {"computer_mode": False},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tool_name"] == "echo"
    assert body["result"] == {"text": "hello"}
    assert body["artifact_ids"] == []
    assert body["event_ids"] == []
    assert body["action_log_id"]


def test_execute_unknown_tool_returns_contract_error() -> None:
    client = TestClient(app)
    response = client.post(
        "/tools/execute",
        json={
            "tool_name": "missing",
            "arguments": {},
            "context": {"computer_mode": False},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["tool_name"] == "missing"
    assert body["error"]["code"] == "TOOL_NOT_FOUND"
    assert body["action_log_id"]


def test_cancel_all_executions_returns_ok_with_no_in_flight_tools() -> None:
    # `with` runs the lifespan so app.state.cancellation_registry is initialized.
    with TestClient(app) as client:
        response = client.post("/tools/executions/cancel-all")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["count"] == 0
    assert body["cancelled"] == []
