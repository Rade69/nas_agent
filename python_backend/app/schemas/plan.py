from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PlanStatus = Literal["draft", "proposed", "approved", "running", "completed", "rejected", "cancelled"]
PlanStepStatus = Literal["pending", "in_progress", "completed", "skipped", "failed"]


class PlanStepCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    details: dict[str, Any] = Field(default_factory=dict)


class PlanStepUpdateRequest(BaseModel):
    status: PlanStepStatus | None = None
    title: str | None = None
    details: dict[str, Any] | None = None


class PlanStepResponse(BaseModel):
    id: str
    plan_id: str
    step_index: int
    title: str
    status: PlanStepStatus
    details: dict[str, Any]


class PlanCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    summary: str | None = None
    steps: list[PlanStepCreateRequest] = Field(default_factory=list)


class PlanUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    status: PlanStatus | None = None


class PlanResponse(BaseModel):
    id: str
    title: str
    status: PlanStatus
    created_at: str
    updated_at: str
    summary: str | None = None
    steps: list[PlanStepResponse] = Field(default_factory=list)


class PlanListResponse(BaseModel):
    plans: list[PlanResponse]
