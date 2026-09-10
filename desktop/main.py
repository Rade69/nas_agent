"""desktop/main.py — composition root Qt shell-a (QM-0/QM-1).

Entry point koji grana prema `--backend` flagu:
- bez flag-a → pokreće Qt UI (QM-0 skelet; puni UI dolazi u QM-4/QM-5);
- sa `--backend` → pokreće FastAPI backend (python_backend/) umjesto UI — ovako
  `desktop/core/process_bridge.py` (QM-1) spawn-uje backend kao zaseban proces,
  frozen-safe (isti exe re-invokovan sa flagom, vidi
  docs/QT_MIGRATION_PLAN_2026-07-20.md §QM-1).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow


def create_app(argv: list[str] | None = None) -> tuple[QApplication, QMainWindow]:
    """Kreira QApplication i prazan glavni prozor (ne ulazi u event loop)."""
    app = QApplication(argv if argv is not None else sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Ricky")
    window.resize(400, 300)
    window.show()
    return app, window


def run_qt(argv: list[str] | None = None) -> int:
    """Pokreće Qt shell: PySide6 + QWebEngineView (postojeći React GUI).

    CR-1/CR-2: backend + Python voice + React UI preko QWebChannel-a.
    """
    from PySide6.QtWidgets import QApplication

    from desktop.app_controller import AppController
    from desktop.web.main_view import MainWebWindow

    app = QApplication.instance() or QApplication(sys.argv)
    controller = AppController()
    window = MainWebWindow(controller)
    window.show()
    controller.start()
    return app.exec()


def run_orb(argv: list[str] | None = None) -> int:
    """Pokreće samo companion orb (dev/test ulaz za QM-2 vizuelnu provjeru).

    Orb se pretplaćuje na VoiceStateBus; bez glasa (voice.py) prikazuje idle.
    """
    from desktop.ui.orb_window import OrbWindow
    from desktop.ui.voice_bus import VoiceStateBus

    app = QApplication.instance() or QApplication(sys.argv)
    bus = VoiceStateBus()
    orb = OrbWindow(voice_bus=bus)
    orb.set_quit_callback(app.quit)
    orb.show()
    return app.exec()


def run_backend(argv: list[str] | None = None) -> int:
    """Pokreće FastAPI backend umjesto Qt UI (entry point sa `--backend`).

    Backend paket živi u sibling direktoriju `python_backend/` i importuje se
    kao top-level `app` paket (isti obrazac kao `python -m uvicorn app.main:app`).
    Host/port se čitaju iz env (RICKY_HOST/RICKY_PORT) koje process_bridge
    postavlja prije spawn-a — ovdje se ne parsira komandna linija.
    """
    backend_dir = Path(__file__).resolve().parents[1] / "python_backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Import nakon sys.path podešavanja. `app.main` na importu već kreira
    # FastAPI instancu (`app = create_app()` na module levelu), pa je dovoljno
    # importovati gotovu instancu i pokrenuti je — ne pozivati create_app() ponovo.
    from app.main import app as backend_app
    from app.core.config import get_settings

    settings = get_settings()
    import uvicorn

    uvicorn.run(backend_app, host=settings.host, port=settings.port)
    return 0


def _utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _flag_int(argv: list[str], flag: str) -> int | None:
    if flag in argv:
        try:
            return int(argv[argv.index(flag) + 1])
        except (IndexError, ValueError):
            return None
    return None


def run_devices(argv: list[str] | None = None) -> int:
    """Ispisuje audio uređaje (PC-1 dijagnostika — "koji mic koristi")."""
    _utf8_stdout()
    from desktop.voice.devices import AudioDeviceService

    svc = AudioDeviceService()
    print("=== INPUT (mikrofoni) ===")
    for d in svc.list_inputs():
        print(f"  [{d.index}] {d.name}  (default={d.default_samplerate:.0f}Hz)")
    print("=== OUTPUT (zvučnici) ===")
    for d in svc.list_outputs():
        print(f"  [{d.index}] {d.name}")
    di = svc.default_input()
    do = svc.default_output()
    print(f"Default input : [{di.index}] {di.name}" if di else "Default input : NONE")
    print(f"Default output: [{do.index}] {do.name}" if do else "Default output: NONE")
    return 0


def run_voice(argv: list[str] | None = None) -> int:
    """PC-1 live test: Python voice end-to-end (bez Electron-a), dijagnostika u terminal.

    Pokreće backend + RealtimeWorker i ispisuje "čuje li me?" lanac:
    session → mic stream → frame → VAD speech_started → transcript → response.
    """
    import threading

    from desktop.core.process_bridge import BackendProcess
    from desktop.voice.worker import RealtimeWorker
    from desktop.voice.session import VoiceCallbacks
    from desktop.ui.tool_bridge import ToolBridge
    from PySide6.QtCore import QCoreApplication

    _utf8_stdout()
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)

    bp = BackendProcess()
    print("[1/7] pokrećem backend...")
    bp.start()
    print(f"[2/7] backend OK ({bp.base_url})")

    bridge = ToolBridge(bp.client)

    cb = VoiceCallbacks()
    cb.on_connected = lambda b: print(f"[3/7] WebSocket {'connected' if b else 'disconnected'}")
    cb.on_input_stream_open = lambda name: print(f"[4/7] mic stream open: {name}")
    cb.on_input_warning = lambda m: print(f"  ⚠ mic warning: {m}")
    cb.on_audio_input_level = lambda lvl: None  # ne spamuj terminal
    cb.on_user_transcript = lambda t: print(f"[5/7] ti: {t}")
    cb.on_assistant_transcript = lambda t: print(f"[6/7] Ricky: {t}")
    cb.on_error = lambda e: print(f"  ✗ error: {e}")
    cb.on_reconnecting = lambda: print("  ⟳ reconnecting...")

    worker = RealtimeWorker(bp.client, bridge, input_device=_flag_int(argv, "--input"), output_device=_flag_int(argv, "--output"))
    worker.state_changed.connect(lambda s: print(f"  state={s}"))
    worker.user_transcript.connect(cb.on_user_transcript)
    worker.assistant_transcript.connect(cb.on_assistant_transcript)
    worker.connected_changed.connect(cb.on_connected)
    worker.input_stream_opened.connect(cb.on_input_stream_open)
    worker.input_warning.connect(cb.on_input_warning)
    worker.error_occurred.connect(cb.on_error)
    worker.reconnecting.connect(cb.on_reconnecting)

    print("[7/7] govori (Ctrl+C za kraj)...")
    worker.start()

    try:
        return app.exec()
    finally:
        worker.request_stop()
        worker.wait(3000)
        bp.stop()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--backend" in argv:
        return run_backend(argv)
    if "--devices" in argv:
        return run_devices(argv)
    if "--voice" in argv:
        return run_voice(argv)
    if "--orb" in argv:
        return run_orb(argv)
    return run_qt(argv)


if __name__ == "__main__":
    raise SystemExit(main())
