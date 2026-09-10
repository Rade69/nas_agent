"""desktop/app_controller.py — composition root (PC-2).

Povezuje Python backend proces, voice runtime, voice-state bus, tool bridge i
orb u jednu aplikaciju. Ovo je "mozak" desktop shell-a — ne sadrži UI widgete,
samo lifecycle i signali. Glavni prozor (ui/main_window.py) se povezuje na ove
signale.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from desktop.core.process_bridge import BackendProcess
from desktop.ui.tool_bridge import ToolBridge
from desktop.ui.voice_bus import VoiceStateBus


class AppController(QObject):
    status = Signal(str)
    backend_ready = Signal()
    backend_failed = Signal(str)
    confirmation_required = Signal(dict)  # {call_id, tool_name, arguments, risk, confirmation_id}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.backend = BackendProcess()
        self.bus = VoiceStateBus()
        self.tool_bridge: ToolBridge | None = None
        self.worker = None  # RealtimeWorker (kreira se lazy)

    def start(self) -> None:
        """Pokreće backend; fail-closed — ne prikazuje lažno spremnu app."""
        self.status.emit("Pokrećem backend...")
        try:
            self.backend.start()
        except Exception as exc:  # pragma: no cover - runtime
            self.backend_failed.emit(str(exc))
            return
        self.tool_bridge = ToolBridge(self.backend.client)
        self.backend_ready.emit()

    def start_voice(self, input_device: int | None = None, output_device: int | None = None) -> None:
        from desktop.voice.worker import RealtimeWorker

        if self.worker is not None and self.worker.isRunning():
            return
        if self.tool_bridge is None:
            return
        self.worker = RealtimeWorker(
            self.backend.client, self.tool_bridge,
            input_device=input_device, output_device=output_device,
        )
        # Poveži worker signale na bus (orb + UI čitaju bus).
        self.worker.state_changed.connect(self.bus.set_state)
        self.worker.audio_input_level.connect(self.bus.set_audio_input_level)
        self.worker.audio_output_level.connect(self.bus.set_audio_output_level)
        self.worker.user_transcript.connect(self.bus.set_user_transcript)
        self.worker.assistant_transcript.connect(self.bus.set_assistant_transcript)
        self.worker.connected_changed.connect(self.bus.set_connected)
        self.worker.error_occurred.connect(self.bus.set_error)
        self.worker.confirmation_required.connect(self.confirmation_required)
        self.worker.start()

    def approve_confirmation(self, call_id: str, confirmation_id: str) -> None:
        if self.worker is not None:
            self.worker.approve_confirmation(call_id, confirmation_id)

    def reject_confirmation(self, call_id: str) -> None:
        if self.worker is not None:
            self.worker.reject_confirmation(call_id)

    def stop_voice(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)

    def shutdown(self) -> None:
        self.stop_voice()
        self.backend.stop()
