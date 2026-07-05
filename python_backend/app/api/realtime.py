import hashlib

import httpx
from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.realtime import RealtimeSessionRequest, RealtimeSessionResponse

router = APIRouter(tags=["realtime"])

OPENAI_REALTIME_URL = "https://api.openai.com/v1/realtime/client_secrets"
# Matches the identifier previously sent from electron/main.cjs's realtime:create-token handler.
SAFETY_IDENTIFIER = hashlib.sha256(b"riley-local-ricky").hexdigest()


@router.post("/realtime/session", response_model=RealtimeSessionResponse)
def create_realtime_session(
    request_body: RealtimeSessionRequest,
    request: Request,
) -> RealtimeSessionResponse:
    settings = request.app.state.settings
    if not settings.openai_api_key:
        raise AppError(
            "MISSING_API_KEY",
            "OPENAI_API_KEY is not configured on the Python backend.",
            status_code=500,
        )

    try:
        response = httpx.post(
            OPENAI_REALTIME_URL,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
                "OpenAI-Safety-Identifier": SAFETY_IDENTIFIER,
            },
            json={"session": request_body.session},
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        raise AppError(
            "REALTIME_REQUEST_FAILED",
            f"Realtime token request failed: {exc}",
            status_code=502,
        ) from exc

    if response.status_code >= 400:
        raise AppError(
            "REALTIME_REQUEST_FAILED",
            f"Realtime token request failed: {response.status_code} {response.text}",
            status_code=502,
        )

    data = response.json()
    value = data.get("value") or (data.get("client_secret") or {}).get("value")
    if not value:
        raise AppError(
            "REALTIME_RESPONSE_INVALID",
            "Realtime token response did not include a client secret value.",
            status_code=502,
        )

    expires_at = data.get("expires_at") or (data.get("client_secret") or {}).get("expires_at")
    return RealtimeSessionResponse(value=value, expiresAt=expires_at)
