from fastapi import FastAPI

from app.agent.tool_registry import create_default_registry
from app.api.health import router as health_router
from app.api.realtime import router as realtime_router
from app.api.tools import router as tools_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.services.action_log import ActionLogService
from app.storage.db import initialize_database
from app.storage.repositories.tool_run_repo import ToolRunRepository


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    initialize_database(settings)

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.tool_registry = create_default_registry()
    app.state.action_log = ActionLogService(ToolRunRepository(settings.database_path))

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(tools_router)
    app.include_router(realtime_router)
    return app


app = create_app()