"""Testovi za desktop Realtime model (RTM-5): backend-owned model."""

from desktop.voice.session import RealtimeSession, VoiceCallbacks


class _FakeResp:
    def __init__(self, body: dict):
        self._body = body

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, body: dict):
        self._body = body
        self.calls = []

    def request(self, path, method="GET", json=None, timeout=5.0):
        self.calls.append((path, json))
        return _FakeResp(self._body)


def test_resolve_credential_returns_backend_model():
    client = _FakeClient({"value": "ek-1", "model": "gpt-realtime-2.1-mini"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    value, model = session._resolve_credential()
    assert value == "ek-1"
    assert model == "gpt-realtime-2.1-mini"


def test_resolve_credential_falls_back_to_default_model():
    client = _FakeClient({"value": "ek-2"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    value, model = session._resolve_credential()
    assert value == "ek-2"
    assert model == "gpt-realtime"


def test_resolve_credential_does_not_send_model_in_request():
    # Desktop NE šalje svoj model kao source of truth — backend odlučuje.
    client = _FakeClient({"value": "ek-3", "model": "gpt-realtime-2.1-mini"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    session._resolve_credential()
    _, sent_json = client.calls[0]
    assert sent_json == {"session": {"type": "realtime"}}
