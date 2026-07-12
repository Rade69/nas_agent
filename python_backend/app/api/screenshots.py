from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.screenshot import ScreenshotDeleteAllResponse, ScreenshotListResponse
from app.services.screenshot_service import ScreenshotService

router = APIRouter(tags=["screenshots"])


def _service(request: Request) -> ScreenshotService:
    service = getattr(request.app.state, "screenshot_service", None)
    if service is None:
        raise AppError("SCREENSHOT_SERVICE_UNAVAILABLE", "Screenshot service is not initialized.", status_code=500)
    return service


@router.get("/screenshots", response_model=ScreenshotListResponse)
def list_screenshots(request: Request) -> ScreenshotListResponse:
    # list() also runs retention cleanup as a side effect (lazy, on-read) —
    # see ScreenshotService.cleanup_expired() for why.
    return ScreenshotListResponse(screenshots=_service(request).list())


@router.delete("/screenshots", response_model=ScreenshotDeleteAllResponse)
def delete_all_screenshots(request: Request) -> ScreenshotDeleteAllResponse:
    deleted_count = _service(request).delete_all()
    return ScreenshotDeleteAllResponse(ok=True, deletedCount=deleted_count)
