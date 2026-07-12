from fastapi import Depends, FastAPI

from app.agent.cancellation import CancellationRegistry
from app.agent.conversation_state import ConversationStateService
from app.agent.model_client import OpenAIModelClient
from app.agent.runtime import LocalDesktopAssistant
from app.agent.tool_executor import ToolExecutor
from app.agent.tool_registry import create_default_registry
from app.api.agent import router as agent_router
from app.api.confirmations import router as confirmations_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.plans import router as plans_router
from app.api.realtime import router as realtime_router
from app.api.screenshots import router as screenshots_router
from app.api.security import router as security_router
from app.api.settings import router as settings_router
from app.api.text import router as text_router
from app.api.tools import router as tools_router
from app.core.auth import require_local_token
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.services.action_log import ActionLogService
from app.services.artifact_service import ArtifactService
from app.services.confirmation_service import ConfirmationService
from app.services.event_bus import EventBus
from app.services.exa_client import ExaClient
from app.services.notes_service import NotesService
from app.services.openai_image_client import OpenAIImageClient
from app.services.plan_service import PlanService
from app.services.records_service import RecordsService
from app.services.screenshot_service import ScreenshotService
from app.services.settings_service import SettingsService
from app.storage.db import initialize_database
from app.storage.repositories.agent_repo import AgentConversationRepository
from app.storage.repositories.artifact_repo import ArtifactRepository
from app.storage.repositories.confirmation_repo import ConfirmationRepository
from app.storage.repositories.event_repo import EventRepository
from app.storage.repositories.notes_repo import NotesRepository
from app.storage.repositories.plan_repo import PlanRepository
from app.storage.repositories.records_repo import RecordsRepository
from app.storage.repositories.screenshot_repo import ScreenshotRepository
from app.storage.repositories.settings_repo import SettingsRepository
from app.storage.repositories.tool_run_repo import ToolRunRepository


def create_app() -> FastAPI:
    settings = get_settings()
    # Security Gate 0 (SECURITY_HARDENING_PLAN.md section 14 "Redaction"):
    # configure logging with the real secrets this process holds so they
    # never appear verbatim in log output.
    configure_logging(secrets=[settings.openai_api_key, settings.local_token, settings.exa_api_key])
    initialize_database(settings)

    # Security PR-1: local session token enforced on every route (fails open
    # only if settings.local_token is unset — see app/core/auth.py docstring).
    app = FastAPI(title=settings.app_name, dependencies=[Depends(require_local_token)])
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
    # User-facing preferences (display name in the prompt, future settings
    # panel additions) — distinct from app.state.settings above, which is
    # process/env configuration, not a user preference.
    # Context: agent_reports/2026-07-11_settings-panel-foundation.md
    app.state.user_settings_service = SettingsService(SettingsRepository(settings.database_path))
    # FAZA 10: permission/risk layer. Cancellation registry is process-lifetime
    # in-memory state (see app/agent/cancellation.py); the durable audit trail
    # stays in tool_runs via ActionLogService.
    app.state.cancellation_registry = CancellationRegistry()
    # FAZA 11: memory + artifact + event bridge services. The permission/risk
    # enforcement layer (FAZA 10) reads tool definition flags; these tools are
    # all low/medium risk (notes, records, artifacts) or require computer_mode
    # (screenshot, ui_inspect), so they coexist with the FAZA 10 permission
    # engine without changes. Legacy PowerShell fallbacks stay in place until
    # these Python versions are verified end-to-end.
    # Context: agent_reports/2026-07-05_faza11-tool-registry-local-tools.md
    event_bus = EventBus(EventRepository(settings.database_path))
    app.state.event_bus = event_bus
    app.state.notes_service = NotesService(NotesRepository(settings.database_path))
    app.state.records_service = RecordsService(RecordsRepository(settings.database_path))
    app.state.artifact_service = ArtifactService(
        ArtifactRepository(settings.database_path), event_bus=event_bus
    )
    # Screenshot retention/privacy (agent_reports/2026-07-12_screenshot-privacy.md,
    # FABLE-5 GUI review finding #3). Cleanup runs once here at startup (files
    # don't wait for someone to open the "Snimci ekrana" tab) and again lazily
    # on every GET /screenshots (see ScreenshotService.list()).
    app.state.screenshot_service = ScreenshotService(ScreenshotRepository(settings.database_path))
    app.state.screenshot_service.cleanup_expired()
    phase11_services = {
        "notes": app.state.notes_service,
        "records": app.state.records_service,
        "artifact": app.state.artifact_service,
        "screenshots_dir": settings.data_dir / "screenshots",
        "screenshot_service": app.state.screenshot_service,
        "event_bus": event_bus,
        # FAZA 16: OpenAI/Exa/image integrations now live in the Python backend.
        "exa_client": ExaClient(settings.exa_api_key),
        "openai_image_client": OpenAIImageClient(settings.openai_api_key),
        "images_dir": settings.data_dir / "images",
    }
    app.state.tool_registry = create_default_registry(services=phase11_services)
    # Emit backend.ready so the UI knows the event bridge is live.
    event_bus.emit("backend.ready", title="Python backend ready")

    # FAZA 15: agent runtime (LocalDesktopAssistant). Tool calls the model
    # requests are executed through this same ToolExecutor instance — the
    # identical permission/cancellation gate used by POST /tools/execute, so
    # the agent runtime has no separate path that could bypass it.
    app.state.conversation_state_service = ConversationStateService(
        AgentConversationRepository(settings.database_path)
    )
    agent_tool_executor = ToolExecutor(
        app.state.tool_registry,
        action_log=app.state.action_log,
        confirmations=app.state.confirmation_service,
        cancellations=app.state.cancellation_registry,
    )
    app.state.agent_runtime = LocalDesktopAssistant(
        model_client=OpenAIModelClient(settings.openai_api_key),
        tool_executor=agent_tool_executor,
        conversations=app.state.conversation_state_service,
    )
    # Dictation Mode "Doradi" menu (formalize/shorten/proofread/translate) —
    # a plain text-in/text-out model call, deliberately NOT routed through
    # agent_runtime above (that path persists conversation state and runs a
    # tool-calling loop, wrong semantics for "rewrite this whole note").
    # Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
    app.state.text_model_client = OpenAIModelClient(settings.openai_api_key)

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(tools_router)
    app.include_router(realtime_router)
    app.include_router(confirmations_router)
    app.include_router(plans_router)
    app.include_router(events_router)
    app.include_router(agent_router)
    app.include_router(security_router)
    app.include_router(settings_router)
    app.include_router(text_router)
    app.include_router(screenshots_router)
    return app


app = create_app()


if __name__ == "__main__":
    # FAZA 19: entry point for the PyInstaller sidecar (ricky_backend.spec
    # builds this file into ricky_backend.exe). The dev path launches via
    # `python -m uvicorn app.main:app`, which never executes this block — the
    # uvicorn CLI drives the server itself. A frozen executable has no CLI to
    # invoke, so it must start the server itself here, using the same
    # RICKY_HOST/RICKY_PORT env vars electron/services/pythonProcess.cjs
    # already passes to the packaged backend (see app/core/config.py).
    # Context: agent_reports/2026-07-06_faza19-packaging-plan.md
    import uvicorn

    _settings = get_settings()
    uvicorn.run(app, host=_settings.host, port=_settings.port)