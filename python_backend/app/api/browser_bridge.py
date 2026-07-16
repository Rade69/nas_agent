"""REST endpoint for the browser extension bridge status (PR 1: browser_tabs).

Returns connection state, pairing secret display fragment, and broker URL
so the Settings panel can show the pairing code.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.services.browser_extension_broker import get_broker

router = APIRouter(tags=["browser-bridge"])


class BrowserBridgeStatus(BaseModel):
    connected: bool
    pairing_display: str  # first 8 chars + "…"
    broker_url: str


@router.get("/browser-bridge/status", response_model=BrowserBridgeStatus)
def get_bridge_status(request: Request) -> BrowserBridgeStatus:
    broker = get_broker()
    return BrowserBridgeStatus(
        connected=broker.is_connected,
        pairing_display=broker.get_pairing_display(),
        broker_url="ws://127.0.0.1:9119",
    )