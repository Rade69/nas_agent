from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.schemas.tool import ToolState

_TERMINAL_STATES: frozenset[ToolState] = frozenset(
    {"completed", "failed", "cancelled_before_commit", "cannot_cancel_commit_started"}
)


@dataclass
class ExecutionRecord:
    execution_id: str
    tool_name: str
    state: ToolState = "planned"
    cancel_requested: bool = False
    commit_started: bool = False


class CancellationRegistry:
    """In-memory execution_id/cancellation_token tracking (FAZA 10).

    Deliberately not persisted: this tracks in-flight tool calls for the
    lifetime of the backend process only, mirroring how `cancellation_token`
    is described in SECURITY_HARDENING_PLAN.md section 25 as a runtime
    handshake between "stop" and the tool executor, not a durable record
    (the durable audit trail is the tool_runs action log / Action Receipt).
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, ExecutionRecord] = {}

    def start(self, execution_id: str, tool_name: str) -> ExecutionRecord:
        with self._lock:
            record = ExecutionRecord(execution_id=execution_id, tool_name=tool_name)
            self._records[execution_id] = record
            return record

    def get(self, execution_id: str) -> ExecutionRecord | None:
        with self._lock:
            return self._records.get(execution_id)

    def set_state(self, execution_id: str, state: ToolState) -> None:
        with self._lock:
            record = self._records.get(execution_id)
            if record is not None:
                record.state = state
                if state == "commit_started":
                    record.commit_started = True

    def request_cancel(self, execution_id: str) -> ExecutionRecord | None:
        with self._lock:
            record = self._records.get(execution_id)
            if record is None:
                return None
            record.cancel_requested = True
            if record.state not in _TERMINAL_STATES:
                record.state = "cancel_requested"
            return record

    def request_cancel_all(self) -> list[ExecutionRecord]:
        """Flag every non-terminal in-flight execution for cancellation.

        Backs the Stop button ("stop everything") — the user does not pick an
        execution_id, so this raises the cancel flag on all records that are not
        already in a terminal state and returns the ones that were flagged.
        Already-finished executions are left untouched. Same runtime-handshake
        semantics as request_cancel(): whether a tool actually stops depends on
        its own cancellation checkpoints.
        """
        with self._lock:
            flagged: list[ExecutionRecord] = []
            for record in self._records.values():
                if record.state in _TERMINAL_STATES:
                    continue
                record.cancel_requested = True
                record.state = "cancel_requested"
                flagged.append(record)
            return flagged

    def is_cancel_requested(self, execution_id: str) -> bool:
        with self._lock:
            record = self._records.get(execution_id)
            return bool(record and record.cancel_requested)
