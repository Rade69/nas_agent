"""Omogućava `python -m desktop` — dev spawn put za QM-1 process bridge.

Proces se pokreće kao `python -m desktop --backend` da bi ušao u backend granu
desktop/main.py (frozen build koristi isti exe sa `--backend` bez `-m desktop`).
"""

from desktop.main import main

if __name__ == "__main__":
    raise SystemExit(main())
