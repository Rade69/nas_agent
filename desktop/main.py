"""desktop/main.py — composition root Qt shell-a (QM-0 skeleton).

Minimalan PySide6 entry point koji dokazuje da se desktop/ skelet pokreće:
otvara prazan prozor. Puni layout, navigacija i ožičenje na backend dolaze
u QM-4/QM-5 (vidi docs/QT_MIGRATION_PLAN_2026-07-20.md).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow


def create_app(argv: list[str] | None = None) -> tuple[QApplication, QMainWindow]:
    """Kreira QApplication i prazan glavni prozor (ne ulazi u event loop)."""
    app = QApplication(argv if argv is not None else sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Ricky")
    window.resize(400, 300)
    window.show()
    return app, window


def main() -> int:
    app, _window = create_app()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
