from typing import Any

from pydantic import BaseModel, Field


class RealtimeSessionRequest(BaseModel):
    session: dict[str, Any] = Field(default_factory=dict)


class RealtimeSessionResponse(BaseModel):
    value: str
    expiresAt: int | None = None
