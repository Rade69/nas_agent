from __future__ import annotations

from typing import Any

from app.schemas.tool import ToolDefinition, ToolExecutionRequest, ToolExecutionResponse
from app.storage.repositories.tool_run_repo import ToolRunRepository


class ActionLogService:
    def __init__(self, tool_runs: ToolRunRepository) -> None:
        self._tool_runs = tool_runs

    def log_tool_response(
        self,
        *,
        request: ToolExecutionRequest,
        response: ToolExecutionResponse,
        tool_definition: ToolDefinition | None,
    ) -> None:
        error = response.error
        self._tool_runs.create(
            run_id=response.action_log_id,
            tool_name=request.tool_name,
            input_payload=request.model_dump(mode="json"),
            output_payload=response.model_dump(mode="json"),
            status="success" if response.ok else "failed",
            risk_level=tool_definition.risk if tool_definition else "low",
            requires_confirmation=tool_definition.requires_confirmation if tool_definition else False,
            computer_mode=request.context.computer_mode,
            duration_ms=response.duration_ms,
            error_code=error.code if error else None,
            error_message=error.message if error else None,
        )

    def recent_tool_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return [dict(row) for row in self._tool_runs.list_recent(limit)]