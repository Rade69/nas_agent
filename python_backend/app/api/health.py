"""GET /health — liveness check for the Electron process manager.

Used by electron/services/pythonProcess.cjs to wait for the backend
before opening the main window.
"""
from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(ok=True)
