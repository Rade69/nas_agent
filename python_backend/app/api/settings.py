"""REST endpoints for user-facing preferences (display name, interface
language). Generic by design — any new field added to UserSettings is
automatically served without changes here (reads model_fields).
"""
from fastapi import APIRouter, Request

from app.core.config import resolve_effective_realtime_model
from app.core.errors import AppError
from app.schemas.settings import UserSettings, UserSettingsUpdateRequest
from app.services.settings_service import SettingsService

router = APIRouter(tags=["settings"])


def _service(request: Request) -> SettingsService:
    service = getattr(request.app.state, "user_settings_service", None)
    if service is None:
        raise AppError("SETTINGS_UNAVAILABLE", "Settings service is not initialized.", status_code=500)
    return service


def _resolve_effective(request: Request, settings: UserSettings) -> UserSettings:
    # In-app selector: GET vraća efektivni realtime_model (korisnički izbor,
    # inače env fallback → default) da UI prikaže stvarnu vrijednost nove voice
    # sesije. Invalid persisted value (npr. stara zagađena baza) NE smije
    # srušiti read-only GET /settings — fallback na env/default.
    env_model = request.app.state.settings.openai_realtime_model
    try:
        settings.realtime_model = resolve_effective_realtime_model(
            settings.realtime_model, env_model
        )
    except ValueError:
        settings.realtime_model = env_model
    return settings


@router.get("/settings", response_model=UserSettings)
def get_settings(request: Request) -> UserSettings:
    return _resolve_effective(request, _service(request).get())


@router.patch("/settings", response_model=UserSettings)
def update_settings(request_body: UserSettingsUpdateRequest, request: Request) -> UserSettings:
    return _resolve_effective(
        request, _service(request).update(**request_body.model_dump(exclude_unset=True))
    )
