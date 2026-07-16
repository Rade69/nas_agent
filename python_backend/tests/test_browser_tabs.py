"""Tests for the browser_tabs tool (PR 1 — list, activate, close)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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
        json={
            "tool_name": "browser_tabs",
            "arguments": arguments,
            "context": {"computer_mode": True},
        },
    )
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# Tool definition smoke tests
# ---------------------------------------------------------------------------


def test_browser_tabs_is_listed(client: TestClient) -> None:
    tools = {tool["name"]: tool for tool in client.get("/tools").json()["tools"]}
    tool = tools["browser_tabs"]
    assert tool["risk"] == "medium"
    assert tool["requires_computer_mode"] is True
    assert tool["requires_confirmation"] is False
    assert tool["implemented_by"] == "python"


# ---------------------------------------------------------------------------
# Action validation
# ---------------------------------------------------------------------------


def test_list_defaults_action(client: TestClient) -> None:
    """action is required by schema; omit gets INVALID_ARGUMENTS."""
    body = _execute(client, {})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_rejects_invalid_action(client: TestClient) -> None:
    body = _execute(client, {"action": "hack_tabs"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_list_accepts_valid_scope(client: TestClient) -> None:
    """All valid scopes pass validation even if broker isn't running."""
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        side_effect=RuntimeError("not initialized"),
    ):
        for scope in ["current_window", "all_windows"]:
            body = _execute(client, {"action": "list", "scope": scope})
            assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_rejects_invalid_scope(client: TestClient) -> None:
    body = _execute(client, {"action": "list", "scope": "any_window"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------------------
# Browser validation and "brejv" normalization
# ---------------------------------------------------------------------------


def test_brejv_normalizes_to_brave(client: TestClient) -> None:
    """Phonetic 'brejv' is accepted and normalized to 'brave'."""
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {"action": "list", "browser": "brejv"})
        # Should reach the broker (which then fails) — not fail validation
        assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_brave_is_valid_browser(client: TestClient) -> None:
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {"action": "list", "browser": "brave"})
        assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_chrome_is_valid_browser(client: TestClient) -> None:
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {"action": "list", "browser": "chrome"})
        assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_rejects_unknown_browser(client: TestClient) -> None:
    body = _execute(client, {"action": "list", "browser": "firefox"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------------------
# Snapshot / positional argument validation (activate/close stubs)
# ---------------------------------------------------------------------------


def test_activate_requires_snapshot_id(client: TestClient) -> None:
    body = _execute(client, {"action": "activate", "browser": "brave", "position": 1})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_activate_rejects_zero_position(client: TestClient) -> None:
    body = _execute(client, {
        "action": "activate",
        "browser": "brave",
        "snapshot_id": "snap-test-123",
        "position": 0,
    })
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_activate_rejects_negative_position(client: TestClient) -> None:
    body = _execute(client, {
        "action": "activate",
        "browser": "brave",
        "snapshot_id": "snap-test-123",
        "position": -1,
    })
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_close_requires_snapshot_id(client: TestClient) -> None:
    body = _execute(client, {"action": "close", "browser": "brave", "position": 1})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------------------
# Successful list (mocked broker)
# ---------------------------------------------------------------------------


_SAMPLE_TABS = [
    {
        "position": 1,
        "tab_id": "t-101",
        "title": "YouTube",
        "url": "https://www.youtube.com/",
        "active": False,
        "pinned": False,
        "audible": False,
        "incognito": False,
        "window_id": "w-17",
    },
    {
        "position": 2,
        "tab_id": "t-102",
        "title": "GitHub",
        "url": "https://github.com/",
        "active": True,
        "pinned": False,
        "audible": False,
        "incognito": False,
        "window_id": "w-17",
    },
    {
        "position": 3,
        "tab_id": "t-103",
        "title": "Example",
        "url": "https://example.com/",
        "active": False,
        "pinned": True,
        "audible": True,
        "incognito": False,
        "window_id": "w-17",
    },
]


def test_list_returns_structured_snapshot(client: TestClient) -> None:
    """Mocked list returns correct snapshot shape."""
    mock_broker = MagicMock()
    mock_broker.list_tabs = AsyncMock(return_value={
        "browser": "brave",
        "scope": "current_window",
        "window_id": "w-17",
        "snapshot_id": "tabsnap-abc123",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": 3,
        "tabs": _SAMPLE_TABS,
        "message": "3 tab(s) in brave: 1. YouTube, 2. GitHub, 3. Example",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {"action": "list", "browser": "brave"})

    assert body["ok"] is True
    result = body["result"]
    assert result["browser"] == "brave"
    assert result["snapshot_id"] == "tabsnap-abc123"
    assert result["count"] == 3
    assert len(result["tabs"]) == 3
    assert result["tabs"][1]["position"] == 2  # 1-based
    assert result["tabs"][1]["title"] == "GitHub"
    mock_broker.list_tabs.assert_awaited_once_with(scope="current_window")


def test_list_all_windows_scope(client: TestClient) -> None:
    mock_broker = MagicMock()
    mock_broker.list_tabs = AsyncMock(return_value={
        "browser": "chrome",
        "scope": "all_windows",
        "window_id": None,
        "snapshot_id": "tabsnap-def456",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": 0,
        "tabs": [],
        "message": "No tabs open in the active chrome window.",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "list",
            "browser": "chrome",
            "scope": "all_windows",
        })

    assert body["ok"] is True
    assert body["result"]["count"] == 0
    assert body["result"]["scope"] == "all_windows"
    mock_broker.list_tabs.assert_awaited_once_with(scope="all_windows")


# ---------------------------------------------------------------------------
# PR 2: activate tab tests
# ---------------------------------------------------------------------------


def test_activate_succeeds_with_valid_snapshot(client: TestClient) -> None:
    """Activate with a valid snapshot resolves tab_id and returns success."""
    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(return_value={
        "ok": True,
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 2,
        "tab_id": "t-102",
        "title": "GitHub",
        "url": "https://github.com/",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "tabsnap-abc123",
            "position": 2,
        })

    assert body["ok"] is True
    result = body["result"]
    assert result["position"] == 2
    assert result["title"] == "GitHub"
    assert "GitHub" in result["message"]
    assert "drugi" in result["message"] or "2." in result["message"]
    mock_broker.activate_tab.assert_awaited_once_with(
        snapshot_id="tabsnap-abc123",
        position=2,
        browser="brave",
    )


def test_activate_first_and_last_tab(client: TestClient) -> None:
    """Activate works for first (1) and last (N) positions."""
    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(side_effect=[
        {"ok": True, "snapshot_id": "s1", "position": 1, "tab_id": "t-1", "title": "First"},
        {"ok": True, "snapshot_id": "s1", "position": 6, "tab_id": "t-6", "title": "Last"},
    ])

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body1 = _execute(client, {
            "action": "activate", "browser": "brave",
            "snapshot_id": "s1", "position": 1,
        })
        body2 = _execute(client, {
            "action": "activate", "browser": "brave",
            "snapshot_id": "s1", "position": 6,
        })

    assert body1["ok"] is True
    assert body1["result"]["position"] == 1
    assert body2["ok"] is True
    assert body2["result"]["position"] == 6


def test_activate_stale_snapshot_error(client: TestClient) -> None:
    """When broker raises TAB_SNAPSHOT_STALE, tool returns the error."""
    from app.core.errors import AppError

    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(
        side_effect=AppError(
            "TAB_SNAPSHOT_STALE",
            "The tab list snapshot has expired.",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "expired-snap",
            "position": 3,
        })

    assert body["ok"] is False
    assert body["error"]["code"] == "TAB_SNAPSHOT_STALE"


def test_activate_tab_not_found_in_stale_snapshot(client: TestClient) -> None:
    """When tab at position no longer exists, error maps to TAB_SNAPSHOT_STALE."""
    from app.core.errors import AppError

    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(
        side_effect=AppError(
            "TAB_SNAPSHOT_STALE",
            "Tab at position 3 no longer exists. Please list tabs again.",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "stale-but-not-expired",
            "position": 3,
        })

    assert body["ok"] is False
    assert body["error"]["code"] == "TAB_SNAPSHOT_STALE"


def test_activate_position_out_of_range(client: TestClient) -> None:
    """Position beyond the list gives TAB_POSITION_OUT_OF_RANGE."""
    from app.core.errors import AppError

    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(
        side_effect=AppError(
            "TAB_POSITION_OUT_OF_RANGE",
            "Position 99 is out of range (1–3).",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "snap",
            "position": 99,
        })

    assert body["ok"] is False
    assert body["error"]["code"] == "TAB_POSITION_OUT_OF_RANGE"


def test_activate_rejects_incognito(client: TestClient) -> None:
    """Incognito tabs are rejected with INCOGNITO_NOT_ALLOWED."""
    from app.core.errors import AppError

    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(
        side_effect=AppError(
            "INCOGNITO_NOT_ALLOWED",
            "Incognito tabs are excluded by default.",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "snap",
            "position": 2,
        })

    assert body["ok"] is False
    assert body["error"]["code"] == "INCOGNITO_NOT_ALLOWED"


def test_activate_extension_not_connected(client: TestClient) -> None:
    """When broker isn't initialized, returns BROWSER_EXTENSION_NOT_CONNECTED."""
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brave",
            "snapshot_id": "snap",
            "position": 1,
        })

    assert body["ok"] is False
    assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_activate_brejv_normalized(client: TestClient) -> None:
    """'brejv' browser is normalized to 'brave' for activate too."""
    mock_broker = MagicMock()
    mock_broker.activate_tab = AsyncMock(return_value={
        "ok": True,
        "browser": "brave",
        "snapshot_id": "snap",
        "position": 1,
        "tab_id": "t-1",
        "title": "Test",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute(client, {
            "action": "activate",
            "browser": "brejv",
            "snapshot_id": "snap",
            "position": 1,
        })

    assert body["ok"] is True
    mock_broker.activate_tab.assert_awaited_once_with(
        snapshot_id="snap",
        position=1,
        browser="brave",
    )


# ---------------------------------------------------------------------------
# Snapshot store unit tests
# ---------------------------------------------------------------------------


def test_snapshot_store_ttl_expiry() -> None:
    """Snapshot expires after TTL and returns None."""
    import time
    from app.services.browser_extension_broker import SnapshotStore

    store = SnapshotStore(ttl_seconds=1)
    store.store("snap-1", {"tabs": _SAMPLE_TABS, "count": 3})

    # Fresh snapshot is available
    assert store.get("snap-1") is not None

    # After 1.1s, it should be expired
    time.sleep(1.1)
    assert store.get("snap-1") is None


def test_snapshot_store_cleanup_on_store() -> None:
    """Storing a new snapshot cleans up stale ones."""
    import time
    from app.services.browser_extension_broker import SnapshotStore

    store = SnapshotStore(ttl_seconds=0)
    store.store("snap-stale", {"tabs": []})
    store.get("snap-stale")  # triggers expiry check
    assert store.get("snap-stale") is None

    store = SnapshotStore(ttl_seconds=60)
    store.store("snap-a", {"tabs": [{"id": 1}]})
    store.store("snap-b", {"tabs": [{"id": 2}]})
    assert store.get("snap-a") is not None
    assert store.get("snap-b") is not None


def test_snapshot_store_unknown_snapshot() -> None:
    from app.services.browser_extension_broker import SnapshotStore

    store = SnapshotStore()
    assert store.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Broker pairing secret
# ---------------------------------------------------------------------------


def test_broker_ensure_secret_generates_and_persists(tmp_path) -> None:
    from app.services.browser_extension_broker import BrowserExtensionBroker

    broker = BrowserExtensionBroker(tmp_path)
    secret1 = broker.ensure_secret()
    assert len(secret1) == 64  # 32 bytes = 64 hex chars

    # Secret file should exist
    assert broker.secret_file.exists()
    assert broker.secret_file.read_text().strip() == secret1

    # Reload — should return same secret
    broker2 = BrowserExtensionBroker(tmp_path)
    secret2 = broker2.ensure_secret()
    assert secret2 == secret1


def test_broker_pairing_display() -> None:
    from app.services.browser_extension_broker import BrowserExtensionBroker

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        from pathlib import Path
        broker = BrowserExtensionBroker(Path(tmp))
        display = broker.get_pairing_display()
        assert len(display) == 9  # 8 chars + …
        assert display.endswith("…")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_tab_entry_1_based() -> None:
    from app.schemas.browser_tabs import TabEntry

    tab = TabEntry(
        position=1,
        tab_id="t-1",
        title="Test",
        url="https://test.com",
        active=True,
        pinned=False,
        audible=False,
        incognito=False,
        window_id="w-1",
    )
    assert tab.position == 1


def test_tab_snapshot_created_at_is_utc() -> None:
    from app.schemas.browser_tabs import TabSnapshot

    snap = TabSnapshot(
        snapshot_id="snap-1",
        browser="brave",
        scope="current_window",
        window_id="w-1",
        created_at=datetime.now(timezone.utc),
        count=0,
        tabs=[],
    )
    assert snap.created_at.tzinfo is not None


def test_browser_tab_error_codes_have_all_required() -> None:
    from app.schemas.browser_tabs import BROWSER_TAB_ERROR_CODES

    required = {
        "BROWSER_EXTENSION_NOT_CONNECTED",
        "BROWSER_EXTENSION_AUTH_FAILED",
        "BROWSER_PROFILE_NOT_FOUND",
        "BROWSER_WINDOW_NOT_FOUND",
        "TAB_NOT_FOUND",
        "TAB_POSITION_OUT_OF_RANGE",
        "TAB_SNAPSHOT_STALE",
        "TAB_ACTION_TIMEOUT",
        "TAB_ACTION_FAILED",
        "INCOGNITO_NOT_ALLOWED",
    }
    assert set(BROWSER_TAB_ERROR_CODES.keys()) == required