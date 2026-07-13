"""REST endpoints for thumbnail reference images (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md). Electron-only callers: POST is
invoked right after a native file-picker selection; GET .../resolve is
invoked internally by thumbnail_generate/thumbnail_edit to read the actual
file. Neither is a model-facing tool.
"""
from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.thumbnail import (
    ThumbnailReferenceCreateRequest,
    ThumbnailReferenceResolveResponse,
    ThumbnailReferenceResponse,
)
from app.services.thumbnail_reference_service import ThumbnailReferenceService

router = APIRouter(tags=["thumbnails"])


def _service(request: Request) -> ThumbnailReferenceService:
    service = getattr(request.app.state, "thumbnail_reference_service", None)
    if service is None:
        raise AppError(
            "THUMBNAIL_REFERENCE_SERVICE_UNAVAILABLE",
            "Thumbnail reference service is not initialized.",
            status_code=500,
        )
    return service


@router.post("/thumbnail-references", response_model=ThumbnailReferenceResponse)
def add_thumbnail_reference(request: Request, body: ThumbnailReferenceCreateRequest) -> ThumbnailReferenceResponse:
    result = _service(request).add(body.path, body.label)
    return ThumbnailReferenceResponse(**result)


@router.get("/thumbnail-references/{reference_id}/resolve", response_model=ThumbnailReferenceResolveResponse)
def resolve_thumbnail_reference(request: Request, reference_id: str) -> ThumbnailReferenceResolveResponse:
    resolved = _service(request).resolve(reference_id)
    if resolved is None:
        raise AppError(
            "THUMBNAIL_REFERENCE_NOT_FOUND",
            f"Thumbnail reference '{reference_id}' was not found or is no longer valid.",
            status_code=404,
        )
    return ThumbnailReferenceResolveResponse(canonical_path=str(resolved))
