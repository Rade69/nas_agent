"""Testovi za companion orb (QM-2): widget, provider fail-close, menu labels."""

import httpx

from desktop.ui.orb import ORB_SIZE, STANJA, RickyOrbWidget
from desktop.ui.orb_window import (
    DEFAULT_MENU_LABELS,
    HttpVoiceStateProvider,
    menu_labels_for,
)
from desktop.ui.voice_state import ORB_STATES


# --- orb widget (pytest-qt qapp fixture upravlja QApplication lifecycle-om) ---

def test_orb_states_cover_all_visual_states():
    assert set(STANJA.keys()) == set(ORB_STATES)


def test_orb_widget_creates_and_maps_voice_state(qapp):
    orb = RickyOrbWidget()
    assert orb.width() == 144
    assert orb.height() == 160
    assert orb.stanje == "idle"

    orb.postavi_voice_state("speaking")
    assert orb.stanje == "speaking"

    orb.postavi_voice_state("transcribing")
    assert orb.stanje == "listening"

    orb.postavi_voice_state("garbage")
    assert orb.stanje == "idle"


def test_orb_minimize_toggles_size(qapp):
    orb = RickyOrbWidget()
    orb.toggle_minimize()
    assert orb.minimizirano is True
    assert orb.width() == 28
    orb.toggle_minimize()
    assert orb.minimizirano is False
    assert orb.width() == 144


# --- provider fail-close ---

class _FakeResponse:
    def __init__(self, status_code: int, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, status_code: int = 200, body=None, exc: Exception | None = None):
        self.status_code = status_code
        self.body = body
        self.exc = exc

    def request(self, path, timeout=5.0):
        if self.exc is not None:
            raise self.exc
        return _FakeResponse(self.status_code, self.body)


def test_provider_returns_valid_state():
    p = HttpVoiceStateProvider(_FakeClient(200, {"state": "speaking"}))
    assert p.fetch_state() == "speaking"


def test_provider_fail_closed_on_404():
    p = HttpVoiceStateProvider(_FakeClient(404, {}))
    assert p.fetch_state() == "idle"


def test_provider_fail_closed_on_invalid_state():
    p = HttpVoiceStateProvider(_FakeClient(200, {"state": "garbage"}))
    assert p.fetch_state() == "idle"


def test_provider_fail_closed_on_network_error():
    p = HttpVoiceStateProvider(_FakeClient(exc=httpx.ConnectError("boom")))
    assert p.fetch_state() == "idle"


# --- menu labels ---

def test_menu_labels_fail_open_to_sr_latn():
    assert menu_labels_for(None) is DEFAULT_MENU_LABELS
    assert menu_labels_for("xx") is DEFAULT_MENU_LABELS
    assert menu_labels_for("") is DEFAULT_MENU_LABELS


def test_menu_labels_cover_all_keys():
    assert set(DEFAULT_MENU_LABELS) >= {
        "orbOpen",
        "orbToggleVoice",
        "orbLockPosition",
        "orbQuit",
        "trayShow",
        "trayHide",
    }


def test_menu_labels_english():
    labels = menu_labels_for("en")
    assert labels["orbQuit"] == "Close Ricky"
    assert labels["orbToggleVoice"] == "Toggle voice"
