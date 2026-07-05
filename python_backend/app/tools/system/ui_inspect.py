"""Windows ui_inspect tool handler (FAZA 11).

Returns the foreground window title and owning process without any extra
dependency (uses stdlib `ctypes` for Win32 calls + `psutil` for process info).
The legacy PowerShell `uiInspect.cjs` remains as an Electron-side fallback.

Risk: low (read-only inspection — see SECURITY_MODEL.md). Requires
computer_mode.
"""
from __future__ import annotations

import sys
from typing import Any


def make_handlers() -> dict[str, Any]:
    def ui_inspect(arguments: dict[str, Any]) -> dict[str, Any]:
        if sys.platform != "win32":
            raise RuntimeError("ui_inspect is only supported on Windows.")

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.GetForegroundWindow()

        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title_buf, 256)

        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))

        process_name = "Unknown"
        try:
            import psutil

            proc = psutil.Process(proc_id.value)
            process_name = proc.name()
        except Exception:
            pass

        summary = f"App: {process_name}\nWindow: {title_buf.value}"
        return {
            "active_window": {
                "title": title_buf.value,
                "process": process_name,
                "pid": proc_id.value,
            },
            "ui_tree_preview": [],
            "artifact": {
                "title": "UI Inspect",
                "kind": "text",
                "content": summary,
            },
        }

    return {"ui_inspect": ui_inspect}
