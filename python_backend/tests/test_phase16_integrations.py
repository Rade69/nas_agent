from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    # FAZA 16: force keys to empty so tests never hit real Exa/OpenAI APIs.
    # get_settings() calls load_dotenv(.env.local) as a fallback, so we must
    # override AFTER that — setting the env var to an empty string makes
    # `os.environ.get(...) or None` resolve to None (empty string is falsy).
    monkeypatch.setenv("EXA_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def test_tools_list_includes_web_search_and_image_generate(client: TestClient) -> None:
    response = client.get("/tools")
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "web_search" in names
    assert "image_generate" in names


def test_web_search_tool_definition_carries_low_risk(client: TestClient) -> None:
    response = client.get("/tools")
    tools = {tool["name"]: tool for tool in response.json()["tools"]}
    assert tools["web_search"]["risk"] == "low"
    assert tools["web_search"]["requires_confirmation"] is False
    assert tools["web_search"]["requires_computer_mode"] is False
    # FAZA 16: web search is a network call — longer timeout than local tools.
    assert tools["web_search"]["timeout_ms"] >= 30000
    # S-2 gap fix (2026-07-12): low risk + no computer_mode means this tool
    # would never have been escalated by the older S-2 check without
    # outbound=True — see test_permission_engine.py's
    # test_external_content_escalates_outbound_reader_tool.
    assert tools["web_search"]["outbound"] is True


def test_image_generate_tool_definition_carries_low_risk(client: TestClient) -> None:
    response = client.get("/tools")
    tools = {tool["name"]: tool for tool in response.json()["tools"]}
    assert tools["image_generate"]["risk"] == "low"
    assert tools["image_generate"]["requires_confirmation"] is False
    # Image generation can take a while — timeout should reflect that.
    assert tools["image_generate"]["timeout_ms"] >= 60000
    # S-2 gap fix (2026-07-12) — see test_web_search_tool_definition_carries_low_risk.
    assert tools["image_generate"]["outbound"] is True


def test_web_search_without_api_key_returns_structured_error(client: TestClient) -> None:
    # No EXA_API_KEY configured in the fixture — the tool surfaces MISSING_API_KEY
    # as an AppError, which the FastAPI error handler returns as a structured
    # 500 (server misconfiguration, not a tool execution failure).
    response = client.post(
        "/tools/execute",
        json={"tool_name": "web_search", "arguments": {"query": "test query"}},
    )
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "MISSING_API_KEY"


def test_image_generate_without_api_key_returns_structured_error(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "image_generate", "arguments": {"prompt": "a cat"}},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "MISSING_API_KEY"


def test_web_search_requires_query(client: TestClient) -> None:
    # Set a dummy key so the argument validation is what gets exercised
    # (not the MISSING_API_KEY check).
    import os

    os.environ["EXA_API_KEY"] = "dummy-key-for-arg-validation"
    try:
        response = client.post(
            "/tools/execute",
            json={"tool_name": "web_search", "arguments": {"query": ""}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "INVALID_ARGUMENTS"
    finally:
        os.environ["EXA_API_KEY"] = ""


def test_image_generate_requires_prompt(client: TestClient) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "dummy-key-for-arg-validation"
    try:
        response = client.post(
            "/tools/execute",
            json={"tool_name": "image_generate", "arguments": {"prompt": ""}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "INVALID_ARGUMENTS"
    finally:
        os.environ["OPENAI_API_KEY"] = ""
