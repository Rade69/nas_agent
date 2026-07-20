"""REST endpoints for thumbnail reference images (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md). Electron-only callers: POST is
invoked right after a native file-picker selection; GET .../resolve is
invoked internally by thumbnail_generate/thumbnail_edit to read the actual
file. Neither is a model-facing tool.
"""
from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.thumbnail import (
    ThumbnailBoardResponse,
    ThumbnailBoardViewResponse,
    ThumbnailEditRequest,
    ThumbnailGenerateRequest,
    ThumbnailGridRequest,
    ThumbnailLoadingPrepareRequest,
    ThumbnailReferenceCreateRequest,
    ThumbnailReferenceResolveResponse,
    ThumbnailReferenceResponse,
    ThumbnailSelectRequest,
)
from app.services.thumbnail_board_service import ThumbnailBoardService
from app.services.thumbnail_reference_service import ThumbnailReferenceService

router = APIRouter(tags=["thumbnails"])


def _reference_service(request: Request) -> ThumbnailReferenceService:
    service = getattr(request.app.state, "thumbnail_reference_service", None)
    if service is None:
        raise AppError(
            "THUMBNAIL_REFERENCE_SERVICE_UNAVAILABLE",
            "Thumbnail reference service is not initialized.",
            status_code=500,
        )
    return service


def _board_service(request: Request) -> ThumbnailBoardService:
    service = getattr(request.app.state, "thumbnail_board_service", None)
    if service is None:
        raise AppError(
            "THUMBNAIL_BOARD_SERVICE_UNAVAILABLE",
            "Thumbnail board service is not initialized.",
            status_code=500,
        )
    return service


@router.post("/thumbnail-references", response_model=ThumbnailReferenceResponse)
def add_thumbnail_reference(request: Request, body: ThumbnailReferenceCreateRequest) -> ThumbnailReferenceResponse:
    result = _reference_service(request).add(body.path, body.label)
    return ThumbnailReferenceResponse(**result)


@router.get("/thumbnail-references/{reference_id}/resolve", response_model=ThumbnailReferenceResolveResponse)
def resolve_thumbnail_reference(request: Request, reference_id: str) -> ThumbnailReferenceResolveResponse:
    resolved = _reference_service(request).resolve(reference_id)
    if resolved is None:
        raise AppError(
            "THUMBNAIL_REFERENCE_NOT_FOUND",
            f"Thumbnail reference '{reference_id}' was not found or is no longer valid.",
            status_code=404,
        )
    return ThumbnailReferenceResolveResponse(canonical_path=str(resolved))


# ------------------------------------------------------------------ #
# QM-6T1: Thumbnail board REST API
# ------------------------------------------------------------------ #


@router.get("/thumbnails/board", response_model=ThumbnailBoardViewResponse)
def get_thumbnail_board(request: Request) -> ThumbnailBoardViewResponse:
    """Return current board state and artifact."""
    svc = _board_service(request)
    return ThumbnailBoardViewResponse(
        ok=True,
        board=svc.summary(),
        artifact=svc._build_artifact(),
    )


@router.post("/thumbnails/loading", response_model=ThumbnailBoardResponse)
def post_thumbnail_loading(request: Request, body: ThumbnailLoadingPrepareRequest) -> ThumbnailBoardResponse:
    """Create a loading placeholder."""
    svc = _board_service(request)
    result = svc.loading_prepare(
        prompt=body.prompt,
        mode=body.mode,
        number=body.number,
        target_id=body.target_id,
    )
    return ThumbnailBoardResponse(**result)


@router.post("/thumbnails/generate", response_model=ThumbnailBoardResponse)
def post_thumbnail_generate(request: Request, body: ThumbnailGenerateRequest) -> ThumbnailBoardResponse:
    """Record a generated thumbnail as ready."""
    svc = _board_service(request)
    result = svc.generate(
        prompt=body.prompt,
        run_id=body.run_id,
        references=body.references,
    )
    return ThumbnailBoardResponse(**result)


@router.post("/thumbnails/edit", response_model=ThumbnailBoardResponse)
def post_thumbnail_edit(request: Request, body: ThumbnailEditRequest) -> ThumbnailBoardResponse:
    """Edit an existing thumbnail (creates new record with parent_id)."""
    svc = _board_service(request)
    result = svc.edit(
        prompt=body.prompt,
        number=body.number,
        target_id=body.target_id,
        run_id=body.run_id,
        references=body.references,
    )
    return ThumbnailBoardResponse(**result)


@router.post("/thumbnails/select", response_model=ThumbnailBoardResponse)
def post_thumbnail_select(request: Request, body: ThumbnailSelectRequest) -> ThumbnailBoardResponse:
    """Select a thumbnail by permanent number."""
    svc = _board_service(request)
    result = svc.select(number=body.number)
    return ThumbnailBoardResponse(**result)


@router.post("/thumbnails/grid", response_model=ThumbnailBoardResponse)
def post_thumbnail_grid(request: Request, body: ThumbnailGridRequest) -> ThumbnailBoardResponse:
    """Show a paginated page of the thumbnail board."""
    svc = _board_service(request)
    result = svc.grid(page=body.page)
    return ThumbnailBoardResponse(**result)


@router.post("/thumbnails/clear-loading", response_model=ThumbnailBoardViewResponse)
def post_thumbnail_clear_loading(request: Request) -> ThumbnailBoardViewResponse:
    """Clear any leftover loading placeholders (startup cleanup)."""
    svc = _board_service(request)
    svc.clear_startup_loading()
    return ThumbnailBoardViewResponse(
        ok=True,
        board=svc.summary(),
        artifact=svc._build_artifact(),
    )


@router.get("/thumbnails/instructions")
def get_thumbnail_instructions(request: Request) -> dict:
    """Return thumbnail board state as Markdown instructions for the Realtime
    prompt (parity with legacyMedia.cjs buildThumbnailBoardInstructions)."""
    svc = _board_service(request)
    return {"ok": True, "instructions": svc.get_instructions()}
