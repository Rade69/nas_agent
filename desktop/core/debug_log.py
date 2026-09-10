"""Python debug log -> data/debug.log (parity sa Electron debugLog)."""

from __future__ import annotations

import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LOG_PATH = _REPO_ROOT / "data" / "debug.log"


def debugLog(*parts: object) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {' '.join(str(p) for p in parts)}\n"
        with _LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass
