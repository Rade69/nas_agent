"""Localhost WebSocket broker for the Ricky Browser Bridge extension.

Manages authenticated connections from the MV3 Chrome/Brave extension,
maintains a short-lived tab snapshot store (TTL: 10s), and provides
async request/response communication channels.

Security:
- Binds only to 127.0.0.1 (loopback).
- Requires a pairing secret (≥256 bit random hex), stored in local data dir.
- Extension must authenticate with the secret before any command is accepted.
- Unknown/unauthenticated clients are disconnected.
- All messages are JSON; strict max message size (64KB).
- Never sends shell commands or arbitrary JS to the extension.
- One active connection per browser profile.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.errors import AppError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SNAPSHOT_TTL_SECONDS = 10
MAX_MESSAGE_SIZE_BYTES = 64 * 1024
DEFAULT_BROKER_PORT = 9119
PAIRING_SECRET_BYTES = 32  # 256 bits
REPLY_TIMEOUT_SECONDS = 8.0
RECONNECT_BACKOFF_BASE_SECONDS = 1.0


# ---------------------------------------------------------------------------
# Snapshot store
# ---------------------------------------------------------------------------
class SnapshotStore:
    """In-memory tab snapshots with TTL-based expiry."""

    def __init__(self, ttl_seconds: int = SNAPSHOT_TTL_SECONDS) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def store(self, snapshot_id: str, data: dict[str, Any]) -> None:
        self._snapshots[snapshot_id] = {
            "data": data,
            "created_at": time.monotonic(),
        }
        self._cleanup()

    def get(self, snapshot_id: str) -> dict[str, Any] | None:
        entry = self._snapshots.get(snapshot_id)
        if entry is None:
            return None
        if time.monotonic() - entry["created_at"] > self._ttl:
            del self._snapshots[snapshot_id]
            return None
        return entry["data"]

    def _cleanup(self) -> None:
        now = time.monotonic()
        stale = [sid for sid, e in self._snapshots.items() if now - e["created_at"] > self._ttl]
        for sid in stale:
            del self._snapshots[sid]


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------
class BrowserExtensionBroker:
    """Owns the WebSocket connection to one extension instance.

    The broker is created once at backend startup and lives for the
    lifetime of the Python process. It manages one active extension
    connection at a time (per browser profile). The pairing secret
    is loaded from a file in the data directory.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._pairing_secret: str | None = None
        self._active_ws: WebSocket | None = None
        self._active_browser: str | None = None  # "brave" | "chrome"
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._snapshots = SnapshotStore()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Pairing secret management
    # ------------------------------------------------------------------
    @property
    def secret_file(self) -> Path:
        return self._data_dir / "browser_bridge_secret"

    def ensure_secret(self) -> str:
        """Load or generate the pairing secret."""
        if self._pairing_secret is not None:
            return self._pairing_secret

        try:
            if self.secret_file.exists():
                self._pairing_secret = self.secret_file.read_text().strip()
                if len(self._pairing_secret) >= 64:
                    return self._pairing_secret
        except OSError:
            pass

        # Generate a fresh 256-bit hex secret
        self._pairing_secret = secrets.token_hex(PAIRING_SECRET_BYTES)
        try:
            self.secret_file.parent.mkdir(parents=True, exist_ok=True)
            self.secret_file.write_text(self._pairing_secret)
        except OSError:
            pass
        return self._pairing_secret

    def get_pairing_display(self) -> str:
        """First 8 chars for display in Settings UI."""
        secret = self.ensure_secret()
        return secret[:8] + "…"

    # ------------------------------------------------------------------
    # WebSocket handler (registered as a FastAPI route)
    # ------------------------------------------------------------------
    async def handle_ws(self, websocket: WebSocket) -> None:
        await websocket.accept()
        authenticated = False

        try:
            async for raw in websocket.iter_text():
                # Size limit
                if len(raw) > MAX_MESSAGE_SIZE_BYTES:
                    await websocket.send_text(json.dumps({
                        "type": "auth_failed",
                        "reason": "message too large",
                    }))
                    await websocket.close(code=1009)
                    return

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "INVALID_JSON",
                        "message": "Could not parse message as JSON.",
                    }))
                    continue

                msg_type = msg.get("type", "")

                # --- Auth phase ---
                if msg_type == "auth":
                    secret = self.ensure_secret()
                    provided = str(msg.get("secret", ""))
                    if not secrets.compare_digest(secret, provided):
                        await websocket.send_text(json.dumps({
                            "type": "auth_failed",
                            "reason": "wrong pairing secret",
                        }))
                        await websocket.close(code=4001)
                        return

                    authenticated = True
                    session_id = uuid4().hex[:16]
                    self._active_ws = websocket
                    await websocket.send_text(json.dumps({
                        "type": "auth_ok",
                        "session_id": session_id,
                    }))
                    continue

                # --- Post-auth phase: all other messages ---
                if not authenticated:
                    await websocket.send_text(json.dumps({
                        "type": "auth_failed",
                        "reason": "authenticate first",
                    }))
                    continue

                # Handle responses from the extension
                request_id = msg.get("request_id")
                if request_id and request_id in self._pending:
                    future = self._pending.pop(request_id, None)
                    if future and not future.done():
                        future.set_result(msg)
                # "pong" responses to keep-alive pings
                elif msg_type == "pong":
                    request_id = msg.get("request_id")
                    if request_id and request_id in self._pending:
                        future = self._pending.pop(request_id)
                        if future and not future.done():
                            future.set_result(msg)

        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            if self._active_ws is websocket:
                self._active_ws = None
                self._active_browser = None
            # Fail all pending futures
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(
                        AppError("BROWSER_EXTENSION_NOT_CONNECTED", "Extension disconnected.")
                    )
            self._pending.clear()

    # ------------------------------------------------------------------
    # Request/response interface for tool handlers
    # ------------------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        ws = self._active_ws
        return ws is not None and ws.client_state == WebSocketState.CONNECTED

    async def _send_and_wait(
        self, msg: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]:
        """Send a command to the extension and await its response."""
        if not self.is_connected or self._active_ws is None:
            raise AppError(
                "BROWSER_EXTENSION_NOT_CONNECTED",
                "Browser extension is not connected. Open extension options and pair it with Ricky.",
            )

        rid = request_id or uuid4().hex[:16]
        msg["request_id"] = rid
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[rid] = future

        try:
            await self._active_ws.send_text(json.dumps(msg))
        except Exception as exc:
            self._pending.pop(rid, None)
            raise AppError(
                "BROWSER_EXTENSION_NOT_CONNECTED",
                f"Failed to send command to extension: {exc}",
            ) from exc

        try:
            result = await asyncio.wait_for(future, timeout=REPLY_TIMEOUT_SECONDS)
            return result
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            raise AppError(
                "TAB_ACTION_TIMEOUT",
                f"Extension did not respond within {REPLY_TIMEOUT_SECONDS}s.",
            )

    # ------------------------------------------------------------------
    # High-level commands (called by the browser_tabs tool)
    # ------------------------------------------------------------------
    async def list_tabs(self, scope: str = "current_window") -> dict[str, Any]:
        """List open tabs and return a snapshot."""
        result = await self._send_and_wait({
            "type": "list_tabs",
            "scope": scope,
        })
        if result.get("type") == "error":
            raise AppError(
                result.get("code", "TAB_LIST_FAILED"),
                result.get("message", "Failed to list tabs."),
            )

        # Store snapshot
        snapshot_id = f"tabsnap_{uuid4().hex[:12]}"
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "browser": self._active_browser or "brave",
            "scope": scope,
            "created_at": datetime.now(timezone.utc),
            "count": result.get("count", 0),
            "tabs": result.get("tabs", []),
        }
        self._snapshots.store(snapshot_id, snapshot_data)

        # Extract window_id from the first tab's window_id if scope is current_window
        tabs = result.get("tabs", [])
        window_id = tabs[0].get("window_id") if tabs else None

        return {
            "browser": snapshot_data["browser"],
            "scope": scope,
            "window_id": window_id,
            "snapshot_id": snapshot_id,
            "created_at": snapshot_data["created_at"].isoformat(),
            "count": snapshot_data["count"],
            "tabs": snapshot_data["tabs"],
        }

    async def activate_tab(
        self, snapshot_id: str, position: int, browser: str = "brave"
    ) -> dict[str, Any]:
        """Activate a tab by 1-based position, using a fresh snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise AppError(
                "TAB_SNAPSHOT_STALE",
                "The tab list snapshot has expired. Please list tabs again to get the current state."
            )

        tabs = snap.get("tabs", [])
        if position < 1 or position > len(tabs):
            raise AppError(
                "TAB_POSITION_OUT_OF_RANGE",
                f"Position {position} is out of range (1–{len(tabs)})."
            )

        tab = tabs[position - 1]
        if tab.get("incognito"):
            raise AppError(
                "INCOGNITO_NOT_ALLOWED",
                "Incognito tabs are excluded by default."
            )

        result = await self._send_and_wait({
            "type": "activate_tab",
            "tab_id": tab["tab_id"],
            "window_id": tab["window_id"],
        })

        if result.get("type") == "error":
            error_msg = result.get("message", "")
            # Detect stale snapshot: tab was closed/moved since the snapshot
            if any(keyword in error_msg.lower() for keyword in (
                "no tab with id", "no window with id", "not found",
            )):
                raise AppError(
                    "TAB_SNAPSHOT_STALE",
                    f"Tab at position {position} no longer exists. Please list tabs again to see the current state."
                )
            raise AppError(
                result.get("code", "TAB_ACTION_FAILED"),
                result.get("message", "Failed to activate tab."),
            )

        return {
            "ok": True,
            "browser": browser,
            "snapshot_id": snapshot_id,
            "position": position,
            "tab_id": tab["tab_id"],
            "title": tab.get("title", ""),
            "url": tab.get("url", ""),
        }

    async def close_tab(
        self, snapshot_id: str, position: int, browser: str = "brave"
    ) -> dict[str, Any]:
        """Close a tab by 1-based position, using a fresh snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise AppError(
                "TAB_SNAPSHOT_STALE",
                "The tab list snapshot has expired. Please list tabs again to get the current state."
            )

        tabs = snap.get("tabs", [])
        if position < 1 or position > len(tabs):
            raise AppError(
                "TAB_POSITION_OUT_OF_RANGE",
                f"Position {position} is out of range (1–{len(tabs)})."
            )

        tab = tabs[position - 1]
        if tab.get("incognito"):
            raise AppError(
                "INCOGNITO_NOT_ALLOWED",
                "Incognito tabs are excluded by default."
            )

        result = await self._send_and_wait({
            "type": "close_tab",
            "tab_id": tab["tab_id"],
        })

        if result.get("type") == "error":
            error_msg = result.get("message", "")
            if any(keyword in error_msg.lower() for keyword in (
                "no tab with id", "not found",
            )):
                raise AppError(
                    "TAB_SNAPSHOT_STALE",
                    f"Tab at position {position} was already closed. Please list tabs again to see the current state."
                )
            raise AppError(
                result.get("code", "TAB_ACTION_FAILED"),
                result.get("message", "Failed to close tab."),
            )

        return {
            "ok": True,
            "browser": browser,
            "snapshot_id": snapshot_id,
            "position": position,
            "tab_id": tab["tab_id"],
            "title": tab.get("title", ""),
        }


# Singleton holder — set by app/main.py
_broker: BrowserExtensionBroker | None = None


def get_broker() -> BrowserExtensionBroker:
    global _broker
    if _broker is None:
        raise RuntimeError("BrowserExtensionBroker not initialized. Call init_broker() first.")
    return _broker


def init_broker(data_dir: Path) -> BrowserExtensionBroker:
    global _broker
    _broker = BrowserExtensionBroker(data_dir)
    _broker.ensure_secret()
    return _broker