from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def test_create_realtime_session_returns_client_secret() -> None:
    app.state.settings.openai_api_key = "sk-test-key"
    client = TestClient(app)

    with patch(
        "app.api.realtime.httpx.post",
        return_value=_FakeResponse(200, {"value": "ek-123", "expires_at": 1234567890}),
    ) as mocked_post:
        response = client.post("/realtime/session", json={"session": {"model": "gpt-realtime-2"}})

    assert response.status_code == 200
    body = response.json()
    assert body == {"value": "ek-123", "expiresAt": 1234567890}

    _, kwargs = mocked_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer sk-test-key"
    assert kwargs["json"] == {"session": {"model": "gpt-realtime-2"}}


def test_create_realtime_session_without_api_key_returns_500() -> None:
    app.state.settings.openai_api_key = None
    client = TestClient(app)

    response = client.post("/realtime/session", json={"session": {}})

    assert response.status_code == 500
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "MISSING_API_KEY"


def test_create_realtime_session_propagates_upstream_failure() -> None:
    app.state.settings.openai_api_key = "sk-test-key"
    client = TestClient(app)

    with patch(
        "app.api.realtime.httpx.post",
        return_value=_FakeResponse(401, {"error": "invalid key"}),
    ):
        response = client.post("/realtime/session", json={"session": {}})

    assert response.status_code == 502
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "REALTIME_REQUEST_FAILED"
