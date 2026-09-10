"""Testovi za provider selection (MM-1/MM-3): factory, capabilities, MiniMax M3."""

from types import SimpleNamespace

import httpx

from app.agent.model_client import MiniMaxModelClient, OpenAIModelClient
from app.agent.providers import (
    AIProvider,
    MINIMAX_CAPABILITIES,
    OPENAI_CAPABILITIES,
    capabilities_for,
    create_model_client,
)
from app.core.errors import AppError


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text

    def json(self):
        return self._json


def _settings(**kw):
    base = dict(
        ai_provider="openai",
        openai_api_key="oa-key",
        openai_model="gpt-4o-mini",
        minimax_api_key="mm-key",
        minimax_model="MiniMax-M3",
    )
    base.update(kw)
    return SimpleNamespace(**base)


# --- factory ---

def test_factory_defaults_to_openai():
    client = create_model_client(_settings())
    assert isinstance(client, OpenAIModelClient)


def test_factory_returns_minimax():
    client = create_model_client(_settings(ai_provider="minimax"))
    assert isinstance(client, MiniMaxModelClient)


def test_factory_unknown_provider_falls_back_to_openai():
    client = create_model_client(_settings(ai_provider="bogus"))
    assert isinstance(client, OpenAIModelClient)


# --- capabilities ---

def test_capabilities_reflect_reality():
    assert capabilities_for(AIProvider.OPENAI).realtime_audio_input is True
    assert capabilities_for(AIProvider.MINIMAX).realtime_audio_input is False  # nema native realtime
    assert capabilities_for(AIProvider.MINIMAX).tool_calling is True
    assert capabilities_for(AIProvider.MINIMAX).streaming_audio is True
    assert OPENAI_CAPABILITIES.interruption is True
    assert MINIMAX_CAPABILITIES.interruption is False


# --- MiniMax M3 client ---

def test_minimax_complete_parses_tool_calls(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "radim",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "web_search",
                                        "arguments": '{"q": "vrijeme"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = MiniMaxModelClient("mm-key")
    resp = client.complete(messages=[{"role": "user", "content": "hi"}], tools=[{"type": "function"}])

    assert captured["url"] == "https://api.minimax.io/v1/chat/completions"
    assert captured["json"]["model"] == "MiniMax-M3"
    assert captured["json"]["thinking"] == {"type": "disabled"}
    assert resp.tool_calls[0].tool_name == "web_search"
    assert resp.tool_calls[0].arguments == {"q": "vrijeme"}


def test_minimax_missing_key_raises():
    client = MiniMaxModelClient(None)
    try:
        client.complete(messages=[], tools=[])
        assert False, "trebalo je da baci"
    except AppError as exc:
        assert exc.code == "MISSING_API_KEY"


def test_minimax_base_resp_error_surfaced(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            200,
            {"choices": [], "base_resp": {"status_code": 1004, "status_msg": "auth failed"}},
        ),
    )
    client = MiniMaxModelClient("mm-key")
    try:
        client.complete(messages=[], tools=[])
        assert False, "trebalo je da baci"
    except AppError as exc:
        assert "1004" in exc.message
