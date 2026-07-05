from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from app.agent.cancellation import CancellationRegistry
from app.agent.permission_engine import check_permission
from app.agent.tool_registry import RegisteredTool, ToolRegistry
from app.core.errors import AppError
from app.schemas.tool import ToolError, ToolExecutionRequest, ToolExecutionResponse, ToolState
from app.services.action_log import ActionLogService
from app.services.confirmation_service import ConfirmationService


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        action_log: ActionLogService | None = None,
        confirmations: ConfirmationService | None = None,
        cancellations: CancellationRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._action_log = action_log
        self._confirmations = confirmations
        self._cancellations = cancellations

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        started = perf_counter()
        action_log_id = str(uuid4())
        execution_id = f"exec_{uuid4().hex[:12]}"
        tool = self._registry.get(request.tool_name)

        if tool is None:
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "TOOL_NOT_FOUND",
                f"Tool '{request.tool_name}' is not registered.",
                execution_id=execution_id,
                tool_state="failed",
            )
            self._log(request=request, response=response, tool=None)
            return response

        if not tool.definition.enabled:
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "TOOL_DISABLED",
                f"Tool '{request.tool_name}' is disabled.",
                execution_id=execution_id,
                tool_state="failed",
            )
            self._log(request=request, response=response, tool=tool)
            return response

        record = self._cancellations.start(execution_id, request.tool_name) if self._cancellations else None

        permission_error: AppError | None = check_permission(tool.definition, request, self._confirmations)
        if permission_error is not None:
            if self._cancellations:
                self._cancellations.set_state(execution_id, "failed")
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                permission_error.code,
                permission_error.message,
                execution_id=execution_id,
                tool_state="failed",
            )
            self._log(request=request, response=response, tool=tool)
            return response

        if self._cancellations:
            self._cancellations.set_state(execution_id, "preflight")

        # Voice interruption and tool cancellation are separate layers (see
        # SECURITY_HARDENING_PLAN.md section 25). A cancel requested up to this
        # point stops the tool before it ever touches the OS/handler.
        if record is not None and record.cancel_requested:
            self._cancellations.set_state(execution_id, "cancelled_before_commit")  # type: ignore[union-attr]
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "CANCELLED",
                f"Tool '{request.tool_name}' was cancelled before it started.",
                execution_id=execution_id,
                tool_state="cancelled_before_commit",
            )
            self._log(request=request, response=response, tool=tool)
            return response

        # Commit phase begins here. For today's synchronous, atomic handlers
        # (e.g. echo) this call cannot itself be interrupted mid-flight; a
        # cancel requested during this window is reported honestly via
        # cannot_cancel_commit_started rather than pretending a rollback
        # happened. Long-running OS tools (FAZA 13/14) must check
        # cancellations.is_cancel_requested(execution_id) between their own
        # internal segments instead of relying on this single checkpoint.
        if self._cancellations:
            self._cancellations.set_state(execution_id, "commit_started")

        try:
            result = tool.handler(request.arguments)
        except ValueError as exc:
            if self._cancellations:
                self._cancellations.set_state(execution_id, "failed")
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "INVALID_ARGUMENTS",
                str(exc),
                execution_id=execution_id,
                tool_state="failed",
            )
            self._log(request=request, response=response, tool=tool)
            return response

        final_state: ToolState = "completed"
        if record is not None and record.cancel_requested:
            final_state = "cannot_cancel_commit_started"
        if self._cancellations:
            self._cancellations.set_state(execution_id, final_state)

        response = ToolExecutionResponse(
            ok=True,
            tool_name=request.tool_name,
            result=result,
            artifact_ids=[],
            event_ids=[],
            action_log_id=action_log_id,
            duration_ms=self._duration_ms(started),
            execution_id=execution_id,
            tool_state=final_state,
        )
        self._log(request=request, response=response, tool=tool)
        return response

    def _error_response(
        self,
        tool_name: str,
        action_log_id: str,
        started: float,
        code: str,
        message: str,
        *,
        execution_id: str | None = None,
        tool_state: ToolState | None = None,
    ) -> ToolExecutionResponse:
        return ToolExecutionResponse(
            ok=False,
            tool_name=tool_name,
            error=ToolError(code=code, message=message, details={}),
            action_log_id=action_log_id,
            duration_ms=self._duration_ms(started),
            execution_id=execution_id,
            tool_state=tool_state,
        )

    def _duration_ms(self, started: float) -> int:
        return int((perf_counter() - started) * 1000)

    def _log(
        self,
        *,
        request: ToolExecutionRequest,
        response: ToolExecutionResponse,
        tool: RegisteredTool | None,
    ) -> None:
        if self._action_log is None:
            return
        self._action_log.log_tool_response(
            request=request,
            response=response,
            tool_definition=tool.definition if tool else None,
        )