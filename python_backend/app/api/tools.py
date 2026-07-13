"""REST endpoints for the tool system.

GET /tools — list all registered tool definitions.
POST /tools/execute — execute a single tool through the permission/
  cancellation gate (same ToolExecutor instance the agent runtime uses).
POST /tools/executions/cancel-all — flag all in-flight executions for
  cancellation (Stop button / kill-switch backend half).
"""
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


@router.post("/tools/executions/cancel-all")
def cancel_all_tool_executions(request: Request) -> dict[str, object]:
    """Request cancellation of every in-flight tool call (Stop button).

    The Stop button is "stop everything": the user does not choose an
    execution_id, so this flags all non-terminal executions at once. Voice
    interruption tears down the Realtime connection separately in the renderer;
    this is the backend half so an in-flight tool actually gets the cancel flag.
    Returns the list of execution_ids that were flagged (may be empty if nothing
    was running).
    """
    registry = getattr(request.app.state, "cancellation_registry", None)
    if registry is None:
        raise AppError("CANCELLATION_UNAVAILABLE", "Cancellation registry is not initialized.", status_code=500)

    flagged = registry.request_cancel_all()
    return {"ok": True, "cancelled": [record.execution_id for record in flagged], "count": len(flagged)}


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