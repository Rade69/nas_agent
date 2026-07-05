from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from app.agent.tool_registry import RegisteredTool, ToolRegistry
from app.schemas.tool import ToolError, ToolExecutionRequest, ToolExecutionResponse
from app.services.action_log import ActionLogService


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, action_log: ActionLogService | None = None) -> None:
        self._registry = registry
        self._action_log = action_log

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        started = perf_counter()
        action_log_id = str(uuid4())
        tool = self._registry.get(request.tool_name)

        if tool is None:
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "TOOL_NOT_FOUND",
                f"Tool '{request.tool_name}' is not registered.",
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
            )
            self._log(request=request, response=response, tool=tool)
            return response

        try:
            result = tool.handler(request.arguments)
        except ValueError as exc:
            response = self._error_response(
                request.tool_name,
                action_log_id,
                started,
                "INVALID_ARGUMENTS",
                str(exc),
            )
            self._log(request=request, response=response, tool=tool)
            return response

        response = ToolExecutionResponse(
            ok=True,
            tool_name=request.tool_name,
            result=result,
            artifact_ids=[],
            event_ids=[],
            action_log_id=action_log_id,
            duration_ms=self._duration_ms(started),
        )
        self._log(request=request, response=response, tool=tool)
        return response

    def _error_response(
        self, tool_name: str, action_log_id: str, started: float, code: str, message: str
    ) -> ToolExecutionResponse:
        return ToolExecutionResponse(
            ok=False,
            tool_name=tool_name,
            error=ToolError(code=code, message=message, details={}),
            action_log_id=action_log_id,
            duration_ms=self._duration_ms(started),
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