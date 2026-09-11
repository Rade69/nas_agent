"""desktop/voice/worker.py — RealtimeWorker (OA-1).

QThread koji pokreće glasovnu sesiju (RealtimeSession) u sopstvenom asyncio
loop-u. Komunikacija: session → worker preko VoiceCallbacks → Qt signali
(QueuedConnection, thread-safe); UI → worker preko thread-safe metoda
(request_stop/approve_confirmation/reject_confirmation) koje stavljaju u
session inbox. Worker NE sadrži business security logiku.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal

from desktop.voice.session import RealtimeSession, VoiceCallbacks


class RealtimeWorker(QThread):
    state_changed = Signal(str)
    audio_input_level = Signal(float)
    audio_output_level = Signal(float)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    confirmation_required = Signal(dict)
    error_occurred = Signal(str)
    connected_changed = Signal(bool)
    reconnecting = Signal()
    # PC-1 mic health.
    input_stream_opened = Signal(str)
    input_warning = Signal(str)

    def __init__(self, backend_client, tool_bridge, model: str = "gpt-realtime-2.1-mini", parent=None,
                 input_device: int | None = None, output_device: int | None = None) -> None:
        super().__init__(parent)
        self._client = backend_client
        self._tool_bridge = tool_bridge
        self._model = model
        self._input_device = input_device
        self._output_device = output_device
        self._session: RealtimeSession | None = None

    def run(self) -> None:  # noqa: D401
        callbacks = VoiceCallbacks()
        callbacks.on_state = self.state_changed.emit
        callbacks.on_audio_input_level = self.audio_input_level.emit
        callbacks.on_audio_output_level = self.audio_output_level.emit
        callbacks.on_user_transcript = self.user_transcript.emit
        callbacks.on_assistant_transcript = self.assistant_transcript.emit
        callbacks.on_confirmation_required = self.confirmation_required.emit
        callbacks.on_error = self.error_occurred.emit
        callbacks.on_connected = self.connected_changed.emit
        callbacks.on_reconnecting = self.reconnecting.emit
        callbacks.on_input_stream_open = self.input_stream_opened.emit
        callbacks.on_input_warning = self.input_warning.emit

        self._session = RealtimeSession(
            self._client, self._tool_bridge, callbacks, self._model,
            input_device=self._input_device, output_device=self._output_device,
        )
        try:
            asyncio.run(self._session.run())
        except Exception as exc:  # pragma: no cover - runtime audio/network
            self.error_occurred.emit(f"{type(exc).__name__}: {exc}")

    # ── UI → worker (thread-safe) ─────────────────────────────────────────────

    def request_stop(self) -> None:
        if self._session is not None:
            self._session.request_stop()

    def approve_confirmation(self, call_id: str, confirmation_id: str) -> None:
        if self._session is not None:
            self._session.approve_confirmation(call_id, confirmation_id)

    def approve_confirmation_by_id(self, confirmation_id: str) -> None:
        if self._session is not None:
            self._session.approve_by_confirmation_id(confirmation_id)

    def reject_confirmation_by_id(self, confirmation_id: str) -> None:
        if self._session is not None:
            self._session.reject_by_confirmation_id(confirmation_id)

    def reject_confirmation(self, call_id: str) -> None:
        if self._session is not None:
            self._session.reject_confirmation(call_id)
