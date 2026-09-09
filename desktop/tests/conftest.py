"""Osigurava da je repo root na sys.path za desktop testove.

Testovi se pokreću sa `python -m pytest desktop/tests` iz repo root-a; ovaj
conftest garantuje importabilnost `desktop` paketa nezavisno od toga kako je
pytest pokrenut.
"""

import os
import sys
from pathlib import Path

# Qt testovi (orb widget) moraju raditi headless — postavi prije nego što se
# ijedan QApplication kreira.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: spawnuje stvarni backend proces (sporo)"
    )
