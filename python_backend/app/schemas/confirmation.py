from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.tool import RiskLevel

ConfirmationStatus = Literal["pending", "approved", "rejected", "expired", "cancelled"]


class ConfirmationCreateRequest(BaseModel):
    action_name: str = Field(..., min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = "medium"
    plan_id: str | None = None
    summary: str | None = None


class ConfirmationResponse(BaseModel):
    id: str
    status: ConfirmationStatus
    action_name: str
    payload: dict[str, Any]
    risk_level: RiskLevel
    plan_id: str | None = None
    summary: str | None = None
    created_at: str
    resolved_at: str | None = None


class ConfirmationListResponse(BaseModel):
    confirmations: list[ConfirmationResponse]


class ConfirmationDecisionResponse(BaseModel):
    ok: bool = True
    confirmation: ConfirmationResponse
