from fastapi import APIRouter, Request

from app.agent.tool_executor import ToolExecutor
from app.core.errors import AppError
from app.schemas.tool import ToolExecutionRequest, ToolExecutionResponse, ToolsListResponse

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=ToolsListResponse)
def list_tools(request: Request) -> ToolsListResponse:
    return ToolsListResponse(tools=request.app.state.tool_registry.list())


@router.post("/tools/execute", response_model=ToolExecutionResponse)
def execute_tool(
    request_body: ToolExecutionRequest,
    request: Request,
) -> ToolExecutionResponse:
    executor = ToolExecutor(
        request.app.state.tool_registry,
        action_log=getattr(request.app.state, "action_log", None),
        confirmations=getattr(request.app.state, "confirmation_service", None),
        cancellations=getattr(request.app.state, "cancellation_registry", None),
    )
    return executor.execute(request_body)


@router.post("/tools/executions/{execution_id}/cancel")
def cancel_tool_execution(execution_id: str, request: Request) -> dict[str, str | bool | None]:
    """Request cancellation of an in-flight tool call (FAZA 10).

    Voice interruption ("stop") should call this in addition to tearing down
    the Realtime connection — the two are separate layers (see
    SECURITY_HARDENING_PLAN.md section 25). Whether the tool actually stops
    depends on its own cancellation checkpoints; the response tool_state from
    /tools/execute reports the real outcome, this endpoint only raises the flag.
    """
    registry = getattr(request.app.state, "cancellation_registry", None)
    if registry is None:
        raise AppError("CANCELLATION_UNAVAILABLE", "Cancellation registry is not initialized.", status_code=500)

    record = registry.request_cancel(execution_id)
    if record is None:
        raise AppError("EXECUTION_NOT_FOUND", f"Execution '{execution_id}' not found.", status_code=404)

    return {"ok": True, "execution_id": execution_id, "tool_state": record.state}