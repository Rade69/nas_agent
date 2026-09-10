"""desktop/ui/voice_bus.py — VoiceStateBus (OA-2 centralni signal contract).

Centralni izvor istine za glasovno stanje i audio nivo u Qt procesu. Glasovna
sesija (desktop/voice/worker.py) se povezuje na ovaj bus; orb i glavni prozor
se pretplaćuju kroz Qt signale — NEMA HTTP polling-a. `state_changed` se
emituje samo kad se stanje stvarno promijeni; audio level se emituje ~10–30×/s.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from desktop.ui.voice_state import VoiceState


class VoiceStateBus(QObject):
    state_changed = Signal(str)          # VoiceState vrijednost
    audio_input_level = Signal(float)    # 0..1 (mikrofon)
    audio_output_level = Signal(float)   # 0..1 (agentov govor)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    connected_changed = Signal(bool)
    error = Signal(str)

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

    def set_audio_input_level(self, level: float) -> None:
        self.audio_input_level.emit(level)

    def set_audio_output_level(self, level: float) -> None:
        self.audio_output_level.emit(level)

    def set_user_transcript(self, text: str) -> None:
        self.user_transcript.emit(text)

    def set_assistant_transcript(self, text: str) -> None:
        self.assistant_transcript.emit(text)

    def set_connected(self, connected: bool) -> None:
        self.connected_changed.emit(connected)

    def set_error(self, message: str) -> None:
        self.error.emit(message)
