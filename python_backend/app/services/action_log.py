"""Durable audit trail for tool executions (FAZA 7).

Wraps ToolRunRepository to persist every tool run (success or failure)
in the tool_runs SQLite table, including duration, error codes, and
risk/confirmation metadata.
"""
from __future__ import annotations

from typing import Any

from app.schemas.tool import ToolDefinition, ToolExecutionRequest, ToolExecutionResponse
from app.storage.repositories.tool_run_repo import ToolRunRepository

# FAZA S-4 / audit O3 (agent_reports/2026-07-08_pi-log-hygiene-audit.md):
# the tool_runs audit table used to store the FULL input/output payload of every
# tool call in plaintext SQLite — including the exact text typed by
# computer_type_text (which can be a password typed into a field), email bodies,
# transcripts, and any credential-bearing argument. We keep the audit record
# (which tool ran, with which keys, result status) but redact the free-text /
# credential *values* so the durable DB no longer holds that sensitive content.
# Full DB-at-rest protection (0600 ACLs on Windows, SQLCipher) is a separate B3
# follow-up; this closes the plaintext-content leak cross-platform.
SENSITIVE_PAYLOAD_KEYS = frozenset(
    {
        "text",
        "body",
        "content",
        "transcript",
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
    }
)

_REDACTED = "[REDACTED]"


def redact_sensitive(value: Any) -> Any:
    """Return a copy of `value` with sensitive free-text/credential values
    replaced by a placeholder, recursing into nested dicts/lists. Keys are
    preserved so the audit log still shows the shape of the call."""
    if isinstance(value, dict):
        return {
            key: (_REDACTED if key.lower() in SENSITIVE_PAYLOAD_KEYS else redact_sensitive(inner))
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


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
            input_payload=redact_sensitive(request.model_dump(mode="json")),
            output_payload=redact_sensitive(response.model_dump(mode="json")),
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