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
