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
    # RTM-4: authoritative model koji je backend stvarno odabrao (source of
    # truth) — desktop ga koristi za WebSocket URL + session.update. Nikad
    # permanentni API ključ.
    model: str
