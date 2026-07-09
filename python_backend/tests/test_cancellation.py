from __future__ import annotations

from app.agent.cancellation import CancellationRegistry


def test_start_creates_planned_record() -> None:
    registry = CancellationRegistry()
    record = registry.start("exec_1", "test_tool")
    assert record.state == "planned"
    assert record.cancel_requested is False


def test_request_cancel_before_terminal_state() -> None:
    registry = CancellationRegistry()
    registry.start("exec_1", "test_tool")

    record = registry.request_cancel("exec_1")
    assert record is not None
    assert record.cancel_requested is True
    assert record.state == "cancel_requested"
    assert registry.is_cancel_requested("exec_1") is True


def test_request_cancel_unknown_execution_returns_none() -> None:
    registry = CancellationRegistry()
    assert registry.request_cancel("does_not_exist") is None


def test_request_cancel_after_completion_flags_but_does_not_override_terminal_state() -> None:
    registry = CancellationRegistry()
    registry.start("exec_1", "test_tool")
    registry.set_state("exec_1", "completed")

    record = registry.request_cancel("exec_1")
    assert record is not None
    assert record.cancel_requested is True
    assert record.state == "completed"


def test_set_state_commit_started_marks_commit_started_flag() -> None:
    registry = CancellationRegistry()
    registry.start("exec_1", "test_tool")
    registry.set_state("exec_1", "commit_started")

    record = registry.get("exec_1")
    assert record is not None
    assert record.commit_started is True
    assert record.state == "commit_started"


def test_request_cancel_all_flags_every_in_flight_execution() -> None:
    registry = CancellationRegistry()
    registry.start("exec_1", "tool_a")
    registry.start("exec_2", "tool_b")

    flagged = registry.request_cancel_all()

    assert {r.execution_id for r in flagged} == {"exec_1", "exec_2"}
    assert registry.is_cancel_requested("exec_1") is True
    assert registry.is_cancel_requested("exec_2") is True
    assert registry.get("exec_1").state == "cancel_requested"


def test_request_cancel_all_skips_terminal_executions() -> None:
    registry = CancellationRegistry()
    registry.start("exec_done", "tool_a")
    registry.set_state("exec_done", "completed")
    registry.start("exec_live", "tool_b")

    flagged = registry.request_cancel_all()

    # Only the still-running execution is flagged; the completed one is untouched.
    assert {r.execution_id for r in flagged} == {"exec_live"}
    assert registry.is_cancel_requested("exec_done") is False
    assert registry.get("exec_done").state == "completed"


def test_request_cancel_all_on_empty_registry_returns_empty_list() -> None:
    registry = CancellationRegistry()
    assert registry.request_cancel_all() == []
