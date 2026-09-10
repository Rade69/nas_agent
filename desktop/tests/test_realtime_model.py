"""Testovi za desktop Realtime model (RTM-5 + C-1/C-3): backend-owned, fail-closed."""

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
    client = _FakeClient({"value": "ek-1", "model": "gpt-realtime-2.1"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    value, model = session._resolve_credential()
    assert value == "ek-1"
    assert model == "gpt-realtime-2.1"


def test_resolve_credential_returns_default_backend_model():
    # backend eksplicitno vraća gpt-realtime — NIJE desktop fallback.
    client = _FakeClient({"value": "ek-4", "model": "gpt-realtime-2"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    value, model = session._resolve_credential()
    assert value == "ek-4"
    assert model == "gpt-realtime-2"


def test_resolve_credential_fails_if_backend_model_missing():
    # C-1/C-3: credential bez modela NIJE validan response — fail-closed.
    client = _FakeClient({"value": "ek-2"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    assert session._resolve_credential() is None


def test_resolve_credential_fails_if_credential_missing():
    client = _FakeClient({"model": "gpt-realtime-2"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    assert session._resolve_credential() is None


def test_resolve_credential_fails_if_both_missing():
    client = _FakeClient({})
    session = RealtimeSession(client, None, VoiceCallbacks())
    assert session._resolve_credential() is None


def test_resolve_credential_does_not_send_model_in_request():
    # Desktop NE šalje svoj model kao source of truth — backend odlučuje.
    client = _FakeClient({"value": "ek-3", "model": "gpt-realtime-2.1"})
    session = RealtimeSession(client, None, VoiceCallbacks())
    session._resolve_credential()
    _, sent_json = client.calls[0]
    assert sent_json == {"session": {"type": "realtime"}}
