from __future__ import annotations

from app.agent.permission_engine import check_permission
from app.core.config import Settings
from app.schemas.tool import ToolDefinition, ToolExecutionContext, ToolExecutionRequest
from app.services.confirmation_service import ConfirmationService
from app.storage.db import initialize_database
from app.storage.repositories.confirmation_repo import ConfirmationRepository


def make_confirmations(tmp_path) -> ConfirmationService:
    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)
    return ConfirmationService(ConfirmationRepository(settings.database_path))


def low_risk_tool(**overrides) -> ToolDefinition:
    base = dict(
        name="test_tool",
        description="Test tool.",
        input_schema={"type": "object"},
        risk="low",
        requires_confirmation=False,
        requires_computer_mode=False,
        allowed_in_background=True,
        timeout_ms=5000,
        implemented_by="python",
        enabled=True,
    )
    base.update(overrides)
    return ToolDefinition(**base)


def make_request(**context_overrides) -> ToolExecutionRequest:
    return ToolExecutionRequest(
        tool_name="test_tool",
        arguments={"a": 1},
        context=ToolExecutionContext(**context_overrides),
    )


def test_low_risk_tool_needs_no_permission(tmp_path) -> None:
    tool = low_risk_tool()
    error = check_permission(tool, make_request(), make_confirmations(tmp_path))
    assert error is None


def test_computer_mode_required_blocks_when_off(tmp_path) -> None:
    tool = low_risk_tool(requires_computer_mode=True)
    error = check_permission(tool, make_request(computer_mode=False), make_confirmations(tmp_path))
    assert error is not None
    assert error.code == "COMPUTER_MODE_REQUIRED"


def test_computer_mode_required_allows_when_on(tmp_path) -> None:
    tool = low_risk_tool(requires_computer_mode=True)
    error = check_permission(tool, make_request(computer_mode=True), make_confirmations(tmp_path))
    assert error is None


def test_confirmation_required_but_missing(tmp_path) -> None:
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    error = check_permission(tool, make_request(), make_confirmations(tmp_path))
    assert error is not None
    assert error.code == "CONFIRMATION_REQUIRED"


def test_confirmation_not_found(tmp_path) -> None:
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    error = check_permission(
        tool, make_request(confirmation_id="confirm_missing"), make_confirmations(tmp_path)
    )
    assert error is not None
    assert error.code == "CONFIRMATION_NOT_FOUND"


def test_confirmation_not_yet_approved(tmp_path) -> None:
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 1}, risk_level="high", tool_name="test_tool"
    )

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is not None
    assert error.code == "CONFIRMATION_NOT_APPROVED"


def test_approved_confirmation_matching_payload_allows_execution(tmp_path) -> None:
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 1}, risk_level="high", tool_name="test_tool"
    )
    confirmations.approve(confirmation["id"])

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is None


def test_approved_confirmation_wrong_payload_is_rejected(tmp_path) -> None:
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 999}, risk_level="high", tool_name="test_tool"
    )
    confirmations.approve(confirmation["id"])

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is not None
    assert error.code == "CONFIRMATION_MISMATCH"


def test_approved_confirmation_wrong_tool_is_rejected(tmp_path) -> None:
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="other_tool", payload={"a": 1}, risk_level="high", tool_name="other_tool"
    )
    confirmations.approve(confirmation["id"])

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is not None
    assert error.code == "CONFIRMATION_MISMATCH"


def test_expired_confirmation_is_rejected(tmp_path) -> None:
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool",
        payload={"a": 1},
        risk_level="high",
        tool_name="test_tool",
        ttl_seconds=1,
    )
    confirmations.approve(confirmation["id"])

    # Force expiry without sleeping in the test.
    stored = confirmations.get(confirmation["id"])
    assert stored is not None
    from datetime import UTC, datetime, timedelta

    past = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    with_expired = {**stored, "expires_at": past}
    assert confirmations.is_expired(with_expired) is True


def test_critical_risk_requires_confirmation_even_if_not_flagged(tmp_path) -> None:
    tool = low_risk_tool(risk="critical", requires_confirmation=False)
    error = check_permission(tool, make_request(), make_confirmations(tmp_path))
    assert error is not None
    assert error.code == "CONFIRMATION_REQUIRED"
