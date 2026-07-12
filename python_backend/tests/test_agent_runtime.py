from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.model_client import ModelResponse, ModelToolCall
from app.core.auth import require_local_token
from app.main import create_app


class ScriptedModelClient:
    """Fake ModelClient (FAZA 15) — returns a scripted sequence of responses,
    one per call to `complete()`. Never makes a real network/API call, so
    tests never spend the user's OpenAI budget (project rule).
    """

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelResponse:
        self.calls.append({"messages": messages, "tools": tools})
        return self._responses.pop(0)


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def _install_fake_model(client: TestClient, responses: list[ModelResponse]) -> ScriptedModelClient:
    fake = ScriptedModelClient(responses)
    client.app.state.agent_runtime._model_client = fake
    return fake


def test_agent_message_plain_reply(client: TestClient) -> None:
    _install_fake_model(client, [ModelResponse(content="Hello there!")])

    response = client.post("/agent/message", json={"message": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Hello there!"
    assert body["tool_calls"] == []
    assert body["conversation_id"].startswith("conv_")


def test_agent_conversation_persists_and_is_fetchable(client: TestClient) -> None:
    _install_fake_model(client, [ModelResponse(content="Hi!")])
    sent = client.post("/agent/message", json={"message": "hello"})
    conversation_id = sent.json()["conversation_id"]

    fetched = client.get(f"/agent/conversations/{conversation_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == conversation_id
    roles = [message["role"] for message in body["messages"]]
    assert roles == ["user", "assistant"]


def test_agent_unknown_conversation_returns_404(client: TestClient) -> None:
    response = client.get("/agent/conversations/conv_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"


def test_agent_executes_low_risk_tool_via_permission_layer(client: TestClient) -> None:
    """echo is low risk / no confirmation — the runtime should call it through
    the same ToolExecutor/permission engine as POST /tools/execute and then
    ask the model for a final reply once the tool result is in history.
    """
    _install_fake_model(
        client,
        [
            ModelResponse(
                content=None,
                tool_calls=[ModelToolCall(id="call_1", tool_name="echo", arguments={"text": "ping"})],
            ),
            ModelResponse(content="The tool said ping."),
        ],
    )

    response = client.post("/agent/message", json={"message": "echo ping please"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "The tool said ping."
    assert len(body["tool_calls"]) == 1
    executed = body["tool_calls"][0]
    assert executed["tool_name"] == "echo"
    assert executed["ok"] is True
    assert executed["tool_state"] == "completed"


def test_agent_cannot_bypass_permission_layer_for_critical_tool(client: TestClient) -> None:
    """Acceptance criterion (MIGRATION_PLAN.md FAZA 15): the agent runtime
    cannot bypass the FAZA 10 permission layer. records_delete is critical
    risk and requires an approved confirmation_id bound to the exact
    tool/payload — the runtime never has one to hand it, so the tool call
    must come back rejected with CONFIRMATION_REQUIRED, exactly like a direct
    POST /tools/execute call without a confirmation_id would.
    """
    _install_fake_model(
        client,
        [
            ModelResponse(
                content=None,
                tool_calls=[
                    ModelToolCall(
                        id="call_1",
                        tool_name="records_delete",
                        arguments={"id": "rec_does_not_exist", "confirmed": True},
                    )
                ],
            ),
            ModelResponse(content="I could not delete that record without your confirmation."),
        ],
    )

    response = client.post("/agent/message", json={"message": "delete that record"})
    assert response.status_code == 200
    body = response.json()
    executed = body["tool_calls"][0]
    assert executed["tool_name"] == "records_delete"
    assert executed["ok"] is False
    assert executed["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_agent_tool_requiring_computer_mode_is_blocked_without_it(client: TestClient) -> None:
    _install_fake_model(
        client,
        [
            ModelResponse(
                content=None,
                tool_calls=[ModelToolCall(id="call_1", tool_name="screen_snapshot", arguments={})],
            ),
            ModelResponse(content="I need Computer Mode enabled to take a screenshot."),
        ],
    )

    response = client.post("/agent/message", json={"message": "take a screenshot"})
    assert response.status_code == 200
    executed = response.json()["tool_calls"][0]
    assert executed["ok"] is False
    assert executed["error"]["code"] == "COMPUTER_MODE_REQUIRED"
