"""Safe folder/file opener used by the dedicated open_path tool.

Companion to filesystem_search: filesystem_search finds a path, open_path
opens it in File Explorer. Together they close the "find -> open" chain
without a single confirmation-gated computer_click — which was the main UX
frustration before this tool existed (see filesystem_search.py docstring).

Security model:
  - Folders: os.startfile(folder) — opens Explorer at that folder. Benign:
    does not read/modify contents, does not execute anything.
  - Files: explorer.exe /select,<path> — opens the containing folder and
    SELECTS the file. NEVER os.startfile on a file (that would launch it
    with its default application — dangerous for .exe/.bat/.ps1 etc.).
  - Path validation: resolve_within_roots() rejects UNC/network paths,
    resolves symlinks and `..` traversal, and confirms the path is inside
    one of the same search roots filesystem_search walks. This means a
    path the search tool could return is always openable here, while a
    model-injected path from prompt-injected content that points outside
    allowed roots is rejected.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.core.path_sandbox import resolve_within_roots


def _drive_roots() -> list[Path]:
    if os.name != "nt":
        return []
    roots: list[Path] = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = Path(f"{letter}:\\")
        if drive.exists():
            roots.append(drive)
    return roots


def _search_roots(data_dir: Path) -> list[Path]:
    """Same root set as filesystem_search._search_roots — a path the search
    tool can find is always openable here. Duplicated (not imported) to keep
    the two modules decoupled; if the root set ever changes, update both."""
    home = Path.home()
    ordered = [data_dir, home, *_drive_roots()]
    seen: set[Path] = set()
    roots: list[Path] = []
    for root in ordered:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def _handle_open_path(arguments: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    raw_path = str(arguments.get("path", "")).strip()
    if not raw_path:
        raise ValueError("path is required.")

    if sys.platform != "win32":
        raise AppError("OPEN_PATH_UNAVAILABLE", "open_path is available only on Windows.")

    allowed_roots = _search_roots(data_dir)
    resolved = resolve_within_roots(raw_path, allowed_roots)

    if not resolved.exists():
        raise AppError("PATH_NOT_FOUND", f"Path does not exist: {raw_path}", status_code=404)

    if resolved.is_dir():
        # Folder: open Explorer at this folder directly. Benign — no content
        # is read or modified, nothing is executed.
        os.startfile(str(resolved))  # type: ignore[attr-defined]
        return {
            "message": f"Opened folder: {resolved}",
            "path": str(resolved),
            "kind": "folder",
        }
    else:
        # File: open the containing folder and SELECT the file. NEVER
        # os.startfile on a file — that would launch it with its default
        # application, which is dangerous for executables/scripts.
        subprocess.Popen(["explorer.exe", "/select,", str(resolved)], shell=False)
        return {
            "message": f"Selected file in Explorer: {resolved}",
            "path": str(resolved),
            "kind": "file",
        }


def make_handler(data_dir: Path):
    """Return the open_path handler for ToolRegistry registration."""
    def open_path(arguments: dict[str, Any]) -> dict[str, Any]:
        return _handle_open_path(arguments, data_dir)
    return open_path
