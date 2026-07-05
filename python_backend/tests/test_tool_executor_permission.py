from __future__ import annotations

from app.agent.cancellation import CancellationRegistry
from app.agent.tool_executor import ToolExecutor
from app.agent.tool_registry import ToolRegistry
from app.core.config import Settings
from app.schemas.tool import ToolDefinition, ToolExecutionContext, ToolExecutionRequest
from app.services.confirmation_service import ConfirmationService
from app.storage.db import initialize_database
from app.storage.repositories.confirmation_repo import ConfirmationRepository


def make_env(tmp_path):
    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)
    confirmations = ConfirmationService(ConfirmationRepository(settings.database_path))
    cancellations = CancellationRegistry()

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="risky_tool",
            description="Requires confirmation and computer mode.",
            input_schema={"type": "object"},
            risk="high",
            requires_confirmation=True,
            requires_computer_mode=True,
            allowed_in_background=False,
            timeout_ms=5000,
            implemented_by="python",
            enabled=True,
        ),
        lambda arguments: {"echoed": arguments},
    )

    executor = ToolExecutor(registry, confirmations=confirmations, cancellations=cancellations)
    return executor, confirmations, cancellations


def test_execute_without_computer_mode_is_blocked(tmp_path) -> None:
    executor, _confirmations, _cancellations = make_env(tmp_path)

    response = executor.execute(
        ToolExecutionRequest(
            tool_name="risky_tool",
            arguments={"x": 1},
            context=ToolExecutionContext(computer_mode=False),
        )
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "COMPUTER_MODE_REQUIRED"
    assert response.tool_state == "failed"
    assert response.execution_id is not None


def test_execute_without_confirmation_is_blocked(tmp_path) -> None:
    executor, _confirmations, _cancellations = make_env(tmp_path)

    response = executor.execute(
        ToolExecutionRequest(
            tool_name="risky_tool",
            arguments={"x": 1},
            context=ToolExecutionContext(computer_mode=True),
        )
    )

    assert response.ok is False
    assert response.error.code == "CONFIRMATION_REQUIRED"
    assert response.tool_state == "failed"


def test_execute_with_approved_confirmation_succeeds(tmp_path) -> None:
    executor, confirmations, cancellations = make_env(tmp_path)
    confirmation = confirmations.propose(
        action_name="risky_tool",
        payload={"x": 1},
        risk_level="high",
        tool_name="risky_tool",
    )
    confirmations.approve(confirmation["id"])

    response = executor.execute(
        ToolExecutionRequest(
            tool_name="risky_tool",
            arguments={"x": 1},
            context=ToolExecutionContext(computer_mode=True, confirmation_id=confirmation["id"]),
        )
    )

    assert response.ok is True
    assert response.result == {"echoed": {"x": 1}}
    assert response.tool_state == "completed"
    assert cancellations.get(response.execution_id).state == "completed"


def test_cancel_requested_before_execution_stops_the_tool(tmp_path) -> None:
    executor, confirmations, cancellations = make_env(tmp_path)
    confirmation = confirmations.propose(
        action_name="risky_tool",
        payload={"x": 1},
        risk_level="high",
        tool_name="risky_tool",
    )
    confirmations.approve(confirmation["id"])

    # Simulate a "stop" arriving for an execution_id that a caller already
    # knows about (e.g. reused from a previous planning step) — here we just
    # pre-cancel by hooking into the registry the way a concurrent
    # /tools/executions/{id}/cancel request would, then execute.
    original_start = cancellations.start

    def start_and_cancel(execution_id: str, tool_name: str):
        record = original_start(execution_id, tool_name)
        cancellations.request_cancel(execution_id)
        return record

    cancellations.start = start_and_cancel  # type: ignore[method-assign]

    response = executor.execute(
        ToolExecutionRequest(
            tool_name="risky_tool",
            arguments={"x": 1},
            context=ToolExecutionContext(computer_mode=True, confirmation_id=confirmation["id"]),
        )
    )

    assert response.ok is False
    assert response.error.code == "CANCELLED"
    assert response.tool_state == "cancelled_before_commit"
