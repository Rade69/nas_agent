"""set_mode tool handler — permission-gate-only, no window side effect.

Computer Mode itself is Electron BrowserWindow state (show/hide/resize),
which this backend cannot reach. This handler exists purely so
permission_engine's S-2 escalation rule (agent_reports/2026-07-13_
computer-mode-voice-reentry.md) can gate a model-initiated set_mode call —
electron/main.cjs calls this first and only performs the actual window
switch once it returns ok (or is exempt via a Python confirmation).

Risk: medium (see tool_catalog/phase11.py registration) — a plain request
executes immediately; escalates to require confirmation only if the model
already read untrusted external content earlier this turn.
"""
from __future__ import annotations

from typing import Any


def make_handlers() -> dict[str, Any]:
    def set_mode(arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode") or "")
        if mode not in ("display", "computer"):
            raise ValueError("set_mode requires 'mode' to be 'display' or 'computer'.")
        return {"mode": mode}

    return {"set_mode": set_mode}
