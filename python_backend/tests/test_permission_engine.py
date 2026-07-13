from __future__ import annotations

from app.agent.permission_engine import check_active_window, check_permission
from app.core.config import Settings
from app.schemas.tool import ToolDefinition, ToolExecutionContext, ToolExecutionRequest
from app.agent.permission_engine import AppError
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


# =============================================================================
#  S-04 fix: one-time-use confirmations
#  Context: docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md
# =============================================================================


def test_approved_confirmation_is_consumed_after_first_use(tmp_path) -> None:
    """The core acceptance test: check_permission() doesn't just validate the
    confirmation, it burns it — status flips to 'consumed' as a side effect
    of the first successful check."""
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 1}, risk_level="high", tool_name="test_tool"
    )
    confirmations.approve(confirmation["id"])

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is None

    stored = confirmations.get(confirmation["id"])
    assert stored is not None
    assert stored["status"] == "consumed"


def test_replaying_a_consumed_confirmation_is_rejected(tmp_path) -> None:
    """A second execution attempt with the exact same confirmation_id — a
    retry, a duplicate request, or an attacker replaying a captured ID —
    must not be authorized by the confirmation a first attempt already used.
    In the sequential case (this test) the second call's own status re-read
    already sees 'consumed' and is rejected by the earlier not-approved
    check — CONFIRMATION_ALREADY_CONSUMED (asserted separately below at the
    repository level) only fires for a true concurrent race, where both
    calls read 'approved' before either write lands."""
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 1}, risk_level="high", tool_name="test_tool"
    )
    confirmations.approve(confirmation["id"])

    first = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert first is None

    second = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert second is not None
    assert second.code == "CONFIRMATION_NOT_APPROVED"
    assert "consumed" in second.message


def test_consume_is_atomic_a_second_direct_call_is_rejected(tmp_path) -> None:
    """Repository-level guard test, independent of check_permission's earlier
    status check: calling ConfirmationService.consume() itself a second time
    for the same id returns None — this is the actual compare-and-swap that
    protects the true concurrent-race window."""
    confirmations = make_confirmations(tmp_path)
    confirmation = confirmations.propose(
        action_name="test_tool", payload={"a": 1}, risk_level="high", tool_name="test_tool"
    )
    confirmations.approve(confirmation["id"])

    first = confirmations.consume(confirmation["id"])
    assert first is not None
    assert first["status"] == "consumed"

    second = confirmations.consume(confirmation["id"])
    assert second is None


def test_confirmation_without_tool_name_cannot_gate_a_tool_call(tmp_path) -> None:
    """A confirmation created without tool_name (still valid for non-tool
    actions, e.g. plan proposals) must not be usable as a 'blank check' to
    authorize an arbitrary tool call just because payload happens to match."""
    confirmations = make_confirmations(tmp_path)
    tool = low_risk_tool(requires_confirmation=True, risk="high")
    confirmation = confirmations.propose(
        action_name="some_action", payload={"a": 1}, risk_level="high"
    )
    confirmations.approve(confirmation["id"])

    error = check_permission(tool, make_request(confirmation_id=confirmation["id"]), confirmations)
    assert error is not None
    assert error.code == "CONFIRMATION_MISMATCH"


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

# =============================================================================
#  R2d test coverage: check_active_window (FAZA 13 enforcement)
#  Context: agent_reports/2026-07-09_pi-permission-engine-test-coverage.md
# =============================================================================


def test_active_window_skips_when_flag_false() -> None:
    """When requires_active_window_match=False, check is skipped entirely."""
    tool = low_risk_tool(requires_active_window_match=False)
    error = check_active_window(tool)
    assert error is None


def test_active_window_skips_when_no_lists() -> None:
    """When allowed_apps and blocked_apps are both empty, nothing to enforce."""
    tool = low_risk_tool(requires_active_window_match=True, allowed_apps=[], blocked_apps=[])
    error = check_active_window(tool)
    assert error is None


def test_active_window_blocked_exact_match(monkeypatch) -> None:
    """Blocked app case-insensitive match on the foreground process."""
    monkeypatch.setattr(
        "app.agent.permission_engine._get_active_window_process",
        lambda: "powershell.exe",
    )
    tool = low_risk_tool(
        requires_active_window_match=True,
        blocked_apps=["powershell.exe"],
        allowed_apps=[],
    )
    error = check_active_window(tool)
    assert isinstance(error, AppError)
    assert error.code == "ACTIVE_WINDOW_BLOCKED"


def test_active_window_blocked_case_insensitive(monkeypatch) -> None:
    """Block check is case-insensitive (uses .lower())."""
    monkeypatch.setattr(
        "app.agent.permission_engine._get_active_window_process",
        lambda: "POWERSHELL.EXE",
    )
    tool = low_risk_tool(
        requires_active_window_match=True,
        blocked_apps=["powershell.exe"],
        allowed_apps=[],
    )
    error = check_active_window(tool)
    assert isinstance(error, AppError)
    assert error.code == "ACTIVE_WINDOW_BLOCKED"


def test_active_window_not_allowed(monkeypatch) -> None:
    """Process not in allowed list is rejected."""
    monkeypatch.setattr(
        "app.agent.permission_engine._get_active_window_process",
        lambda: "chrome.exe",
    )
    tool = low_risk_tool(
        requires_active_window_match=True,
        allowed_apps=["notepad.exe"],
        blocked_apps=[],
    )
    error = check_active_window(tool)
    assert isinstance(error, AppError)
    assert error.code == "ACTIVE_WINDOW_NOT_ALLOWED"


def test_active_window_allowed(monkeypatch) -> None:
    """Process in allowed list passes."""
    monkeypatch.setattr(
        "app.agent.permission_engine._get_active_window_process",
        lambda: "notepad.exe",
    )
    tool = low_risk_tool(
        requires_active_window_match=True,
        allowed_apps=["notepad.exe"],
        blocked_apps=[],
    )
    error = check_active_window(tool)
    assert error is None


def test_active_window_unknown_fail_closed(monkeypatch) -> None:
    """Cannot determine foreground process → fail-closed (security guarantee)."""
    monkeypatch.setattr(
        "app.agent.permission_engine._get_active_window_process",
        lambda: None,
    )
    tool = low_risk_tool(
        requires_active_window_match=True,
        blocked_apps=["x.exe"],
        allowed_apps=[],
    )
    error = check_active_window(tool)
    assert isinstance(error, AppError)
    assert error.code == "ACTIVE_WINDOW_UNKNOWN"


# =============================================================================
#  R2d test coverage: check_permission S-2 external_content_seen escalation
# =============================================================================


def test_external_content_escalates_medium_tool(tmp_path) -> None:
    """Medium-risk non-reader tool escalated when external content was seen."""
    tool = low_risk_tool(
        risk="medium",
        reads_external_content=False,
        requires_confirmation=False,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True),
        make_confirmations(tmp_path),
    )
    assert isinstance(error, AppError)
    assert error.code == "CONFIRMATION_REQUIRED"


def test_external_content_does_not_escalate_readers(tmp_path) -> None:
    """Pure readers (reads_external_content=True) are exempt from S-2 escalation."""
    tool = low_risk_tool(
        risk="low",
        reads_external_content=True,
        requires_confirmation=False,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True),
        make_confirmations(tmp_path),
    )
    assert error is None


def test_external_content_escalates_computer_mode_tool(tmp_path) -> None:
    """Low-risk computer-mode tool escalated because requires_computer_mode=True."""
    tool = low_risk_tool(
        risk="low",
        reads_external_content=False,
        requires_computer_mode=True,
        requires_confirmation=False,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True, computer_mode=True),
        make_confirmations(tmp_path),
    )
    assert isinstance(error, AppError)
    assert error.code == "CONFIRMATION_REQUIRED"


def test_external_content_no_escalation_when_not_seen(tmp_path) -> None:
    """Baseline: without external_content_seen the tool runs normally."""
    tool = low_risk_tool(
        risk="medium",
        reads_external_content=False,
        requires_confirmation=False,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=False),
        make_confirmations(tmp_path),
    )
    assert error is None


# =============================================================================
#  S-2 gap fix (2026-07-12): outbound low-risk tools now escalate too
#  Context: docs/PROJECT_OVERVIEW.md section 4.7 (found by FABLE-5 review)
# =============================================================================


def test_external_content_escalates_outbound_low_risk_tool(tmp_path) -> None:
    """A low-risk, non-computer-mode, non-reader tool (e.g. image_generate)
    used to fall through both prior conditions untouched — the risk/
    computer_mode escalation only covers tools that act locally. outbound=True
    now escalates it independently of risk level."""
    tool = low_risk_tool(
        risk="low",
        reads_external_content=False,
        requires_computer_mode=False,
        requires_confirmation=False,
        outbound=True,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True),
        make_confirmations(tmp_path),
    )
    assert isinstance(error, AppError)
    assert error.code == "CONFIRMATION_REQUIRED"


def test_external_content_escalates_outbound_reader_tool(tmp_path) -> None:
    """A tool that is both a reader and outbound (e.g. web_search: its results
    are untrusted content, and its query itself is sent externally) must not
    be exempted by the reads_external_content reader exemption — that
    exemption only covers the local-acting escalation branch."""
    tool = low_risk_tool(
        risk="low",
        reads_external_content=True,
        requires_computer_mode=False,
        requires_confirmation=False,
        outbound=True,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True),
        make_confirmations(tmp_path),
    )
    assert isinstance(error, AppError)
    assert error.code == "CONFIRMATION_REQUIRED"


def test_non_outbound_low_risk_tool_still_not_escalated(tmp_path) -> None:
    """Regression guard: a plain local low-risk tool (e.g. note_add) must stay
    unescalated — outbound=False by default, so this fix must not widen S-2
    beyond tools that actually send data externally."""
    tool = low_risk_tool(
        risk="low",
        reads_external_content=False,
        requires_computer_mode=False,
        requires_confirmation=False,
    )
    error = check_permission(
        tool,
        make_request(external_content_seen=True),
        make_confirmations(tmp_path),
    )
    assert error is None
