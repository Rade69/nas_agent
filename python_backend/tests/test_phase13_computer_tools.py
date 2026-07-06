"""Tests for FAZA 13 computer-use tools.

Covers:
- Tool registration (all 5 computer_* tools appear in /tools)
- Computer mode enforcement (all 5 fail without computer_mode)
- Argument validation (missing required args)
- Active window enforcement in permission_engine.py
- Handler logic (mocked Win32 calls to avoid actual mouse/keyboard events)
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """FastAPI test client with isolated data directory."""
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def computer_mode_context() -> dict:
    return {"computer_mode": True}


def _approved_context(client: TestClient, tool_name: str, arguments: dict) -> dict:
    """Create and approve a confirmation bound to this exact tool/payload, and
    return a computer_mode context carrying its confirmation_id.

    computer_type_text/computer_click/computer_click_element/
    computer_set_text_element all require an approved confirmation
    (see permission_engine.check_permission) — tests exercising their
    handler logic need one bound to the exact arguments under test.
    """
    created = client.post(
        "/confirmations",
        json={
            "action_name": tool_name,
            "payload": arguments,
            "risk_level": "high",
            "tool_name": tool_name,
        },
    )
    assert created.status_code == 200
    confirmation_id = created.json()["id"]
    approved = client.post(f"/confirmations/{confirmation_id}/approve")
    assert approved.status_code == 200
    return {"computer_mode": True, "confirmation_id": confirmation_id}


# ---------------------------------------------------------------------------
# /tools listing tests
# ---------------------------------------------------------------------------


def test_computer_tools_are_listed(client: TestClient) -> None:
    """All 5 computer_* tools appear in the /tools listing with correct metadata."""
    response = client.get("/tools")
    assert response.status_code == 200
    tools = {t["name"]: t for t in response.json()["tools"]}

    for name in ("computer_open_app", "computer_type_text", "computer_press_key", "computer_click", "computer_scroll"):
        assert name in tools, f"{name} missing from /tools"
        t = tools[name]
        assert t["risk"] in ("medium", "high"), f"{name} risk={t['risk']}"
        assert t["requires_computer_mode"] is True, f"{name} should require computer mode"
        assert t["implemented_by"] == "python"
        assert t["enabled"] is True

    # Echo should still be there (regression check)
    assert "echo" in tools


# ---------------------------------------------------------------------------
# Computer mode enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name,args", [
    ("computer_open_app", {"appName": "notepad"}),
    ("computer_type_text", {"text": "hello"}),
    ("computer_press_key", {"key": "enter"}),
    ("computer_click", {"x": 100, "y": 200}),
    ("computer_scroll", {"direction": "down"}),
])
def test_computer_tool_fails_without_computermode(client: TestClient, tool_name: str, args: dict) -> None:
    """Every computer_* tool must return COMPUTER_MODE_REQUIRED without context.computer_mode."""
    response = client.post(
        "/tools/execute",
        json={"tool_name": tool_name, "arguments": args, "context": {"computer_mode": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "COMPUTER_MODE_REQUIRED"


# ---------------------------------------------------------------------------
# Argument validation (these reach the handler; Win32 calls are NOT mocked,
# so they will fail on non-Windows — skip those, but test arg logic on any OS
# by mocking the platform check)
# ---------------------------------------------------------------------------


# computer_type_text and computer_click require an approved confirmation
# (see permission_engine.check_permission) — that check runs before argument
# validation, so these two need a confirmation bound to the exact payload
# under test to reach INVALID_ARGUMENTS at all. The other tools here don't
# require confirmation, so they use the plain computer_mode_context fixture.
NEEDS_CONFIRMATION = {"computer_type_text", "computer_click"}


@pytest.mark.parametrize("tool_name,args,expected_code", [
    ("computer_open_app", {}, "INVALID_ARGUMENTS"),         # missing appName
    ("computer_open_app", {"appName": ""}, "INVALID_ARGUMENTS"),   # empty appName
    ("computer_type_text", {}, "INVALID_ARGUMENTS"),        # missing text
    ("computer_type_text", {"text": ""}, "INVALID_ARGUMENTS"),      # empty text
    ("computer_press_key", {}, "INVALID_ARGUMENTS"),        # missing key
    ("computer_press_key", {"key": "f1"}, "INVALID_ARGUMENTS"),     # unsupported key
    ("computer_click", {}, "INVALID_ARGUMENTS"),            # missing x,y
    ("computer_click", {"x": 100}, "INVALID_ARGUMENTS"),    # missing y
    ("computer_scroll", {}, "INVALID_ARGUMENTS"),           # missing direction
    ("computer_scroll", {"direction": "diagonal"}, "INVALID_ARGUMENTS"),  # unsupported dir
])
def test_computer_tool_invalid_args(
    client: TestClient, tool_name: str, args: dict, expected_code: str, computer_mode_context: dict
) -> None:
    """Argument validation errors are returned before any Win32 call.

    On non-Windows, the handlers also raise RuntimeError — but if we mock
    sys.platform, we can test the arg parsing without Win32.
    """
    context = (
        _approved_context(client, tool_name, args) if tool_name in NEEDS_CONFIRMATION else computer_mode_context
    )
    with patch.object(sys, "platform", "win32"), patch("ctypes.windll", create=True):
        response = client.post(
            "/tools/execute",
            json={"tool_name": tool_name, "arguments": args, "context": context},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == expected_code


# ---------------------------------------------------------------------------
# Handler unit tests (mocked Win32) — only runnable on any OS since we mock
# ---------------------------------------------------------------------------


class TestComputerOpenApp:
    def test_missing_appname_raises(self) -> None:
        from app.tools.system.computer import _handle_open_app
        with pytest.raises(ValueError, match="appName"):
            _handle_open_app({})

    def test_empty_appname_raises(self) -> None:
        from app.tools.system.computer import _handle_open_app
        with pytest.raises(ValueError, match="appName"):
            _handle_open_app({"appName": ""})

    def test_opens_with_startfile(self) -> None:
        from app.tools.system.computer import _handle_open_app
        with patch.object(sys, "platform", "win32"), patch("os.startfile") as mock_startfile:
            result = _handle_open_app({"appName": "notepad"})
            mock_startfile.assert_called_once_with("notepad")
            assert result["app_name"] == "notepad"
            assert "Opened" in result["message"]

    def test_falls_back_to_popen(self) -> None:
        from app.tools.system.computer import _handle_open_app
        with patch.object(sys, "platform", "win32"), patch("os.startfile", side_effect=OSError), \
             patch("subprocess.Popen") as mock_popen:
            result = _handle_open_app({"appName": "chrome"})
            mock_popen.assert_called_once_with("chrome", shell=True)
            assert result["app_name"] == "chrome"


class TestComputerTypeText:
    def test_missing_text_raises(self) -> None:
        from app.tools.system.computer import _handle_type_text
        with pytest.raises(ValueError, match="text"):
            _handle_type_text({})

    def test_empty_text_raises(self) -> None:
        from app.tools.system.computer import _handle_type_text
        with pytest.raises(ValueError, match="text"):
            _handle_type_text({"text": ""})

    def test_unicode_key_sends_correct_count(self) -> None:
        from app.tools.system.computer import _handle_type_text, _send_input
        with patch.object(sys, "platform", "win32"), \
             patch("app.tools.system.computer._send_input", wraps=_send_input) as mock_send, \
             patch("ctypes.windll", create=True):
            # _send_input gets a real ctypes call into windll which we mocked.
            # The mock ctypes.windll means SendInput returns 0, but the struct
            # packing still works. We just count calls.
            result = _handle_type_text({"text": "ab"})
        assert result["length"] == 2
        # Each char sends 2 events (down + up) = 4 calls for "ab"
        # On Windows with real windll, _send_input is called; with our mock it
        # still gets called 4 times (2 per char).
        assert mock_send.call_count >= 2  # at least one call per char

    def test_newline_becomes_enter(self) -> None:
        from app.tools.system.computer import _handle_type_text
        with patch.object(sys, "platform", "win32"), \
             patch("app.tools.system.computer._press_key") as mock_press, \
             patch("app.tools.system.computer._type_unicode_char") as mock_unicode:
            _handle_type_text({"text": "a\nb"})
        # enter key should have been pressed once for the newline
        enter_vk = 0x0D
        mock_press.assert_any_call(enter_vk)
        # 'a' and 'b' should each get _type_unicode_char
        assert mock_unicode.call_count == 2


class TestComputerPressKey:
    def test_missing_key_raises(self) -> None:
        from app.tools.system.computer import _handle_press_key
        with pytest.raises(ValueError, match="key"):
            _handle_press_key({})

    def test_unsupported_key_raises(self) -> None:
        from app.tools.system.computer import _handle_press_key
        with pytest.raises(ValueError, match="Unsupported key"):
            _handle_press_key({"key": "f1"})

    def test_valid_key_returns_message(self) -> None:
        from app.tools.system.computer import _handle_press_key
        with patch.object(sys, "platform", "win32"), \
             patch("app.tools.system.computer._press_key") as mock_press, \
             patch("ctypes.windll", create=True):
            result = _handle_press_key({"key": "enter"})
        assert result["key"] == "enter"
        assert result["repeat"] == 1
        mock_press.assert_called_once()

    def test_repeat_multiplies(self) -> None:
        from app.tools.system.computer import _handle_press_key
        with patch.object(sys, "platform", "win32"), \
             patch("app.tools.system.computer._press_key") as mock_press, \
             patch("ctypes.windll", create=True):
            result = _handle_press_key({"key": "tab", "repeat": 3})
        assert result["key"] == "tab"
        assert result["repeat"] == 3
        assert mock_press.call_count == 3

    def test_repeat_clamped_to_20(self) -> None:
        from app.tools.system.computer import _handle_press_key
        with patch.object(sys, "platform", "win32"), \
             patch("app.tools.system.computer._press_key") as mock_press, \
             patch("ctypes.windll", create=True):
            result = _handle_press_key({"key": "space", "repeat": 100})
        assert result["repeat"] == 20
        assert mock_press.call_count == 20


class TestComputerClick:
    def test_missing_x_raises(self) -> None:
        from app.tools.system.computer import _handle_click
        with pytest.raises(ValueError, match="x and y"):
            _handle_click({"x": 100})

    def test_missing_y_raises(self) -> None:
        from app.tools.system.computer import _handle_click
        with pytest.raises(ValueError, match="x and y"):
            _handle_click({"y": 200})

    def test_click_moves_and_clicks(self) -> None:
        from app.tools.system.computer import _handle_click
        with patch.object(sys, "platform", "win32"), \
             patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.SetCursorPos = MagicMock()
            mock_windll.user32.mouse_event = MagicMock()
            result = _handle_click({"x": 150, "y": 350})
        assert result["x"] == 150
        assert result["y"] == 350
        mock_windll.user32.SetCursorPos.assert_called_once_with(150, 350)
        assert mock_windll.user32.mouse_event.call_count == 2  # down + up


class TestComputerScroll:
    def test_missing_direction_raises(self) -> None:
        from app.tools.system.computer import _handle_scroll
        with pytest.raises(ValueError, match="direction"):
            _handle_scroll({})

    def test_bad_direction_raises(self) -> None:
        from app.tools.system.computer import _handle_scroll
        with pytest.raises(ValueError, match="Unsupported scroll direction"):
            _handle_scroll({"direction": "diagonal"})

    @pytest.mark.parametrize("direction,expected_dw", [
        ("up", 480),     # 120 * 4 (default amount)
        ("down", -480),
        ("left", -480),
        ("right", 480),
    ])
    def test_scroll_directions(self, direction: str, expected_dw: int) -> None:
        from app.tools.system.computer import _handle_scroll
        with patch.object(sys, "platform", "win32"), \
             patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.mouse_event = MagicMock()
            result = _handle_scroll({"direction": direction})
        assert result["direction"] == direction
        # mouse_event called once with correct dwData
        call_args = mock_windll.user32.mouse_event.call_args[0]
        assert call_args[3] == expected_dw

    def test_amount_clamped(self) -> None:
        from app.tools.system.computer import _handle_scroll
        with patch.object(sys, "platform", "win32"), \
             patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.mouse_event = MagicMock()
            result = _handle_scroll({"direction": "up", "amount": 50})
        assert result["amount"] == 20
        call_args = mock_windll.user32.mouse_event.call_args[0]
        assert call_args[3] == 120 * 20  # clamped

    def test_amount_minimum_1(self) -> None:
        from app.tools.system.computer import _handle_scroll
        with patch.object(sys, "platform", "win32"), \
             patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.mouse_event = MagicMock()
            result = _handle_scroll({"direction": "down", "amount": 0})
        assert result["amount"] == 1


# ---------------------------------------------------------------------------
# Active window enforcement (permission_engine.py)
# ---------------------------------------------------------------------------


class TestActiveWindowEnforcement:
    def test_no_enforcement_when_flag_false(self) -> None:
        """check_active_window returns None when requires_active_window_match=False."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=False,
            allowed_apps=["notepad.exe"],
            blocked_apps=["chrome.exe"],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        assert check_active_window(tool) is None

    def test_no_enforcement_when_no_lists(self) -> None:
        """check_active_window returns None when lists are empty even if flag is True."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=[],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        assert check_active_window(tool) is None

    def test_non_windows_returns_none_gracefully(self) -> None:
        """On non-Windows, _get_active_window_process returns None, and
        check_active_window fails closed with ACTIVE_WINDOW_UNKNOWN."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=["notepad.exe"],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        with patch.object(sys, "platform", "linux"):
            error = check_active_window(tool)
        assert error is not None
        assert error.code == "ACTIVE_WINDOW_UNKNOWN"

    def test_blocked_app_fails(self) -> None:
        """Tool fails when active window is in blocked_apps."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=[],
            blocked_apps=["chrome.exe"],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        with patch("app.agent.permission_engine._get_active_window_process", return_value="chrome.exe"):
            error = check_active_window(tool)
        assert error is not None
        assert error.code == "ACTIVE_WINDOW_BLOCKED"

    def test_allowed_app_mismatch_fails(self) -> None:
        """Tool fails when active window is not in allowed_apps."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=["notepad.exe"],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        with patch("app.agent.permission_engine._get_active_window_process", return_value="chrome.exe"):
            error = check_active_window(tool)
        assert error is not None
        assert error.code == "ACTIVE_WINDOW_NOT_ALLOWED"

    def test_allowed_app_passes(self) -> None:
        """Tool passes when active window is in allowed_apps."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=["notepad.exe", "calc.exe"],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        with patch("app.agent.permission_engine._get_active_window_process", return_value="notepad.exe"):
            error = check_active_window(tool)
        assert error is None

    def test_case_insensitive_match(self) -> None:
        """allowed_apps matching is case-insensitive."""
        from app.agent.permission_engine import check_active_window
        from app.schemas.tool import ToolDefinition

        tool = ToolDefinition(
            name="test",
            description="test",
            input_schema={},
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=True,
            allowed_apps=["Notepad.EXE"],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=1000,
            implemented_by="python",
            enabled=True,
        )
        with patch("app.agent.permission_engine._get_active_window_process", return_value="notepad.exe"):
            error = check_active_window(tool)
        assert error is None


# ---------------------------------------------------------------------------
# Active window enforcement — real registered tools, not a synthetic
# ToolDefinition. The unit tests above prove check_active_window() itself is
# correct in isolation; these prove the actual computer_* tools registered in
# tool_registry.py are wired to it with a real blocked_apps list, not just
# that the mechanism exists somewhere in the codebase unused.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name,args", [
    ("computer_press_key", {"key": "enter"}),
    ("computer_scroll", {"direction": "down"}),
])
def test_registered_tool_blocked_when_active_window_is_dangerous(
    client: TestClient, tool_name: str, args: dict
) -> None:
    """computer_press_key/computer_scroll (no confirmation needed) must still
    be refused when the real foreground window is on the default blocklist
    (SECURITY_HARDENING_PLAN.md section 9), via the actual registered tool
    definition — not a hand-built ToolDefinition in the unit tests above."""
    with patch("app.agent.permission_engine._get_active_window_process", return_value="powershell.exe"):
        response = client.post(
            "/tools/execute",
            json={"tool_name": tool_name, "arguments": args, "context": {"computer_mode": True}},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "ACTIVE_WINDOW_BLOCKED"


def test_registered_computer_click_requires_confirmation(client: TestClient) -> None:
    """computer_click is risk=high and must require an approved confirmation_id,
    not just Computer Mode — matches computer_click_element's existing gate."""
    response = client.post(
        "/tools/execute",
        json={"tool_name": "computer_click", "arguments": {"x": 10, "y": 10}, "context": {"computer_mode": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_registered_computer_type_text_requires_confirmation(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "computer_type_text", "arguments": {"text": "hi"}, "context": {"computer_mode": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_registered_computer_click_succeeds_with_approved_confirmation(client: TestClient) -> None:
    """End-to-end: propose, approve, then execute with the bound confirmation_id
    and a safe (non-blocked) active window — should actually run."""
    args = {"x": 42, "y": 43}
    context = _approved_context(client, "computer_click", args)
    with patch.object(sys, "platform", "win32"), \
         patch("ctypes.windll", create=True) as mock_windll, \
         patch("app.agent.permission_engine._get_active_window_process", return_value="notepad.exe"):
        mock_windll.user32.SetCursorPos = MagicMock()
        mock_windll.user32.mouse_event = MagicMock()
        response = client.post(
            "/tools/execute",
            json={"tool_name": "computer_click", "arguments": args, "context": context},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["x"] == 42


# ---------------------------------------------------------------------------
# Regression: existing tools still work
# ---------------------------------------------------------------------------


def test_echo_still_works(client: TestClient) -> None:
    """FAZA 13 should not break the echo tool."""
    response = client.post(
        "/tools/execute",
        json={"tool_name": "echo", "arguments": {"text": "hello faza13"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"] == {"text": "hello faza13"}


def test_note_add_still_works(client: TestClient) -> None:
    """FAZA 13 should not break FAZA 11 memory tools."""
    response = client.post(
        "/tools/execute",
        json={"tool_name": "note_add", "arguments": {"text": "faza13 note"}},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True