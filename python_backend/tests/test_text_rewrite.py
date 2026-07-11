from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agent.model_client import ModelResponse
from app.main import create_app


class ScriptedModelClient:
    """Fake ModelClient — same pattern as test_agent_runtime.py's
    ScriptedModelClient. Never makes a real network/API call."""

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
    return TestClient(app)


def _install_fake_model(client: TestClient, responses: list[ModelResponse]) -> ScriptedModelClient:
    fake = ScriptedModelClient(responses)
    client.app.state.text_model_client = fake
    return fake


def test_rewrite_returns_model_output(client: TestClient) -> None:
    fake = _install_fake_model(client, [ModelResponse(content="Poštovani, molim Vas...")])

    response = client.post("/text/rewrite", json={"text": "ej sta ima", "operation": "formalize"})

    assert response.status_code == 200
    assert response.json() == {"text": "Poštovani, molim Vas..."}
    assert fake.calls[0]["messages"][-1] == {"role": "user", "content": "ej sta ima"}
    assert fake.calls[0]["tools"] == []


def test_rewrite_empty_text_rejected(client: TestClient) -> None:
    _install_fake_model(client, [])

    response = client.post("/text/rewrite", json={"text": "   ", "operation": "shorten"})

    assert response.status_code == 400


def test_rewrite_falls_back_to_original_on_empty_model_reply(client: TestClient) -> None:
    _install_fake_model(client, [ModelResponse(content=None)])

    response = client.post("/text/rewrite", json={"text": "originalni tekst", "operation": "proofread"})

    assert response.status_code == 200
    assert response.json() == {"text": "originalni tekst"}


@pytest.mark.parametrize("operation", ["formalize", "shorten", "proofread", "translate_en"])
def test_all_operations_are_accepted(client: TestClient, operation: str) -> None:
    _install_fake_model(client, [ModelResponse(content="rezultat")])

    response = client.post("/text/rewrite", json={"text": "tekst", "operation": operation})

    assert response.status_code == 200
    assert response.json() == {"text": "rezultat"}
