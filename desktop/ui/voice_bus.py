"""desktop/ui/voice_bus.py — VoiceStateBus (QM-3).

Centralni izvor istine za glasovno stanje u Qt procesu. Glasovna sesija
(voice.py) emituje VoiceState promjene ovdje; orb i glavni prozor se
pretplaćuju kroz Qt signal — nema HTTP roundtrip-a kroz backend za lokalnu
stvar. `state_changed` se emituje samo kad se stanje stvarno promijeni.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from desktop.ui.voice_state import VoiceState


class VoiceStateBus(QObject):
    state_changed = Signal(str)  # VoiceState vrijednost

    def __init__(self, initial: str = VoiceState.IDLE.value) -> None:
        super().__init__()
        self._state: str = initial

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)
