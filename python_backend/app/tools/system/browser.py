"""Safe Windows browser launcher used by the dedicated browser_open tool.

Separates browser navigation from generic computer-use launching: only an
allowlisted browser and an optional validated HTTP(S) URL can reach the OS.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.errors import AppError


_BROWSER_EXECUTABLES: dict[str, str] = {
    "brave": "brave.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
}

_BROWSER_ALIASES: dict[str, str] = {
    # Common Serbian/Bosnian/Croatian speech-to-text spelling.
    "brejv": "brave",
}


def _validate_url(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    url = str(value).strip()
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute http:// or https:// URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("url must not contain embedded credentials.")
    return url


def _candidate_paths(browser: str) -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("PROGRAMFILES", ""))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", ""))
    if browser == "brave":
        return [
            local / "BraveSoftware/Brave-Browser/Application/brave.exe",
            program_files / "BraveSoftware/Brave-Browser/Application/brave.exe",
            program_files_x86 / "BraveSoftware/Brave-Browser/Application/brave.exe",
        ]
    if browser == "chrome":
        return [
            local / "Google/Chrome/Application/chrome.exe",
            program_files / "Google/Chrome/Application/chrome.exe",
            program_files_x86 / "Google/Chrome/Application/chrome.exe",
        ]
    if browser == "edge":
        return [
            program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
            program_files / "Microsoft/Edge/Application/msedge.exe",
        ]
    return [
        program_files / "Mozilla Firefox/firefox.exe",
        program_files_x86 / "Mozilla Firefox/firefox.exe",
    ]


def _find_browser(browser: str) -> str | None:
    executable = _BROWSER_EXECUTABLES[browser]
    from_path = shutil.which(executable)
    if from_path:
        return from_path
    return next((str(path) for path in _candidate_paths(browser) if path.is_file()), None)


def _handle_browser_open(arguments: dict[str, Any]) -> dict[str, Any]:
    if sys.platform != "win32":
        raise AppError("BROWSER_UNAVAILABLE", "browser_open is available only on Windows.")

    requested_browser = str(arguments.get("browser", "default")).strip().lower() or "default"
    browser = _BROWSER_ALIASES.get(requested_browser, requested_browser)
    if browser not in {"default", *_BROWSER_EXECUTABLES}:
        raise ValueError("browser must be one of: default, brave, brejv, chrome, edge, firefox.")
    url = _validate_url(arguments.get("url"))
    target = url or "about:blank"

    try:
        if browser == "default":
            if not webbrowser.open(target, new=1):
                raise AppError("BROWSER_OPEN_FAILED", "Windows did not accept the default-browser launch request.")
            return {
                "message": "Opened the default browser.",
                "browser": "default",
                "url": url,
                "launch_accepted": True,
                "process_started": None,
            }

        executable = _find_browser(browser)
        if executable is None:
            raise AppError("BROWSER_NOT_INSTALLED", f"Browser '{browser}' was not found on this computer.", 404)
        process = subprocess.Popen([executable, target], shell=False)
        return {
            "message": f"Opened {browser}.",
            "browser": browser,
            "url": url,
            "launch_accepted": True,
            "process_started": True,
            "process_id": process.pid,
        }
    except AppError:
        raise
    except OSError as exc:
        raise AppError("BROWSER_OPEN_FAILED", f"Could not open browser '{browser}': {exc}") from exc


def make_handler():
    """Return the browser_open handler for ToolRegistry registration."""
    return _handle_browser_open
