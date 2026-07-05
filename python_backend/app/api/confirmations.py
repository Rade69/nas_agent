from fastapi import APIRouter, Query, Request

from app.core.errors import AppError
from app.schemas.confirmation import (
    ConfirmationCreateRequest,
    ConfirmationDecisionResponse,
    ConfirmationListResponse,
    ConfirmationResponse,
)
from app.services.confirmation_service import ConfirmationService

router = APIRouter(tags=["confirmations"])


def _service(request: Request) -> ConfirmationService:
    service = getattr(request.app.state, "confirmation_service", None)
    if service is None:
        raise AppError("CONFIRMATIONS_UNAVAILABLE", "Confirmation service is not initialized.", status_code=500)
    return service


@router.post("/confirmations", response_model=ConfirmationResponse)
def create_confirmation(
    request_body: ConfirmationCreateRequest,
    request: Request,
) -> ConfirmationResponse:
    data = _service(request).propose(
        action_name=request_body.action_name,
        payload=request_body.payload,
        risk_level=request_body.risk_level,
        plan_id=request_body.plan_id,
        summary=request_body.summary,
        tool_name=request_body.tool_name,
        ttl_seconds=request_body.ttl_seconds,
    )
    return ConfirmationResponse(**data)


@router.get("/confirmations", response_model=ConfirmationListResponse)
def list_confirmations(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> ConfirmationListResponse:
    items = _service(request).list(status=status, limit=limit)
    return ConfirmationListResponse(
        confirmations=[ConfirmationResponse(**item) for item in items]
    )


@router.get("/confirmations/pending", response_model=ConfirmationListResponse)
def list_pending_confirmations(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> ConfirmationListResponse:
    items = _service(request).list_pending(limit=limit)
    return ConfirmationListResponse(
        confirmations=[ConfirmationResponse(**item) for item in items]
    )


@router.post("/confirmations/{confirmation_id}/approve", response_model=ConfirmationDecisionResponse)
def approve_confirmation(confirmation_id: str, request: Request) -> ConfirmationDecisionResponse:
    result = _service(request).approve(confirmation_id)
    if result is None:
        raise AppError("CONFIRMATION_NOT_FOUND", f"Confirmation '{confirmation_id}' not found.", status_code=404)
    return ConfirmationDecisionResponse(confirmation=ConfirmationResponse(**result))


@router.post("/confirmations/{confirmation_id}/reject", response_model=ConfirmationDecisionResponse)
def reject_confirmation(confirmation_id: str, request: Request) -> ConfirmationDecisionResponse:
    result = _service(request).reject(confirmation_id)
    if result is None:
        raise AppError("CONFIRMATION_NOT_FOUND", f"Confirmation '{confirmation_id}' not found.", status_code=404)
    return ConfirmationDecisionResponse(confirmation=ConfirmationResponse(**result))


@router.delete("/confirmations/{confirmation_id}", response_model=ConfirmationDecisionResponse)
def cancel_confirmation(confirmation_id: str, request: Request) -> ConfirmationDecisionResponse:
    result = _service(request).cancel(confirmation_id)
    if result is None:
        raise AppError("CONFIRMATION_NOT_FOUND", f"Confirmation '{confirmation_id}' not found.", status_code=404)
    return ConfirmationDecisionResponse(confirmation=ConfirmationResponse(**result))
