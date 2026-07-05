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
    # FAZA 10: bind this confirmation to a specific tool call so it can't be
    # replayed against a different tool or a modified payload (see
    # SECURITY_HARDENING_PLAN.md section 25.3 / TOOL_CONTRACTS.md). Optional
    # because confirmations can still be proposed for non-tool actions.
    tool_name: str | None = None
    ttl_seconds: int = Field(default=300, ge=1, le=3600)


class ConfirmationResponse(BaseModel):
    id: str
    status: ConfirmationStatus
    action_name: str
    payload: dict[str, Any]
    risk_level: RiskLevel
    plan_id: str | None = None
    summary: str | None = None
    tool_name: str | None = None
    payload_hash: str | None = None
    expires_at: str | None = None
    created_at: str
    resolved_at: str | None = None


class ConfirmationListResponse(BaseModel):
    confirmations: list[ConfirmationResponse]


class ConfirmationDecisionResponse(BaseModel):
    ok: bool = True
    confirmation: ConfirmationResponse
