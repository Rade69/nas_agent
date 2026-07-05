from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "critical"]
ImplementedBy = Literal["python", "electron_legacy"]

# FAZA 10 tool execution state machine — see SECURITY_HARDENING_PLAN.md section 25
# "Realtime Event Flow and Cancellation Safety". Voice interruption and tool
# cancellation are separate layers; this is the tool-side state.
ToolState = Literal[
    "planned",
    "preflight",
    "running",
    "commit_started",
    "completed",
    "cancel_requested",
    "cancelled_before_commit",
    "cannot_cancel_commit_started",
    "failed",
]


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: RiskLevel
    requires_confirmation: bool
    requires_computer_mode: bool
    requires_active_window_match: bool = False
    allowed_apps: list[str] = Field(default_factory=list)
    blocked_apps: list[str] = Field(default_factory=list)
    logs_action_receipt: bool = False
    allowed_in_background: bool
    timeout_ms: int
    implemented_by: ImplementedBy
    enabled: bool


class ToolsListResponse(BaseModel):
    tools: list[ToolDefinition]


class ToolExecutionContext(BaseModel):
    computer_mode: bool = False
    conversation_id: str | None = None
    request_id: str | None = None
    # FAZA 10: required when the tool definition sets requires_confirmation.
    # Must reference an "approved" confirmation bound to this exact tool_name
    # and payload (see app/agent/permission_engine.py).
    confirmation_id: str | None = None


class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: ToolExecutionContext = Field(default_factory=ToolExecutionContext)


class ToolError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResponse(BaseModel):
    ok: bool
    tool_name: str
    result: dict[str, Any] | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    action_log_id: str
    duration_ms: int
    error: ToolError | None = None
    execution_id: str | None = None
    tool_state: ToolState | None = None
