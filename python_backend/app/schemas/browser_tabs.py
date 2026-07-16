"""Pydantic models for the browser_tabs tool (PR 1 — list only).

Snapshot-based design: every mutation (activate/close) must reference
a recent list snapshot. A stale snapshot (TTL expired or tabs changed)
is never acted on — the caller must list again.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TabEntry(BaseModel):
    """One tab in a snapshot — metadata only, never page content."""

    position: int  # 1-based display order
    tab_id: str
    title: str
    url: str
    active: bool
    pinned: bool
    audible: bool
    incognito: bool
    window_id: str


class TabSnapshot(BaseModel):
    """Immutable point-in-time tab list bound to one browser window."""

    snapshot_id: str
    browser: str  # "brave" | "chrome"
    scope: str  # "current_window" | "all_windows"
    window_id: str | None = None  # None for all_windows scope
    created_at: datetime
    count: int
    tabs: list[TabEntry]


class TabListResult(BaseModel):
    """Returned by browser_tabs action='list'."""

    browser: str
    scope: str
    window_id: str | None
    snapshot_id: str
    created_at: datetime
    count: int
    tabs: list[TabEntry]
    message: str


class TabActivateResult(BaseModel):
    """Returned by browser_tabs action='activate'."""

    ok: bool
    browser: str
    snapshot_id: str
    position: int
    tab_id: str | None = None
    title: str | None = None
    message: str


class TabCloseResult(BaseModel):
    """Returned by browser_tabs action='close'."""

    ok: bool
    browser: str
    snapshot_id: str
    position: int
    tab_id: str | None = None
    title: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

BROWSER_TAB_ERROR_CODES = {
    "BROWSER_EXTENSION_NOT_CONNECTED": "The browser extension is not connected. Open the extension settings to pair it with Ricky.",
    "BROWSER_EXTENSION_AUTH_FAILED": "The browser extension could not authenticate. Check the pairing secret.",
    "BROWSER_PROFILE_NOT_FOUND": "The requested browser profile was not found.",
    "BROWSER_WINDOW_NOT_FOUND": "The target browser window was not found or was closed.",
    "TAB_NOT_FOUND": "The requested tab position does not match any open tab.",
    "TAB_POSITION_OUT_OF_RANGE": "The requested position is out of range for the current tab list.",
    "TAB_SNAPSHOT_STALE": "The tab list has changed. Please list tabs again to get the current state.",
    "TAB_ACTION_TIMEOUT": "The requested action timed out. The browser extension may be unresponsive.",
    "TAB_ACTION_FAILED": "The browser tab action failed.",
    "INCOGNITO_NOT_ALLOWED": "Incognito tabs are excluded by default.",
}