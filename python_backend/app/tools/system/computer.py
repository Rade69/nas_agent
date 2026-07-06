"""Windows computer-use tool handlers (FAZA 13).

1:1 Python replacements for the legacy PowerShell computer_* tools in
electron/tools_legacy/powershell/. Uses ctypes + Win32 API (SendInput,
SetCursorPos, mouse_event) — no extra dependencies beyond stdlib.

All handlers require computer mode (enforced by the permission engine via
requires_computer_mode=True on each ToolDefinition).

Risk model (see SECURITY_MODEL.md):
  - computer_open_app:  medium (launches arbitrary process, but visible to user)
  - computer_type_text: high   (injects keystrokes into the active window)
  - computer_press_key: medium (single key injection, limited set)
  - computer_click:     high   (can click dangerous UI elements)
  - computer_scroll:    medium (read-only effect on viewport, but changes what's visible)
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes
from typing import Any


# ---------------------------------------------------------------------------
# Win32 API constants (kept module-private)
# ---------------------------------------------------------------------------

# Input type
_INPUT_MOUSE = 0
_INPUT_KEYBOARD = 1

# Keyboard event flags
_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_SCANCODE = 0x0008

# Mouse event flags
_MOUSEEVENTF_LEFTDOWN = 0x0002
_MOUSEEVENTF_LEFTUP = 0x0004
_MOUSEEVENTF_WHEEL = 0x0800
_MOUSEEVENTF_HWHEEL = 0x1000

# Virtual-key codes for special keys
_VK_CODES: dict[str, int] = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "delete": 0x2E,
    "space": 0x20,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}


# ---------------------------------------------------------------------------
# SendInput ctypes structures
# ---------------------------------------------------------------------------

class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# ---------------------------------------------------------------------------
# Internal helpers — only callable on win32
# ---------------------------------------------------------------------------

def _check_win32() -> None:
    if sys.platform != "win32":
        raise RuntimeError("computer_* tools are only supported on Windows.")


def _send_input(*inputs: _INPUT) -> int:
    """Send one or more INPUT structures via SendInput. Returns count of events inserted."""
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    n = len(inputs)
    arr = (_INPUT * n)(*inputs)
    return user32.SendInput(n, arr, ctypes.sizeof(_INPUT))


def _key_down(vk: int, extended: bool = False) -> None:
    flags = _KEYEVENTF_SCANCODE
    if extended:
        flags |= 0x0001  # KEYEVENTF_EXTENDEDKEY
    inp = _INPUT()
    inp.type = _INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)  # type: ignore[attr-defined]
    inp.union.ki.dwFlags = flags
    _send_input(inp)


def _key_up(vk: int, extended: bool = False) -> None:
    flags = _KEYEVENTF_KEYUP | _KEYEVENTF_SCANCODE
    if extended:
        flags |= 0x0001
    inp = _INPUT()
    inp.type = _INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)  # type: ignore[attr-defined]
    inp.union.ki.dwFlags = flags
    _send_input(inp)


def _press_key(vk: int, extended: bool = False) -> None:
    """Press and release a single key (down + up). Used for simple special keys (enter, tab, …)."""
    _key_down(vk, extended)
    time.sleep(0.01)
    _key_up(vk, extended)


def _type_unicode_char(ch: str) -> None:
    """Send a single Unicode character via SendInput KEYEVENTF_UNICODE."""
    if len(ch) != 1:
        return
    code = ord(ch)
    # KEYEVENTF_UNICODE: wVk=0, wScan=the UTF-16 code unit
    inp_down = _INPUT()
    inp_down.type = _INPUT_KEYBOARD
    inp_down.union.ki.wVk = 0
    inp_down.union.ki.wScan = code
    inp_down.union.ki.dwFlags = _KEYEVENTF_UNICODE

    inp_up = _INPUT()
    inp_up.type = _INPUT_KEYBOARD
    inp_up.union.ki.wVk = 0
    inp_up.union.ki.wScan = code
    inp_up.union.ki.dwFlags = _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP

    _send_input(inp_down, inp_up)


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

# Key code → SendKey approach is deliberately "stupid" — one character at a
# time via KEYEVENTF_UNICODE. This is slower than PowerShell's SendKeys but
# stays entirely in stdlib with no .NET dependency. CR/LF → Enter key.
# For a faster approach, a future phase can batch scancodes.

def _handle_open_app(arguments: dict[str, Any]) -> dict[str, Any]:
    app_name = str(arguments.get("appName", "")).strip()
    if not app_name:
        raise ValueError("appName is required.")
    _check_win32()
    try:
        # os.startfile opens a file/app with its associated program on Windows.
        # Falls back to subprocess.Popen for executables that need direct launch.
        os.startfile(app_name)
    except OSError:
        # Some apps (especially without file associations) need Popen.
        subprocess.Popen(app_name, shell=True)
    return {"message": f"Opened {app_name}.", "app_name": app_name}


def _handle_type_text(arguments: dict[str, Any]) -> dict[str, Any]:
    text = str(arguments.get("text", ""))
    if not text:
        raise ValueError("text is required.")
    _check_win32()
    for ch in text:
        if ch == "\n" or ch == "\r":
            if ch == "\r":
                continue  # skip CR; LF alone is enough
            _press_key(_VK_CODES["enter"])
        elif ch == "\t":
            _press_key(_VK_CODES["tab"])
        else:
            _type_unicode_char(ch)
        time.sleep(0.002)  # ~2 ms per char — fast enough, still safe
    return {"message": "Typed text into the active app.", "length": len(text)}


def _handle_press_key(arguments: dict[str, Any]) -> dict[str, Any]:
    key = str(arguments.get("key", "")).lower().strip()
    if not key:
        raise ValueError("key is required.")
    vk = _VK_CODES.get(key)
    if vk is None:
        raise ValueError(f"Unsupported key: {key}. Supported: {', '.join(sorted(_VK_CODES))}.")
    repeat = max(1, min(20, int(arguments.get("repeat", 1) or 1)))
    _check_win32()
    for _ in range(repeat):
        _press_key(vk)
        time.sleep(0.01)
    return {"message": f"Pressed {key}." + (f" x{repeat}" if repeat > 1 else ""), "key": key, "repeat": repeat}


def _handle_click(arguments: dict[str, Any]) -> dict[str, Any]:
    x = arguments.get("x")
    y = arguments.get("y")
    if x is None or y is None:
        raise ValueError("x and y are required for computer_click.")
    x = int(x)
    y = int(y)
    _check_win32()
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    user32.mouse_event(_MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(_MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {"message": f"Clicked {x}, {y}.", "x": x, "y": y}


def _handle_scroll(arguments: dict[str, Any]) -> dict[str, Any]:
    raw_direction = arguments.get("direction")
    if raw_direction is None or str(raw_direction).strip() == "":
        raise ValueError("direction is required.")
    direction = str(raw_direction).lower().strip()
    if direction not in ("up", "down", "left", "right"):
        raise ValueError(f"Unsupported scroll direction: {direction}. Use up/down/left/right.")
    raw_amount = arguments.get("amount", 4)
    amount = max(1, min(20, int(raw_amount) if raw_amount is not None else 4))
    _check_win32()
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    wheel_delta = 120 * amount
    is_horizontal = direction in ("left", "right")
    flags = _MOUSEEVENTF_HWHEEL if is_horizontal else _MOUSEEVENTF_WHEEL
    dw_data = -wheel_delta if direction in ("down", "left") else wheel_delta
    user32.mouse_event(flags, 0, 0, dw_data, 0)
    return {"message": f"Scrolled {direction}.", "direction": direction, "amount": amount}


def make_handlers() -> dict[str, Any]:
    """Return a dict of tool_name → handler suitable for registration in ToolRegistry."""
    return {
        "computer_open_app": _handle_open_app,
        "computer_type_text": _handle_type_text,
        "computer_press_key": _handle_press_key,
        "computer_click": _handle_click,
        "computer_scroll": _handle_scroll,
    }