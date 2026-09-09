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
    """Pokreće Qt UI (glavni event loop)."""
    app, _window = create_app(argv)
    return app.exec()


def run_orb(argv: list[str] | None = None) -> int:
    """Pokreće samo companion orb (dev/test ulaz za QM-2 vizuelnu provjeru).

    Bez backend-a — orb prikazuje idle dok QM-3 ne ožiči stvarni VoiceState.
    """
    from desktop.ui.orb_window import OrbWindow

    app = QApplication.instance() or QApplication(sys.argv)
    orb = OrbWindow()
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--backend" in argv:
        return run_backend(argv)
    if "--orb" in argv:
        return run_orb(argv)
    return run_qt(argv)


if __name__ == "__main__":
    raise SystemExit(main())
