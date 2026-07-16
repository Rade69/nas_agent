"""Chromium browser discovery on Windows (C2).

Detects installed browsers without reading history/cookies/content.
Uses registry App Paths, known install directories, and shutil.which()
as fallback. Returns installation status only — extension connection
status is tracked separately by the broker.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

# Canonical browser kinds and their detection metadata
BROWSER_DEFINITIONS: list[dict[str, Any]] = [
    {
        "browser_kind": "chrome",
        "display_name": "Google Chrome",
        "registry_key": "chrome.exe",
        "exe_name": "chrome.exe",
        "profile_dirs": ["%LOCALAPPDATA%/Google/Chrome/User Data"],
        "known_paths": [
            "%LOCALAPPDATA%/Google/Chrome/Application/chrome.exe",
            "%PROGRAMFILES%/Google/Chrome/Application/chrome.exe",
            "%PROGRAMFILES(X86)%/Google/Chrome/Application/chrome.exe",
        ],
    },
    {
        "browser_kind": "edge",
        "display_name": "Microsoft Edge",
        "registry_key": "msedge.exe",
        "exe_name": "msedge.exe",
        "profile_dirs": ["%LOCALAPPDATA%/Microsoft/Edge/User Data"],
        "known_paths": [
            "%PROGRAMFILES(X86)%/Microsoft/Edge/Application/msedge.exe",
            "%PROGRAMFILES%/Microsoft/Edge/Application/msedge.exe",
        ],
    },
    {
        "browser_kind": "brave",
        "display_name": "Brave",
        "registry_key": "brave.exe",
        "exe_name": "brave.exe",
        "profile_dirs": ["%LOCALAPPDATA%/BraveSoftware/Brave-Browser/User Data"],
        "known_paths": [
            "%LOCALAPPDATA%/BraveSoftware/Brave-Browser/Application/brave.exe",
            "%PROGRAMFILES%/BraveSoftware/Brave-Browser/Application/brave.exe",
            "%PROGRAMFILES(X86)%/BraveSoftware/Brave-Browser/Application/brave.exe",
        ],
    },
    {
        "browser_kind": "vivaldi",
        "display_name": "Vivaldi",
        "registry_key": "vivaldi.exe",
        "exe_name": "vivaldi.exe",
        "profile_dirs": ["%LOCALAPPDATA%/Vivaldi/User Data"],
        "known_paths": [
            "%LOCALAPPDATA%/Vivaldi/Application/vivaldi.exe",
            "%PROGRAMFILES%/Vivaldi/Application/vivaldi.exe",
        ],
    },
    {
        "browser_kind": "opera",
        "display_name": "Opera",
        "registry_key": "opera.exe",
        "exe_name": "opera.exe",
        "profile_dirs": ["%APPDATA%/Opera Software/Opera Stable"],
        "known_paths": [
            "%LOCALAPPDATA%/Programs/Opera/opera.exe",
            "%PROGRAMFILES%/Opera/opera.exe",
        ],
    },
    {
        "browser_kind": "opera_gx",
        "display_name": "Opera GX",
        "registry_key": "opera_gx.exe",  # unlikely in registry, check paths
        "exe_name": "opera.exe",  # Opera GX uses same exe name
        "profile_dirs": ["%APPDATA%/Opera Software/Opera GX Stable"],
        "known_paths": [
            "%LOCALAPPDATA%/Programs/Opera GX/opera.exe",
            "%PROGRAMFILES%/Opera GX/opera.exe",
        ],
    },
    {
        "browser_kind": "chromium",
        "display_name": "Chromium",
        "registry_key": "chromium.exe",  # unlikely in registry
        "exe_name": "chrome.exe",
        "profile_dirs": ["%LOCALAPPDATA%/Chromium/User Data"],
        "known_paths": [
            "%LOCALAPPDATA%/Chromium/Application/chrome.exe",
        ],
    },
]

# Speech-to-text aliases
BROWSER_ALIASES: dict[str, str] = {
    "brejv": "brave",
    "edž": "edge",
    "edz": "edge",
    "hrom": "chrome",
    "google chrome": "chrome",
    "microsoft edge": "edge",
    "opera gx": "opera_gx",
    "opera ge-iks": "opera_gx",
}


def _expand_env(path_template: str) -> str:
    """Expand %ENVVAR% patterns in a path template."""
    return str(Path(
        path_template
        .replace("%LOCALAPPDATA%", _get_env("LOCALAPPDATA", ""))
        .replace("%APPDATA%", _get_env("APPDATA", ""))
        .replace("%PROGRAMFILES%", _get_env("PROGRAMFILES", ""))
        .replace("%PROGRAMFILES(X86)%", _get_env("PROGRAMFILES(X86)", ""))
    ))


def _get_env(name: str, default: str) -> str:
    import os
    return os.environ.get(name, default)


def _check_registry_app_path(exe_name: str) -> bool:
    """Check if browser is registered in Windows App Paths."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe_name}",
            )
            winreg.CloseKey(key)
            return True
        except OSError:
            pass
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe_name}",
            )
            winreg.CloseKey(key)
            return True
        except OSError:
            pass
    except Exception:
        pass
    return False


def _check_known_paths(known_paths: list[str], exe_name: str) -> bool:
    """Check known install paths for the browser executable."""
    # Expand env vars in known paths
    for path_template in known_paths:
        expanded = _expand_env(path_template)
        if Path(expanded).is_file():
            return True
    # Also check shutil.which
    if shutil.which(exe_name):
        return True
    return False


def discover_browsers() -> list[dict[str, Any]]:
    """Discover installed Chromium browsers on this machine.

    Returns a list of browser entries with installation status.
    Does NOT check extension connection status — that's the broker's job.
    """
    if sys.platform != "win32":
        return []

    results: list[dict[str, Any]] = []
    for definition in BROWSER_DEFINITIONS:
        installed = _check_registry_app_path(definition["registry_key"]) or \
                    _check_known_paths(definition["known_paths"], definition["exe_name"])

        # Check which profile directories exist
        profile_dirs = []
        for pd_template in definition["profile_dirs"]:
            expanded = _expand_env(pd_template)
            if Path(expanded).is_dir():
                profile_dirs.append(expanded)

        results.append({
            "browser_kind": definition["browser_kind"],
            "display_name": definition["display_name"],
            "installed": installed,
            "profile_dirs": profile_dirs,
        })

    return results


def normalize_browser(raw: str) -> str:
    """Normalize a browser name (including speech-to-text aliases)."""
    normalized = raw.strip().lower()
    return BROWSER_ALIASES.get(normalized, normalized)
