"""Testovi za companion orb (QM-2/QM-3): widget, voice-state bus, menu labels."""

from desktop.ui.orb import ORB_SIZE, STANJA, RickyOrbWidget
from desktop.ui.orb_window import (
    DEFAULT_MENU_LABELS,
    menu_labels_for,
)
from desktop.ui.voice_bus import VoiceStateBus
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


# --- voice-state bus ---

def test_voice_bus_emits_only_on_change():
    bus = VoiceStateBus()
    seen = []
    bus.state_changed.connect(seen.append)

    bus.set_state("idle")  # isto kao initial → ne emituje
    assert seen == []

    bus.set_state("listening")
    bus.set_state("listening")  # duplikat → ne emituje
    assert seen == ["listening"]

    bus.set_state("speaking")
    assert seen == ["listening", "speaking"]


def test_orb_window_subscribes_to_bus(qapp):
    from desktop.ui.orb_window import OrbWindow

    bus = VoiceStateBus()
    orb_window = OrbWindow(voice_bus=bus)

    bus.set_state("speaking")
    assert orb_window.widget.stanje == "speaking"

    bus.set_state("muted")
    assert orb_window.widget.stanje == "muted"


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
