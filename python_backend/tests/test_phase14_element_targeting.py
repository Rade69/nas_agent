"""Tests for FAZA 14 computer-use element targeting tools (UIA).

Covers:
- Tool registration (4 new tools in /tools)
- Computer mode enforcement
- Argument validation
- Handler unit tests (mocked UIA via sys.modules)
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app


# ---------------------------------------------------------------------------
# Helper: inject a fake uiautomation into sys.modules
# ---------------------------------------------------------------------------

def _mock_uia(**kwargs):
    """Return a MagicMock registered as sys.modules['uiautomation'].

    Caller should use it inside a `with patch.dict(sys.modules, {...}):` block.
    """
    mock = MagicMock(**kwargs)
    return {"uiautomation": mock}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


@pytest.fixture()
def computer_mode_context() -> dict:
    return {"computer_mode": True}


# ---------------------------------------------------------------------------
# /tools listing
# ---------------------------------------------------------------------------


def test_element_tools_are_listed(client: TestClient) -> None:
    response = client.get("/tools")
    assert response.status_code == 200
    tools = {t["name"]: t for t in response.json()["tools"]}

    for name in (
        "computer_find_elements",
        "computer_click_element",
        "computer_set_text_element",
        "computer_get_element_text",
    ):
        assert name in tools, f"{name} missing from /tools"
        t = tools[name]
        assert t["requires_computer_mode"] is True
        assert t["implemented_by"] == "python"
        assert t["enabled"] is True


# ---------------------------------------------------------------------------
# Computer mode enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name,args", [
    ("computer_find_elements", {"app": "notepad.exe"}),
    ("computer_click_element", {"app": "notepad.exe", "name": "OK"}),
    ("computer_set_text_element", {"text": "hello", "app": "notepad.exe"}),
    ("computer_get_element_text", {"app": "notepad.exe"}),
])
def test_element_tool_fails_without_computermode(
    client: TestClient, tool_name: str, args: dict
) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": tool_name, "arguments": args, "context": {"computer_mode": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "COMPUTER_MODE_REQUIRED"


# ---------------------------------------------------------------------------
# Confirmation + active window enforcement — real registered tools
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name,args", [
    ("computer_click_element", {"app": "notepad.exe", "name": "OK"}),
    ("computer_set_text_element", {"text": "hello", "app": "notepad.exe"}),
])
def test_element_write_tools_require_confirmation(
    client: TestClient, tool_name: str, args: dict
) -> None:
    """computer_click_element/computer_set_text_element are risk=high and
    must require an approved confirmation_id, not just Computer Mode."""
    response = client.post(
        "/tools/execute",
        json={"tool_name": tool_name, "arguments": args, "context": {"computer_mode": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_element_write_tool_blocked_when_active_window_is_dangerous(client: TestClient) -> None:
    """computer_click_element must be refused when the real foreground window
    is on the default blocklist, even with an approved confirmation."""
    args = {"app": "notepad.exe", "name": "OK"}
    created = client.post(
        "/confirmations",
        json={"action_name": "computer_click_element", "payload": args, "risk_level": "high", "tool_name": "computer_click_element"},
    )
    confirmation_id = created.json()["id"]
    client.post(f"/confirmations/{confirmation_id}/approve")

    with patch("app.agent.permission_engine._get_active_window_process", return_value="regedit.exe"):
        response = client.post(
            "/tools/execute",
            json={
                "tool_name": "computer_click_element",
                "arguments": args,
                "context": {"computer_mode": True, "confirmation_id": confirmation_id},
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "ACTIVE_WINDOW_BLOCKED"


# ---------------------------------------------------------------------------
# Handler unit tests (mocked UIA via sys.modules)
# ---------------------------------------------------------------------------


class TestFindElements:
    def test_no_criteria_raises(self) -> None:
        from app.tools.system.element_target import _handle_find_elements
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="At least one search criterion"):
                _handle_find_elements({})

    def test_no_criteria_empty_app_raises(self) -> None:
        from app.tools.system.element_target import _handle_find_elements
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="At least one search criterion"):
                _handle_find_elements({"app": "", "title_contains": ""})

    def test_no_windows_found_returns_empty(self) -> None:
        from app.tools.system.element_target import _handle_find_elements
        fake_root = MagicMock()
        fake_root.GetChildren.return_value = []
        mock_uia = {"uiautomation": MagicMock(GetRootControl=lambda: fake_root)}
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **mock_uia):
            result = _handle_find_elements({"app": "nonexistent.exe"})
        assert result["count"] == 0
        assert result["elements"] == []

    def test_finds_elements_by_control_type(self) -> None:
        from app.tools.system.element_target import _handle_find_elements
        fake_root = MagicMock()
        fake_window = MagicMock()
        fake_window.ClassName = "notepad.exe"
        fake_window.Name = "Untitled - Notepad"

        fake_edit = MagicMock()
        fake_edit.ControlTypeName = "Edit"
        fake_edit.Name = ""
        fake_edit.AutomationId = "15"
        fake_edit.ClassName = "Edit"
        fake_edit.BoundingRectangle = "0,0,500,300"
        fake_edit.IsEnabled = True

        fake_window.GetDescendants.return_value = [fake_edit]
        fake_root.GetChildren.return_value = [fake_window]
        mock_uia = {"uiautomation": MagicMock(GetRootControl=lambda: fake_root)}

        with patch("sys.platform", "win32"), patch.dict(sys.modules, **mock_uia):
            result = _handle_find_elements({"app": "notepad.exe", "control_type": "Edit"})
        assert result["count"] == 1
        assert result["elements"][0]["control_type"] == "Edit"


class TestClickElement:
    def test_no_app_or_title_raises(self) -> None:
        from app.tools.system.element_target import _handle_click_element
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="app or title_contains"):
                _handle_click_element({"control_type": "Button"})

    def test_clicks_element(self) -> None:
        from app.tools.system.element_target import _handle_click_element
        fake_root = MagicMock()
        fake_window = MagicMock()
        fake_window.ClassName = "notepad.exe"
        fake_window.Name = "Untitled - Notepad"
        fake_button = MagicMock()
        fake_button.ControlTypeName = "Button"
        fake_button.Name = "OK"
        fake_button.AutomationId = ""
        fake_button.ClassName = "Button"
        fake_button.BoundingRectangle = ""
        fake_button.IsEnabled = True
        fake_button.Click = MagicMock()
        fake_window.GetDescendants.return_value = [fake_button]
        fake_root.GetChildren.return_value = [fake_window]
        mock_uia = {"uiautomation": MagicMock(GetRootControl=lambda: fake_root)}

        with patch("sys.platform", "win32"), patch.dict(sys.modules, **mock_uia):
            result = _handle_click_element({"app": "notepad.exe", "control_type": "Button", "name": "OK"})
        assert "Clicked" in result["message"]
        fake_button.Click.assert_called_once()


class TestSetTextElement:
    def test_missing_text_raises(self) -> None:
        from app.tools.system.element_target import _handle_set_text_element
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="text"):
                _handle_set_text_element({"app": "notepad.exe"})

    def test_empty_text_raises(self) -> None:
        from app.tools.system.element_target import _handle_set_text_element
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="text"):
                _handle_set_text_element({"text": "", "app": "notepad.exe"})

    def test_no_app_or_title_raises(self) -> None:
        from app.tools.system.element_target import _handle_set_text_element
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="app or title_contains"):
                _handle_set_text_element({"text": "hello", "control_type": "Edit"})


class TestGetElementText:
    def test_no_app_or_title_raises(self) -> None:
        from app.tools.system.element_target import _handle_get_element_text
        with patch("sys.platform", "win32"), patch.dict(sys.modules, **_mock_uia()):
            with pytest.raises(ValueError, match="app or title_contains"):
                _handle_get_element_text({"control_type": "Edit"})

    def test_reads_value_pattern(self) -> None:
        from app.tools.system.element_target import _handle_get_element_text
        fake_root = MagicMock()
        fake_window = MagicMock()
        fake_window.ClassName = "notepad.exe"
        fake_window.Name = "Untitled - Notepad"

        fake_edit = MagicMock()
        fake_edit.ControlTypeName = "Edit"
        fake_edit.Name = ""
        fake_edit.AutomationId = "15"
        fake_edit.ClassName = "Edit"
        fake_edit.BoundingRectangle = ""
        fake_edit.IsEnabled = True
        fake_value = MagicMock()
        fake_value.Value = "Hello from Notepad"
        fake_edit.GetPattern.return_value = fake_value

        fake_window.GetDescendants.return_value = [fake_edit]
        fake_root.GetChildren.return_value = [fake_window]
        mock_uia = {
            "uiautomation": MagicMock(
                GetRootControl=lambda: fake_root,
                PatternId=MagicMock(ValuePattern=10002),
            )
        }

        with patch("sys.platform", "win32"), patch.dict(sys.modules, **mock_uia):
            result = _handle_get_element_text({"app": "notepad.exe", "control_type": "Edit"})
        assert result["text"] == "Hello from Notepad"
        assert result["source"] == "value"

    def test_falls_back_to_name_when_no_value_pattern(self) -> None:
        from app.tools.system.element_target import _handle_get_element_text
        fake_root = MagicMock()
        fake_window = MagicMock()
        fake_window.ClassName = "notepad.exe"
        fake_window.Name = "Untitled - Notepad"

        fake_label = MagicMock()
        fake_label.ControlTypeName = "Text"
        fake_label.Name = "Status: Ready"
        fake_label.AutomationId = ""
        fake_label.ClassName = "Static"
        fake_label.BoundingRectangle = ""
        fake_label.IsEnabled = True
        fake_label.GetPattern.side_effect = Exception("no value pattern")

        fake_window.GetDescendants.return_value = [fake_label]
        fake_root.GetChildren.return_value = [fake_window]
        mock_uia = {"uiautomation": MagicMock(GetRootControl=lambda: fake_root)}

        with patch("sys.platform", "win32"), patch.dict(sys.modules, **mock_uia):
            result = _handle_get_element_text({"app": "notepad.exe", "control_type": "Text"})
        assert result["text"] == "Status: Ready"
        assert result["source"] == "name"


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


def test_all_faza13_14_tools_visible(client: TestClient) -> None:
    """All 9 computer_* tools should be listed together."""
    response = client.get("/tools")
    tools = {t["name"] for t in response.json()["tools"]}

    expected = {
        "computer_open_app", "computer_type_text", "computer_press_key",
        "computer_click", "computer_scroll",
        "computer_find_elements", "computer_click_element",
        "computer_set_text_element", "computer_get_element_text",
    }
    assert expected.issubset(tools), f"Missing tools: {expected - tools}"