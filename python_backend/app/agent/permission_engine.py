from __future__ import annotations

from app.core.errors import AppError
from app.core.payload_hash import hash_payload
from app.schemas.tool import ToolDefinition, ToolExecutionRequest
from app.services.confirmation_service import ConfirmationService

# Tool executor checks from SECURITY_HARDENING_PLAN.md section 8. Steps 1-3
# (tool exists / enabled / argument validation) happen in ToolExecutor before
# this is called. Steps 10-12 (active window match, path sandbox, network
# target) are NOT implemented here — they require capabilities the Python
# backend does not have yet (FAZA 11 tool registry / FAZA 13-14 computer-use).
# This function only covers steps 4-9: risk gate, Computer Mode, and
# confirmation_id validation.


def check_permission(
    tool: ToolDefinition,
    request: ToolExecutionRequest,
    confirmation_service: ConfirmationService | None,
) -> AppError | None:
    # Defense in depth: critical tools always require a confirmation, even if
    # a tool definition forgot to set requires_confirmation explicitly.
    requires_confirmation = tool.requires_confirmation or tool.risk == "critical"

    if tool.requires_computer_mode and not request.context.computer_mode:
        return AppError(
            "COMPUTER_MODE_REQUIRED",
            f"Tool '{tool.name}' requires Computer Mode to be enabled.",
            status_code=403,
        )

    if not requires_confirmation:
        return None

    if confirmation_service is None:
        return AppError(
            "CONFIRMATIONS_UNAVAILABLE",
            "Confirmation service is not initialized; cannot execute a tool that requires confirmation.",
            status_code=500,
        )

    confirmation_id = request.context.confirmation_id
    if not confirmation_id:
        return AppError(
            "CONFIRMATION_REQUIRED",
            f"Tool '{tool.name}' requires an approved confirmation_id.",
            status_code=403,
        )

    confirmation = confirmation_service.get(confirmation_id)
    if confirmation is None:
        return AppError(
            "CONFIRMATION_NOT_FOUND",
            f"Confirmation '{confirmation_id}' not found.",
            status_code=404,
        )

    if confirmation["status"] != "approved":
        return AppError(
            "CONFIRMATION_NOT_APPROVED",
            f"Confirmation '{confirmation_id}' is '{confirmation['status']}', not approved.",
            status_code=403,
        )

    if confirmation_service.is_expired(confirmation):
        return AppError(
            "CONFIRMATION_EXPIRED",
            f"Confirmation '{confirmation_id}' has expired.",
            status_code=403,
        )

    bound_tool_name = confirmation.get("tool_name")
    if bound_tool_name and bound_tool_name != tool.name:
        return AppError(
            "CONFIRMATION_MISMATCH",
            f"Confirmation '{confirmation_id}' was approved for tool '{bound_tool_name}', not '{tool.name}'.",
            status_code=403,
        )

    bound_hash = confirmation.get("payload_hash")
    if bound_hash and bound_hash != hash_payload(request.arguments):
        return AppError(
            "CONFIRMATION_MISMATCH",
            f"Confirmation '{confirmation_id}' does not match the submitted arguments.",
            status_code=403,
        )

    return None
