from __future__ import annotations

import sys

from app.core.errors import AppError
from app.core.payload_hash import hash_payload
from app.schemas.tool import ToolDefinition, ToolExecutionRequest
from app.services.confirmation_service import ConfirmationService

# Tool executor checks from SECURITY_HARDENING_PLAN.md section 8.
# Steps 1-3 (tool exists / enabled / argument validation) happen in ToolExecutor
# before this is called. Steps 4-9 (risk gate, Computer Mode, confirmation_id)
# are handled by check_permission().
# Step 10 (active window match) is handled by check_active_window() (FAZA 13).
# Steps 11-12 (path sandbox, network target) remain unimplemented.

# SECURITY_HARDENING_PLAN.md section 9 "Active window validation" — default
# blocked_apps for any tool that types/clicks/scrolls into the active window.
# Only covers processes identifiable by exact executable name; category-level
# risks named in the same section (banking sites, password managers running
# inside a browser tab, "system settings requiring admin") cannot be blocked
# this way — see FAZA 13 agent report follow-up notes for that limitation.
#
# Context: agent_reports/2026-07-06_faza13-14-security-verification-fix.md
# (this list existed as an unused capability before that report — the
# computer_* tool definitions never actually populated blocked_apps).
DEFAULT_BLOCKED_APPS: list[str] = [
    "powershell.exe",
    "powershell_ise.exe",
    "pwsh.exe",
    "cmd.exe",
    "regedit.exe",
    "taskmgr.exe",
    "mmc.exe",
    "credentialuibroker.exe",
    "mstsc.exe",
]


def _get_active_window_process() -> str | None:
    """Return the executable name (e.g. 'notepad.exe') of the foreground window.

    Returns None on non-Windows or if the call fails for any reason.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        hwnd = user32.GetForegroundWindow()
        proc_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        import psutil

        return psutil.Process(proc_id.value).name()
    except Exception:
        return None


def check_active_window(tool: ToolDefinition) -> AppError | None:
    """Enforce active window allow/block lists (SECURITY_HARDENING_PLAN.md step 10).

    Only runs when the tool definition explicitly sets
    requires_active_window_match=True AND either allowed_apps or blocked_apps
    is non-empty. Returns None if the check passes, or an AppError if the
    active window violates the constraints.

    This is a separate function from check_permission() so that the active
    window is queried only once per execution (ToolExecutor calls both in
    sequence, short-circuiting on the first failure).
    """
    if not tool.requires_active_window_match:
        return None

    if not tool.allowed_apps and not tool.blocked_apps:
        return None

    process_name = _get_active_window_process()
    if process_name is None:
        # Cannot determine active window — fail closed
        return AppError(
            "ACTIVE_WINDOW_UNKNOWN",
            f"Tool '{tool.name}' requires active window verification but the foreground process could not be determined.",
            status_code=403,
        )

    if tool.blocked_apps and process_name.lower() in (a.lower() for a in tool.blocked_apps):
        return AppError(
            "ACTIVE_WINDOW_BLOCKED",
            f"Tool '{tool.name}' cannot run when the active window is '{process_name}' (blocked).",
            status_code=403,
        )

    if tool.allowed_apps and process_name.lower() not in (a.lower() for a in tool.allowed_apps):
        return AppError(
            "ACTIVE_WINDOW_NOT_ALLOWED",
            f"Tool '{tool.name}' can only run when the active window is one of: {', '.join(tool.allowed_apps)}. Current: '{process_name}'.",
            status_code=403,
        )

    return None


def check_permission(
    tool: ToolDefinition,
    request: ToolExecutionRequest,
    confirmation_service: ConfirmationService | None,
) -> AppError | None:
    # Defense in depth: critical tools always require a confirmation, even if
    # a tool definition forgot to set requires_confirmation explicitly.
    requires_confirmation = tool.requires_confirmation or tool.risk == "critical"

    # FAZA S-2 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md S8): prompt-injection
    # containment. Once an untrusted-external-content tool has run earlier in
    # this turn (external_content_seen), any tool that *acts* on the system —
    # medium+ risk or anything requiring Computer Mode — is escalated to require
    # confirmation, even if its own definition wouldn't. This breaks the
    # "read attacker-controlled screen/web text -> act without approval" chain.
    # Pure readers (reads_external_content) are exempt so chained inspection
    # doesn't lock itself out.
    if (
        request.context.external_content_seen
        and not tool.reads_external_content
        and (tool.risk in ("medium", "high", "critical") or tool.requires_computer_mode)
    ):
        requires_confirmation = True

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
