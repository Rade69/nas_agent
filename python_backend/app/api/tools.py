from fastapi import APIRouter, Request

from app.agent.tool_executor import ToolExecutor
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
    )
    return executor.execute(request_body)