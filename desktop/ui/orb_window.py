"""desktop/ui/orb_window.py — OrbWindow menadžer (QM-2).

OrbWindow drži RickyOrbWidget i dodaje prozor-nivo logiku koja nije čisto
vizuelna: kontekst meni (desni klik, lokalizovan), position lock, i voice-state
polling (1s) preko HttpVoiceStateProvider → GET /voice/state. MENU_LABELS je
vjeran port iz electron/core/companionWindow.cjs (5 jezika, fail-open na sr-Latn).
"""

from __future__ import annotations

import httpx
from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QMenu

from desktop.ui.orb import RickyOrbWidget
from desktop.ui.voice_state import VoiceState, is_valid_voice_state

# Port iz companionWindow.cjs MENU_LABELS (de/es/fr best-effort, ne
# native-speaker potvrđeno — isti disclaimer kao svaka druga locale u projektu).
MENU_LABELS: dict[str, dict[str, str]] = {
    "sr-Latn": {
        "trayShow": "Prikaži Ricky orb",
        "trayHide": "Sakrij Ricky orb",
        "orbOpen": "Otvori Ricky",
        "orbToggleVoice": "Uključi/isključi glas",
        "orbLockPosition": "Zaključaj poziciju",
        "orbQuit": "Zatvori Ricky",
    },
    "en": {
        "trayShow": "Show companion orb",
        "trayHide": "Hide companion orb",
        "orbOpen": "Open Ricky",
        "orbToggleVoice": "Toggle voice",
        "orbLockPosition": "Lock position",
        "orbQuit": "Close Ricky",
    },
    "de": {
        "trayShow": "Ricky-Orb anzeigen",
        "trayHide": "Ricky-Orb ausblenden",
        "orbOpen": "Ricky öffnen",
        "orbToggleVoice": "Sprache umschalten",
        "orbLockPosition": "Position sperren",
        "orbQuit": "Ricky schließen",
    },
    "es": {
        "trayShow": "Mostrar orbe de Ricky",
        "trayHide": "Ocultar orbe de Ricky",
        "orbOpen": "Abrir Ricky",
        "orbToggleVoice": "Alternar voz",
        "orbLockPosition": "Bloquear posición",
        "orbQuit": "Cerrar Ricky",
    },
    "fr": {
        "trayShow": "Afficher l'orbe Ricky",
        "trayHide": "Masquer l'orbe Ricky",
        "orbOpen": "Ouvrir Ricky",
        "orbToggleVoice": "Activer/désactiver la voix",
        "orbLockPosition": "Verrouiller la position",
        "orbQuit": "Fermer Ricky",
    },
}
DEFAULT_MENU_LABELS = MENU_LABELS["sr-Latn"]


def menu_labels_for(language: str | None) -> dict[str, str]:
    """Vrati labele za jezik, fail-open na sr-Latn. Nikad ne diže."""
    return MENU_LABELS.get(language or "", DEFAULT_MENU_LABELS)


class VoiceStateProvider(QObject):
    """Apstrakcija izvora VoiceState-a (QObject da se može živjeti u Qt niti)."""


class HttpVoiceStateProvider(VoiceStateProvider):
    """Poll-uje GET /voice/state preko BackendClient; fail-close na idle ako
    endpoint ne postoji (do QM-3) ili backend ne odgovara."""

    def __init__(self, client) -> None:
        super().__init__()
        self._client = client

    def fetch_state(self) -> str:
        try:
            resp = self._client.request("/voice/state", timeout=1.0)
            if resp.status_code == 200:
                state = resp.json().get("state")
                if state and is_valid_voice_state(state):
                    return state
        except (httpx.HTTPError, ValueError):
            pass
        return VoiceState.IDLE.value


class VoiceStatePoller(QObject):
    """QTimer-driven polling (1s) → emituje state_changed samo kad se promijeni."""

    state_changed = Signal(str)

    def __init__(self, provider: VoiceStateProvider, interval_ms: int = 1000) -> None:
        super().__init__()
        self._provider = provider
        self._interval_ms = interval_ms
        self._last: str | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._poll()  # odmah jednom, ne čekati prvi interval
        self._timer.start(self._interval_ms)

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self) -> None:
        state = self._provider.fetch_state()
        if state != self._last:
            self._last = state
            self.state_changed.emit(state)


class OrbWindow:
    """Menadžer companion orb prozora: widget + kontekst meni + polling + callback-ovi."""

    def __init__(self, client=None, language: str | None = None) -> None:
        self.widget = RickyOrbWidget()
        self.widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.widget.customContextMenuRequested.connect(self._show_context_menu)

        self._labels = menu_labels_for(language)
        self._open_main_cb = None
        self._toggle_voice_cb = None
        self._quit_cb = None

        self._poller: VoiceStatePoller | None = None
        if client is not None:
            self._poller = VoiceStatePoller(HttpVoiceStateProvider(client))
            self._poller.state_changed.connect(self.widget.postavi_voice_state)

    # Lazy-bound callback-ovi (isti obrazac kao companionWindow.cjs) — glavni
    # prozor (QM-4) i glas (QM-3) ih povezuju kasnije.
    def set_open_main_callback(self, cb) -> None:
        self._open_main_cb = cb

    def set_toggle_voice_callback(self, cb) -> None:
        self._toggle_voice_cb = cb

    def set_quit_callback(self, cb) -> None:
        self._quit_cb = cb

    def show(self) -> None:
        if self._poller is not None:
            self._poller.start()
        self.widget.show()

    def hide(self) -> None:
        if self._poller is not None:
            self._poller.stop()
        self.widget.hide()

    def _show_context_menu(self, pos: QPoint) -> None:
        labels = self._labels
        menu = QMenu(self.widget)

        menu.addAction(labels["orbOpen"], self._open_main)
        menu.addAction(labels["orbToggleVoice"], self._toggle_voice)
        menu.addSeparator()

        minimize_label = labels["trayHide"] if not self.widget.minimizirano else labels["trayShow"]
        menu.addAction(minimize_label, self.widget.toggle_minimize)

        lock_action = menu.addAction(labels["orbLockPosition"])
        lock_action.setCheckable(True)
        lock_action.setChecked(self.widget.is_locked())
        lock_action.toggled.connect(self.widget.set_locked)

        menu.addSeparator()
        menu.addAction(labels["orbQuit"], self._quit)
        menu.exec(self.widget.mapToGlobal(pos))

    def _open_main(self) -> None:
        if self._open_main_cb:
            self._open_main_cb()

    def _toggle_voice(self) -> None:
        if self._toggle_voice_cb:
            self._toggle_voice_cb()

    def _quit(self) -> None:
        if self._quit_cb:
            self._quit_cb()
