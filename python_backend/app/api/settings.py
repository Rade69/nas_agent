"""REST endpoints for user-facing preferences (display name, interface
language). Generic by design — any new field added to UserSettings is
automatically served without changes here (reads model_fields).
"""
from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.settings import UserSettings, UserSettingsUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter(tags=["settings"])


def _service(request: Request) -> SettingsService:
    service = getattr(request.app.state, "user_settings_service", None)
    if service is None:
        raise AppError("SETTINGS_UNAVAILABLE", "Settings service is not initialized.", status_code=500)
    return service


@router.get("/settings", response_model=UserSettings)
def get_settings(request: Request) -> UserSettings:
    return _service(request).get()


@router.patch("/settings", response_model=UserSettings)
def update_settings(request_body: UserSettingsUpdateRequest, request: Request) -> UserSettings:
    return _service(request).update(**request_body.model_dump(exclude_unset=True))
