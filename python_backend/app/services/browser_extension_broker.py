"""Localhost WebSocket broker for the Ricky Browser Bridge extension.

C1: Multi-connection registry — supports multiple simultaneous browser
profiles with per-profile routing, snapshot binding, and revoke.

Manages authenticated connections from MV3 Chrome/Brave/Edge extensions,
maintains a short-lived tab snapshot store (TTL: 10s), and provides
async request/response communication channels.

Security:
- Binds only to 127.0.0.1 (loopback).
- Pairing: one-time 5-minute token, per-install credential after pairing.
- Per-profile credentials; snapshots bound to profile_id.
- Unknown/unauthenticated clients are disconnected.
- All messages are JSON; strict max message size (64KB).
- Never sends shell commands or arbitrary JS to the extension.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
PAIRING_SECRET_BYTES = 32  # 256 bits
CREDENTIAL_BYTES = 32
PAIRING_TOKEN_TTL_SECONDS = 300  # 5 minutes
HUMAN_CODE_LENGTH = 6
REPLY_TIMEOUT_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Snapshot store — now with profile binding
# ---------------------------------------------------------------------------
class SnapshotStore:
    """In-memory tab snapshots with TTL-based expiry and profile binding."""

    def __init__(self, ttl_seconds: int = SNAPSHOT_TTL_SECONDS) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def store(self, snapshot_id: str, data: dict[str, Any]) -> None:
        self._snapshots[snapshot_id] = {
            "data": data,
            "created_at": time.monotonic(),
        }
        self._cleanup()

    def get(self, snapshot_id: str, profile_id: str | None = None) -> dict[str, Any] | None:
        entry = self._snapshots.get(snapshot_id)
        if entry is None:
            return None
        if time.monotonic() - entry["created_at"] > self._ttl:
            del self._snapshots[snapshot_id]
            return None
        data = entry["data"]
        # Profile binding: if profile_id is specified, snapshot must match
        if profile_id and data.get("profile_id") != profile_id:
            return None  # Silently reject — snapshot from different profile
        return data

    def _cleanup(self) -> None:
        now = time.monotonic()
        stale = [sid for sid, e in self._snapshots.items() if now - e["created_at"] > self._ttl]
        for sid in stale:
            del self._snapshots[sid]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class PairingSession:
    pairing_id: str
    human_code: str
    full_token: str
    browser_kind: str
    expires_at: float
    status: str = "pending"
    profile_id: str | None = None


@dataclass
class InstallCredential:
    installation_id: str
    profile_id: str
    credential: str
    browser_kind: str
    profile_label: str
    extension_version: str
    created_at: datetime
    last_seen_at: datetime | None = None
    revoked: bool = False


@dataclass
class ConnectionState:
    profile_id: str
    installation_id: str
    websocket: WebSocket
    install: InstallCredential
    pending: dict[str, asyncio.Future[dict[str, Any]]] = field(default_factory=dict)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------
class BrowserExtensionBroker:
    """C1: Multi-connection broker.

    Supports multiple simultaneous browser profiles. Each connection
    is keyed by profile_id. Snapshots are bound to the originating
    profile and cannot be used across profiles.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._legacy_secret: str | None = None
        # C1: connection registry (profile_id → ConnectionState)
        self._connections: dict[str, ConnectionState] = {}
        self._snapshots = SnapshotStore()
        # Pairing
        self._pairing_sessions: dict[str, PairingSession] = {}
        self._human_code_index: dict[str, str] = {}
        # Credentials (installation_id → InstallCredential, survives reconnect)
        self._install_credentials: dict[str, InstallCredential] = {}

    # ------------------------------------------------------------------
    # Legacy secret (backward compat)
    # ------------------------------------------------------------------
    @property
    def secret_file(self) -> Path:
        return self._data_dir / "browser_bridge_secret"

    def _ensure_legacy_secret(self) -> str:
        if self._legacy_secret is not None:
            return self._legacy_secret
        try:
            if self.secret_file.exists():
                self._legacy_secret = self.secret_file.read_text().strip()
                if len(self._legacy_secret) >= 64:
                    return self._legacy_secret
        except OSError:
            pass
        self._legacy_secret = secrets.token_hex(PAIRING_SECRET_BYTES)
        try:
            self.secret_file.parent.mkdir(parents=True, exist_ok=True)
            self.secret_file.write_text(self._legacy_secret)
        except OSError:
            pass
        return self._legacy_secret

    # ------------------------------------------------------------------
    # Pairing sessions
    # ------------------------------------------------------------------
    def create_pairing_session(self, browser_kind: str) -> dict[str, Any]:
        self._cleanup_expired_sessions()
        pairing_id = f"pair_{uuid4().hex[:12]}"
        human_code = _generate_human_code(self._human_code_index)
        full_token = secrets.token_hex(PAIRING_SECRET_BYTES)
        expires_at = time.monotonic() + PAIRING_TOKEN_TTL_SECONDS
        session = PairingSession(
            pairing_id=pairing_id, human_code=human_code,
            full_token=full_token, browser_kind=browser_kind,
            expires_at=expires_at,
        )
        self._pairing_sessions[pairing_id] = session
        self._human_code_index[human_code] = pairing_id
        return {
            "pairing_id": pairing_id, "human_code": human_code,
            "expires_in_seconds": PAIRING_TOKEN_TTL_SECONDS,
        }

    def get_pairing_session(self, pairing_id: str) -> dict[str, Any] | None:
        session = self._pairing_sessions.get(pairing_id)
        if session is None:
            return None
        if time.monotonic() > session.expires_at and session.status == "pending":
            session.status = "expired"
        return {
            "pairing_id": session.pairing_id, "human_code": session.human_code,
            "browser_kind": session.browser_kind, "status": session.status,
            "expires_in_seconds": max(0, int(session.expires_at - time.monotonic())),
        }

    def cancel_pairing_session(self, pairing_id: str) -> bool:
        session = self._pairing_sessions.get(pairing_id)
        if session is None or session.status != "pending":
            return False
        session.status = "expired"
        self._human_code_index.pop(session.human_code, None)
        return True

    def _consume_pairing_token(
        self, human_code: str, browser_kind: str, installation_id: str,
        profile_label: str, extension_version: str,
    ) -> InstallCredential | None:
        self._cleanup_expired_sessions()
        pairing_id = self._human_code_index.pop(human_code, None)
        if pairing_id is None:
            return None
        session = self._pairing_sessions.get(pairing_id)
        if session is None or session.status != "pending":
            return None
        if time.monotonic() > session.expires_at:
            session.status = "expired"
            return None
        if session.browser_kind != browser_kind:
            return None
        session.status = "consumed"
        session.profile_id = f"profile_{uuid4().hex[:12]}"
        credential = secrets.token_hex(CREDENTIAL_BYTES)
        install = InstallCredential(
            installation_id=installation_id,
            profile_id=session.profile_id,
            credential=credential,
            browser_kind=browser_kind,
            profile_label=profile_label or "Default",
            extension_version=extension_version,
            created_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        self._install_credentials[installation_id] = install
        return install

    def _cleanup_expired_sessions(self) -> None:
        now = time.monotonic()
        expired = [
            pid for pid, s in self._pairing_sessions.items()
            if s.status == "pending" and now > s.expires_at
        ]
        for pid in expired:
            session = self._pairing_sessions[pid]
            session.status = "expired"
            self._human_code_index.pop(session.human_code, None)

    # ------------------------------------------------------------------
    # Connection management (C1: multi-connection)
    # ------------------------------------------------------------------
    def _register_connection(self, ws: WebSocket, install: InstallCredential) -> ConnectionState:
        """Register or replace a connection for the given profile."""
        profile_id = install.profile_id
        # If this profile already has an active connection, close it
        old = self._connections.get(profile_id)
        if old is not None:
            self._fail_pending(old, "Connection replaced by newer session.")
            try:
                old.websocket.close(code=4000, reason="replaced")
            except Exception:
                pass
        conn = ConnectionState(
            profile_id=profile_id,
            installation_id=install.installation_id,
            websocket=ws,
            install=install,
        )
        self._connections[profile_id] = conn
        install.last_seen_at = datetime.now(timezone.utc)
        return conn

    def _remove_connection(self, ws: WebSocket) -> ConnectionState | None:
        """Remove and return the connection for the given WebSocket."""
        for profile_id, conn in list(self._connections.items()):
            if conn.websocket is ws:
                del self._connections[profile_id]
                conn.install.last_seen_at = datetime.now(timezone.utc)
                self._fail_pending(conn, "Extension disconnected.")
                return conn
        return None

    @staticmethod
    def _fail_pending(conn: ConnectionState, reason: str) -> None:
        for fut in conn.pending.values():
            if not fut.done():
                fut.set_exception(AppError("BROWSER_EXTENSION_NOT_CONNECTED", reason))
        conn.pending.clear()

    def revoke_connection(self, profile_id: str) -> bool:
        """Revoke a profile's credential and disconnect it."""
        conn = self._connections.get(profile_id)
        if conn is not None:
            conn.install.revoked = True
            self._fail_pending(conn, "Credential revoked.")
            try:
                conn.websocket.close(code=4002, reason="revoked")
            except Exception:
                pass
            del self._connections[profile_id]
        # Also remove from credential store
        for iid, inst in list(self._install_credentials.items()):
            if inst.profile_id == profile_id:
                inst.revoked = True
                break
        return True

    def rename_profile(self, profile_id: str, new_label: str) -> bool:
        """Rename a profile's display label."""
        conn = self._connections.get(profile_id)
        if conn is not None:
            conn.install.profile_label = new_label
            return True
        for inst in self._install_credentials.values():
            if inst.profile_id == profile_id:
                inst.profile_label = new_label
                return True
        return False

    # ------------------------------------------------------------------
    # Connection status and routing
    # ------------------------------------------------------------------
    @property
    def is_connected(self) -> bool:
        """True if at least one connection is active."""
        return len(self._connections) > 0

    def get_status(self) -> dict[str, Any]:
        """Return status of all connections."""
        connections = []
        for profile_id, conn in self._connections.items():
            connections.append({
                "profile_id": profile_id,
                "installation_id": conn.install.installation_id,
                "browser_kind": conn.install.browser_kind,
                "profile_label": conn.install.profile_label,
                "extension_version": conn.install.extension_version,
                "connected": True,
                "connected_at": conn.connected_at.isoformat(),
                "last_seen_at": conn.install.last_seen_at.isoformat() if conn.install.last_seen_at else None,
            })
        return {
            "connected": len(connections) > 0,
            "connection_count": len(connections),
            "connections": connections,
        }

    def get_connections(self) -> list[dict[str, Any]]:
        """List all connections (active + stored credentials)."""
        seen = set()
        result = []
        # Active connections first
        for profile_id, conn in self._connections.items():
            seen.add(profile_id)
            result.append({
                "profile_id": profile_id,
                "installation_id": conn.install.installation_id,
                "browser_kind": conn.install.browser_kind,
                "profile_label": conn.install.profile_label,
                "extension_version": conn.install.extension_version,
                "connected": True,
                "revoked": conn.install.revoked,
                "last_seen_at": conn.install.last_seen_at.isoformat() if conn.install.last_seen_at else None,
            })
        # Stored credentials not currently connected
        for inst in self._install_credentials.values():
            if inst.profile_id not in seen:
                result.append({
                    "profile_id": inst.profile_id,
                    "installation_id": inst.installation_id,
                    "browser_kind": inst.browser_kind,
                    "profile_label": inst.profile_label,
                    "extension_version": inst.extension_version,
                    "connected": False,
                    "revoked": inst.revoked,
                    "last_seen_at": inst.last_seen_at.isoformat() if inst.last_seen_at else None,
                })
        return result

    def _resolve_profile(
        self, browser: str | None = None, profile_id: str | None = None
    ) -> ConnectionState:
        """Resolve which connection to route a command to.

        Rules:
        1. If profile_id specified, use exact match.
        2. If browser specified with exactly one match, use it.
        3. If browser specified with multiple matches, raise ambiguous.
        4. If neither specified with exactly one connection, use it.
        5. Otherwise, raise appropriate error.
        """
        if profile_id:
            conn = self._connections.get(profile_id)
            if conn is None:
                raise AppError(
                    "BROWSER_PROFILE_NOT_CONNECTED",
                    f"Profile '{profile_id}' is not connected. Available: {', '.join(self._connections.keys()) or 'none'}",
                )
            return conn

        if browser:
            matches = [
                c for c in self._connections.values()
                if c.install.browser_kind == browser
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) == 0:
                available = [c.install.browser_kind for c in self._connections.values()]
                raise AppError(
                    "BROWSER_PROFILE_NOT_CONNECTED",
                    f"No connected {browser} profile. Connected browsers: {', '.join(available) or 'none'}.",
                )
            # Multiple matches — ambiguous
            profiles = [f"{m.install.browser_kind}/{m.install.profile_label}" for m in matches]
            raise AppError(
                "BROWSER_PROFILE_AMBIGUOUS",
                f"Multiple {browser} profiles connected: {', '.join(profiles)}. Specify a profile_id.",
            )

        # No browser, no profile_id — use the only connection if exactly one
        conns = list(self._connections.values())
        if len(conns) == 1:
            return conns[0]
        if len(conns) == 0:
            raise AppError(
                "BROWSER_EXTENSION_NOT_CONNECTED",
                "No browser extension is connected. Open Settings → Browseri i kartice to pair one.",
            )
        profiles = [f"{c.install.browser_kind}/{c.install.profile_label}" for c in conns]
        raise AppError(
            "BROWSER_PROFILE_AMBIGUOUS",
            f"Multiple browser profiles connected: {', '.join(profiles)}. Specify which one.",
        )

    # ------------------------------------------------------------------
    # WebSocket handler
    # ------------------------------------------------------------------
    async def handle_ws(self, websocket: WebSocket) -> None:
        await websocket.accept()
        authenticated = False
        active_conn: ConnectionState | None = None

        try:
            async for raw in websocket.iter_text():
                if len(raw) > MAX_MESSAGE_SIZE_BYTES:
                    await websocket.send_text(json.dumps({
                        "type": "auth_failed", "reason": "message too large",
                    }))
                    await websocket.close(code=1009)
                    return

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error", "code": "INVALID_JSON",
                        "message": "Could not parse message as JSON.",
                    }))
                    continue

                msg_type = msg.get("type", "")

                # --- Pairing ---
                if msg_type == "pair":
                    human_code = str(msg.get("code", "")).strip().upper()
                    browser_kind = str(msg.get("browser_kind", "")).strip().lower()
                    installation_id = str(msg.get("installation_id", "")).strip()
                    profile_label = str(msg.get("profile_label", "Default")).strip()
                    extension_version = str(msg.get("extension_version", "1.0.0")).strip()

                    if not human_code or not installation_id or not browser_kind:
                        await websocket.send_text(json.dumps({
                            "type": "pair_failed",
                            "reason": "Missing code, installation_id, or browser_kind.",
                        }))
                        continue

                    install = self._consume_pairing_token(
                        human_code=human_code, browser_kind=browser_kind,
                        installation_id=installation_id, profile_label=profile_label,
                        extension_version=extension_version,
                    )

                    if install is None:
                        await websocket.send_text(json.dumps({
                            "type": "pair_failed",
                            "reason": "Invalid or expired pairing code.",
                        }))
                        continue

                    authenticated = True
                    active_conn = self._register_connection(websocket, install)
                    await websocket.send_text(json.dumps({
                        "type": "paired",
                        "profile_id": install.profile_id,
                        "credential": install.credential,
                        "browser_kind": install.browser_kind,
                        "profile_label": install.profile_label,
                    }))
                    continue

                # --- Auth ---
                if msg_type == "auth":
                    # Per-install credential auth
                    credential = str(msg.get("credential", ""))
                    installation_id = str(msg.get("installation_id", ""))
                    if credential and installation_id:
                        stored = self._install_credentials.get(installation_id)
                        if stored and secrets.compare_digest(stored.credential, credential):
                            if stored.revoked:
                                await websocket.send_text(json.dumps({
                                    "type": "auth_failed", "reason": "credential revoked",
                                }))
                                await websocket.close(code=4002)
                                return
                            authenticated = True
                            active_conn = self._register_connection(websocket, stored)
                            await websocket.send_text(json.dumps({
                                "type": "auth_ok",
                                "profile_id": stored.profile_id,
                                "browser_kind": stored.browser_kind,
                                "profile_label": stored.profile_label,
                            }))
                            continue

                    # Legacy global secret fallback
                    legacy = self._ensure_legacy_secret()
                    provided = str(msg.get("secret", ""))
                    if secrets.compare_digest(legacy, provided):
                        authenticated = True
                        await websocket.send_text(json.dumps({
                            "type": "auth_ok", "legacy": True,
                            "session_id": uuid4().hex[:16],
                        }))
                        continue

                    await websocket.send_text(json.dumps({
                        "type": "auth_failed", "reason": "wrong credential or secret",
                    }))
                    await websocket.close(code=4001)
                    return

                # --- Post-auth: route response to correct connection ---
                if not authenticated:
                    await websocket.send_text(json.dumps({
                        "type": "auth_failed", "reason": "authenticate or pair first",
                    }))
                    continue

                if active_conn is not None:
                    request_id = msg.get("request_id")
                    if request_id and request_id in active_conn.pending:
                        future = active_conn.pending.pop(request_id, None)
                        if future and not future.done():
                            future.set_result(msg)
                    elif msg_type == "pong":
                        request_id = msg.get("request_id")
                        if request_id and request_id in active_conn.pending:
                            future = active_conn.pending.pop(request_id, None)
                            if future and not future.done():
                                future.set_result(msg)

        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            self._remove_connection(websocket)

    # ------------------------------------------------------------------
    # Request/response interface
    # ------------------------------------------------------------------
    async def _send_and_wait(
        self, msg: dict[str, Any], conn: ConnectionState,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        rid = request_id or uuid4().hex[:16]
        msg["request_id"] = rid
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        conn.pending[rid] = future

        try:
            await conn.websocket.send_text(json.dumps(msg))
        except Exception as exc:
            conn.pending.pop(rid, None)
            raise AppError(
                "BROWSER_EXTENSION_NOT_CONNECTED",
                f"Failed to send command to extension: {exc}",
            ) from exc

        try:
            result = await asyncio.wait_for(future, timeout=REPLY_TIMEOUT_SECONDS)
            return result
        except asyncio.TimeoutError:
            conn.pending.pop(rid, None)
            raise AppError("TAB_ACTION_TIMEOUT", f"Extension did not respond within {REPLY_TIMEOUT_SECONDS}s.")

    # ------------------------------------------------------------------
    # High-level commands (called by browser_tabs tool)
    # ------------------------------------------------------------------
    async def list_tabs(
        self, scope: str = "current_window",
        browser: str | None = None, profile_id: str | None = None,
    ) -> dict[str, Any]:
        conn = self._resolve_profile(browser=browser, profile_id=profile_id)
        result = await self._send_and_wait({"type": "list_tabs", "scope": scope}, conn)
        if result.get("type") == "error":
            raise AppError(
                result.get("code", "TAB_LIST_FAILED"),
                result.get("message", "Failed to list tabs."),
            )

        snapshot_id = f"tabsnap_{uuid4().hex[:12]}"
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "browser": conn.install.browser_kind,
            "profile_id": conn.install.profile_id,
            "profile_label": conn.install.profile_label,
            "connection_id": conn.install.profile_id,
            "scope": scope,
            "created_at": datetime.now(timezone.utc),
            "count": result.get("count", 0),
            "tabs": result.get("tabs", []),
        }
        self._snapshots.store(snapshot_id, snapshot_data)

        tabs = result.get("tabs", [])
        window_id = tabs[0].get("window_id") if tabs else None

        return {
            "browser": snapshot_data["browser"],
            "profile_id": snapshot_data["profile_id"],
            "profile_label": snapshot_data["profile_label"],
            "scope": scope,
            "window_id": window_id,
            "snapshot_id": snapshot_id,
            "created_at": snapshot_data["created_at"].isoformat(),
            "count": snapshot_data["count"],
            "tabs": snapshot_data["tabs"],
        }

    async def activate_tab(
        self, snapshot_id: str, position: int,
        browser: str | None = None, profile_id: str | None = None,
    ) -> dict[str, Any]:
        conn = self._resolve_profile(browser=browser, profile_id=profile_id)
        # Snapshot must be from the SAME profile
        snap = self._snapshots.get(snapshot_id, profile_id=conn.install.profile_id)
        if snap is None:
            # Could be stale, or from different profile
            # Try without profile binding to distinguish
            generic = self._snapshots.get(snapshot_id)
            if generic is not None:
                raise AppError(
                    "TAB_PROFILE_MISMATCH",
                    "This snapshot belongs to a different browser profile. Please list tabs again for this profile.",
                )
            raise AppError(
                "TAB_SNAPSHOT_STALE",
                "The tab list snapshot has expired. Please list tabs again.",
            )

        tabs = snap.get("tabs", [])
        if position < 1 or position > len(tabs):
            raise AppError(
                "TAB_POSITION_OUT_OF_RANGE",
                f"Position {position} is out of range (1–{len(tabs)})."
            )

        tab = tabs[position - 1]
        if tab.get("incognito"):
            raise AppError("INCOGNITO_NOT_ALLOWED", "Incognito tabs are excluded by default.")

        result = await self._send_and_wait({
            "type": "activate_tab",
            "tab_id": tab["tab_id"],
            "window_id": tab["window_id"],
        }, conn)

        if result.get("type") == "error":
            error_msg = result.get("message", "")
            if any(kw in error_msg.lower() for kw in ("no tab with id", "no window with id", "not found")):
                raise AppError(
                    "TAB_SNAPSHOT_STALE",
                    f"Tab at position {position} no longer exists. Please list tabs again."
                )
            raise AppError(
                result.get("code", "TAB_ACTION_FAILED"),
                result.get("message", "Failed to activate tab."),
            )

        return {
            "ok": True,
            "browser": conn.install.browser_kind,
            "profile_id": conn.install.profile_id,
            "profile_label": conn.install.profile_label,
            "snapshot_id": snapshot_id,
            "position": position,
            "tab_id": tab["tab_id"],
            "title": tab.get("title", ""),
            "url": tab.get("url", ""),
        }

    async def close_tab(
        self, snapshot_id: str, position: int,
        browser: str | None = None, profile_id: str | None = None,
    ) -> dict[str, Any]:
        conn = self._resolve_profile(browser=browser, profile_id=profile_id)
        snap = self._snapshots.get(snapshot_id, profile_id=conn.install.profile_id)
        if snap is None:
            generic = self._snapshots.get(snapshot_id)
            if generic is not None:
                raise AppError(
                    "TAB_PROFILE_MISMATCH",
                    "This snapshot belongs to a different browser profile. Please list tabs again.",
                )
            raise AppError(
                "TAB_SNAPSHOT_STALE",
                "The tab list snapshot has expired. Please list tabs again.",
            )

        tabs = snap.get("tabs", [])
        if position < 1 or position > len(tabs):
            raise AppError(
                "TAB_POSITION_OUT_OF_RANGE",
                f"Position {position} is out of range (1–{len(tabs)})."
            )

        tab = tabs[position - 1]
        if tab.get("incognito"):
            raise AppError("INCOGNITO_NOT_ALLOWED", "Incognito tabs are excluded by default.")

        result = await self._send_and_wait({
            "type": "close_tab",
            "tab_id": tab["tab_id"],
        }, conn)

        if result.get("type") == "error":
            error_msg = result.get("message", "")
            if any(kw in error_msg.lower() for kw in ("no tab with id", "not found")):
                raise AppError(
                    "TAB_SNAPSHOT_STALE",
                    f"Tab at position {position} was already closed. Please list tabs again."
                )
            raise AppError(
                result.get("code", "TAB_ACTION_FAILED"),
                result.get("message", "Failed to close tab."),
            )

        return {
            "ok": True,
            "browser": conn.install.browser_kind,
            "profile_id": conn.install.profile_id,
            "profile_label": conn.install.profile_label,
            "snapshot_id": snapshot_id,
            "position": position,
            "tab_id": tab["tab_id"],
            "title": tab.get("title", ""),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _generate_human_code(existing: dict[str, str]) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(HUMAN_CODE_LENGTH))
        if code not in existing:
            return code
    return secrets.token_hex(3).upper()[:HUMAN_CODE_LENGTH]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_broker: BrowserExtensionBroker | None = None


def get_broker() -> BrowserExtensionBroker:
    global _broker
    if _broker is None:
        raise RuntimeError("BrowserExtensionBroker not initialized.")
    return _broker


def init_broker(data_dir: Path) -> BrowserExtensionBroker:
    global _broker
    _broker = BrowserExtensionBroker(data_dir)
    _broker._ensure_legacy_secret()
    return _broker