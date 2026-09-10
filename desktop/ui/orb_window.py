"""desktop/ui/orb_window.py — OrbWindow menadžer (QM-2, ažuriran QM-3).

OrbWindow drži RickyOrbWidget i dodaje prozor-nivo logiku: kontekst meni
(desni klik, lokalizovan), position lock, i pretplatu na VoiceStateBus (lokalni
signal iz voice.py — NEMA HTTP polling-a kroz backend za lokalno stanje).
MENU_LABELS je vjeran port iz electron/core/companionWindow.cjs.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu

from desktop.ui.orb import RickyOrbWidget
from desktop.ui.voice_bus import VoiceStateBus

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


class OrbWindow:
    """Menadžer companion orb prozora: widget + kontekst meni + voice-state bus."""

    def __init__(self, voice_bus: VoiceStateBus | None = None, language: str | None = None) -> None:
        self.widget = RickyOrbWidget()
        self.widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.widget.customContextMenuRequested.connect(self._show_context_menu)

        self._labels = menu_labels_for(language)
        self._open_main_cb = None
        self._toggle_voice_cb = None
        self._quit_cb = None

        if voice_bus is not None:
            voice_bus.state_changed.connect(self.widget.postavi_voice_state)
            voice_bus.audio_input_level.connect(self.widget.postavi_audio_nivo)

    # Lazy-bound callback-ovi (isti obrazac kao companionWindow.cjs) — glavni
    # prozor (QM-4) i glas (QM-3) ih povezuju kasnije.
    def set_open_main_callback(self, cb) -> None:
        self._open_main_cb = cb

    def set_toggle_voice_callback(self, cb) -> None:
        self._toggle_voice_cb = cb

    def set_quit_callback(self, cb) -> None:
        self._quit_cb = cb

    def show(self) -> None:
        self.widget.show()

    def hide(self) -> None:
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
