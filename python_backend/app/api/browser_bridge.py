"""REST endpoints for the browser extension bridge (C1: multi-connection).

GET    /browser-bridge/status                        — connection summary
GET    /browser-bridge/connections                   — list all connections
POST   /browser-bridge/pairing-sessions              — create pairing token
GET    /browser-bridge/pairing-sessions/{id}         — pairing status
DELETE /browser-bridge/pairing-sessions/{id}         — cancel pairing
POST   /browser-bridge/connections/{profile_id}/revoke — revoke credential
PATCH  /browser-bridge/connections/{profile_id}       — rename profile
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.errors import AppError
from app.services.browser_extension_broker import get_broker
from app.services.chromium_discovery import discover_browsers, normalize_browser

router = APIRouter(tags=["browser-bridge"])


# --- Schemas ---
class ConnectionEntry(BaseModel):
    profile_id: str
    installation_id: str
    browser_kind: str
    profile_label: str
    extension_version: str
    connected: bool
    revoked: bool
    last_seen_at: str | None = None


class BridgeStatusResponse(BaseModel):
    connected: bool
    connection_count: int
    connections: list[ConnectionEntry]


class ConnectionsListResponse(BaseModel):
    connections: list[ConnectionEntry]


class PairingSessionRequest(BaseModel):
    browser_kind: str


class PairingSessionResponse(BaseModel):
    pairing_id: str
    human_code: str
    expires_in_seconds: int


class PairingSessionStatus(BaseModel):
    pairing_id: str
    human_code: str
    browser_kind: str
    status: str
    expires_in_seconds: int


class RenameProfileRequest(BaseModel):
    profile_label: str


class BrowserInfo(BaseModel):
    browser_kind: str
    display_name: str
    installed: bool
    profile_dirs: list[str]


class BrowsersListResponse(BaseModel):
    browsers: list[BrowserInfo]


# --- Endpoints ---


@router.get("/browser-bridge/status", response_model=BridgeStatusResponse)
def get_bridge_status(request: Request) -> BridgeStatusResponse:
    broker = get_broker()
    status = broker.get_status()
    return BridgeStatusResponse(
        connected=status["connected"],
        connection_count=status["connection_count"],
        connections=[ConnectionEntry(**c) for c in status["connections"]],
    )


@router.get("/browser-bridge/connections", response_model=ConnectionsListResponse)
def list_connections(request: Request) -> ConnectionsListResponse:
    broker = get_broker()
    return ConnectionsListResponse(
        connections=[ConnectionEntry(**c) for c in broker.get_connections()],
    )


@router.post("/browser-bridge/pairing-sessions", response_model=PairingSessionResponse)
def create_pairing_session(
    request_body: PairingSessionRequest, request: Request,
) -> PairingSessionResponse:
    broker = get_broker()
    allowed = {"brave", "chrome", "edge", "vivaldi", "opera", "opera_gx", "chromium"}
    browser_kind = request_body.browser_kind.strip().lower()
    if browser_kind not in allowed:
        raise AppError(
            "BROWSER_NOT_SUPPORTED",
            f"Browser '{browser_kind}' is not supported.",
            status_code=400,
        )
    result = broker.create_pairing_session(browser_kind)
    return PairingSessionResponse(**result)


@router.get("/browser-bridge/pairing-sessions/{pairing_id}", response_model=PairingSessionStatus)
def get_pairing_session(pairing_id: str, request: Request) -> PairingSessionStatus:
    broker = get_broker()
    session = broker.get_pairing_session(pairing_id)
    if session is None:
        raise AppError("PAIRING_SESSION_NOT_FOUND", "Not found or expired.", status_code=404)
    return PairingSessionStatus(**session)


@router.delete("/browser-bridge/pairing-sessions/{pairing_id}")
def cancel_pairing_session(pairing_id: str, request: Request) -> dict:
    broker = get_broker()
    if broker.cancel_pairing_session(pairing_id):
        return {"ok": True}
    raise AppError("PAIRING_SESSION_NOT_FOUND", "Not found or already consumed.", status_code=404)


@router.get("/browser-bridge/browsers", response_model=BrowsersListResponse)
def list_browsers(request: Request) -> BrowsersListResponse:
    discovered = discover_browsers()
    return BrowsersListResponse(
        browsers=[BrowserInfo(**b) for b in discovered],
    )
def revoke_connection(profile_id: str, request: Request) -> dict:
    broker = get_broker()
    if broker.revoke_connection(profile_id):
        return {"ok": True}
    raise AppError("PROFILE_NOT_FOUND", f"Profile '{profile_id}' not found.", status_code=404)


@router.patch("/browser-bridge/connections/{profile_id}")
def rename_connection(
    profile_id: str, request_body: RenameProfileRequest, request: Request,
) -> dict:
    broker = get_broker()
    label = request_body.profile_label.strip()
    if not label:
        raise AppError("INVALID_ARGUMENTS", "profile_label must not be empty.", status_code=400)
    if broker.rename_profile(profile_id, label):
        return {"ok": True}
    raise AppError("PROFILE_NOT_FOUND", f"Profile '{profile_id}' not found.", status_code=404)