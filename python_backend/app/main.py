from fastapi import FastAPI

from app.agent.cancellation import CancellationRegistry
from app.agent.tool_registry import create_default_registry
from app.api.confirmations import router as confirmations_router
from app.api.health import router as health_router
from app.api.plans import router as plans_router
from app.api.realtime import router as realtime_router
from app.api.tools import router as tools_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.services.action_log import ActionLogService
from app.services.confirmation_service import ConfirmationService
from app.services.plan_service import PlanService
from app.storage.db import initialize_database
from app.storage.repositories.confirmation_repo import ConfirmationRepository
from app.storage.repositories.plan_repo import PlanRepository
from app.storage.repositories.tool_run_repo import ToolRunRepository


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    initialize_database(settings)

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.tool_registry = create_default_registry()
    app.state.action_log = ActionLogService(ToolRunRepository(settings.database_path))
    # FAZA 9: confirmations + plans storage. The permission/risk layer that issues
    # confirmations from tool execution is FAZA 10; here we only expose storage +
    # state machine transitions so the UI/API can already propose/approve plans
    # and manual confirmations. See docs/MIGRATION_PLAN.md and
    # docs/ARCHITECTURE_VOICE_FIRST_REVISED.md "Voice confirmations".
    app.state.confirmation_service = ConfirmationService(ConfirmationRepository(settings.database_path))
    app.state.plan_service = PlanService(PlanRepository(settings.database_path))
    # FAZA 10: permission/risk layer. Cancellation registry is process-lifetime
    # in-memory state (see app/agent/cancellation.py); the durable audit trail
    # stays in tool_runs via ActionLogService.
    app.state.cancellation_registry = CancellationRegistry()

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(tools_router)
    app.include_router(realtime_router)
    app.include_router(confirmations_router)
    app.include_router(plans_router)
    return app


app = create_app()