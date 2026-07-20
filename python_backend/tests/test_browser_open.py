"""Tests for the safe browser_open tool and its structured launch errors."""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def _execute(client: TestClient, arguments: dict) -> dict:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "browser_open", "arguments": arguments, "context": {"computer_mode": True}},
    )
    assert response.status_code == 200
    return response.json()


def test_browser_open_is_listed(client: TestClient) -> None:
    tools = {tool["name"]: tool for tool in client.get("/tools").json()["tools"]}
    tool = tools["browser_open"]
    assert tool["risk"] == "medium"
    # c58d6eb: browser_open je namjerno skinut sa Computer Mode requirement-a.
    # Otvaranje browsera na validiranom URL-u je benigno kao i web_search,
    # URL validacija + shell=False + medium risk i dalje štite.
    assert tool["requires_computer_mode"] is False
    assert tool["implemented_by"] == "python"


def test_browser_open_rejects_unsafe_url(client: TestClient) -> None:
    body = _execute(client, {"browser": "default", "url": "file:///C:/Windows/System32/calc.exe"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_browser_open_rejects_embedded_credentials(client: TestClient) -> None:
    body = _execute(client, {"browser": "default", "url": "https://user:secret@example.com"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_specific_browser_launch_returns_structured_result(client: TestClient) -> None:
    process = Mock(pid=4321)
    with (
        patch("app.tools.system.browser.sys.platform", "win32"),
        patch("app.tools.system.browser._find_browser", return_value=r"C:\\Chrome\\chrome.exe"),
        patch("app.tools.system.browser.subprocess.Popen", return_value=process) as popen,
    ):
        body = _execute(client, {"browser": "chrome", "url": "https://example.com"})

    assert body["ok"] is True
    assert body["result"] == {
        "message": "Opened chrome.",
        "browser": "chrome",
        "url": "https://example.com",
        "launch_accepted": True,
        "process_started": True,
        "process_id": 4321,
    }
    popen.assert_called_once_with([r"C:\\Chrome\\chrome.exe", "https://example.com"], shell=False)


def test_spoken_brejv_alias_launches_brave(client: TestClient) -> None:
    process = Mock(pid=9876)
    with (
        patch("app.tools.system.browser.sys.platform", "win32"),
        patch("app.tools.system.browser._find_browser", return_value=r"C:\\Brave\\brave.exe") as find_browser,
        patch("app.tools.system.browser.subprocess.Popen", return_value=process) as popen,
    ):
        body = _execute(client, {"browser": "brejv"})

    assert body["ok"] is True
    assert body["result"]["browser"] == "brave"
    assert body["result"]["message"] == "Opened brave."
    find_browser.assert_called_once_with("brave")
    popen.assert_called_once_with([r"C:\\Brave\\brave.exe", "about:blank"], shell=False)


def test_missing_browser_has_precise_error_code(client: TestClient) -> None:
    with (
        patch("app.tools.system.browser.sys.platform", "win32"),
        patch("app.tools.system.browser._find_browser", return_value=None),
    ):
        body = _execute(client, {"browser": "firefox"})

    assert body["ok"] is False
    assert body["error"]["code"] == "BROWSER_NOT_INSTALLED"


def test_default_browser_uses_registered_windows_handler(client: TestClient) -> None:
    with (
        patch("app.tools.system.browser.sys.platform", "win32"),
        patch("app.tools.system.browser.webbrowser.open", return_value=True) as open_default,
    ):
        body = _execute(client, {"browser": "default", "url": "https://example.com/docs"})

    assert body["ok"] is True
    assert body["result"]["browser"] == "default"
    assert body["result"]["launch_accepted"] is True
    open_default.assert_called_once_with("https://example.com/docs", new=1)
