"""Pydantic models for the Realtime session endpoint (FAZA 6).

Request/response shapes for POST /realtime/session.
"""
from typing import Any

from pydantic import BaseModel, Field


class RealtimeSessionRequest(BaseModel):
    session: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionResponse(BaseModel):
    value: str
    expiresAt: int | None = None
