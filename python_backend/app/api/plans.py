"""REST endpoints for plans/proposals (FAZA 9).

CRUD + status transitions for plans and their steps, stored in SQLite.
"""
from fastapi import APIRouter, Path, Request

from app.core.errors import AppError
from app.schemas.plan import (
    PlanCreateRequest,
    PlanListResponse,
    PlanResponse,
    PlanStepUpdateRequest,
    PlanUpdateRequest,
)
from app.services.plan_service import PlanService

router = APIRouter(tags=["plans"])


def _service(request: Request) -> PlanService:
    service = getattr(request.app.state, "plan_service", None)
    if service is None:
        raise AppError("PLANS_UNAVAILABLE", "Plan service is not initialized.", status_code=500)
    return service


@router.get("/plans", response_model=PlanListResponse)
def list_plans(request: Request, limit: int = 50) -> PlanListResponse:
    items = _service(request).list(limit=limit)
    return PlanListResponse(plans=[PlanResponse(**item) for item in items])


@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(request_body: PlanCreateRequest, request: Request) -> PlanResponse:
    steps = [step.model_dump(mode="json") for step in request_body.steps]
    data = _service(request).create(
        title=request_body.title,
        summary=request_body.summary,
        steps=steps,
    )
    return PlanResponse(**data)


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(
    request: Request,
    plan_id: str = Path(..., min_length=1),
) -> PlanResponse:
    data = _service(request).get(plan_id)
    if data is None:
        raise AppError("PLAN_NOT_FOUND", f"Plan '{plan_id}' not found.", status_code=404)
    return PlanResponse(**data)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    request_body: PlanUpdateRequest,
    request: Request,
    plan_id: str = Path(..., min_length=1),
) -> PlanResponse:
    data = _service(request).update(
        plan_id,
        title=request_body.title,
        summary=request_body.summary,
        status=request_body.status,
    )
    if data is None:
        raise AppError("PLAN_NOT_FOUND", f"Plan '{plan_id}' not found.", status_code=404)
    return PlanResponse(**data)


@router.patch("/plans/{plan_id}/steps/{step_id}", response_model=PlanResponse)
def update_plan_step(
    request_body: PlanStepUpdateRequest,
    request: Request,
    plan_id: str = Path(..., min_length=1),
    step_id: str = Path(..., min_length=1),
) -> PlanResponse:
    data = _service(request).update_step(
        plan_id,
        step_id,
        status=request_body.status,
        title=request_body.title,
        details=request_body.details,
    )
    if data is None:
        raise AppError(
            "PLAN_STEP_NOT_FOUND",
            f"Step '{step_id}' of plan '{plan_id}' not found.",
            status_code=404,
        )
    return PlanResponse(**data)
