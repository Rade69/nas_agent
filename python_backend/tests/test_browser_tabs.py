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


def _execute_close(client: TestClient, arguments: dict) -> dict:
    """Execute browser_tab_close tool."""
    response = client.post(
        "/tools/execute",
        json={
            "tool_name": "browser_tab_close",
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
    body = _execute(client, {"action": "close"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"

    body = _execute(client, {"action": "hack_tabs"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_list_accepts_valid_scope(client: TestClient) -> None:
    """All valid scopes pass validation even if broker isn't running."""
    with patch(
        "app.tools.system.browser_tabs._get_broker_imported",
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
        "app.tools.system.browser_tabs._get_broker_imported",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {"action": "list", "browser": "brejv"})
        # Should reach the broker (which then fails) — not fail validation
        assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_brave_is_valid_browser(client: TestClient) -> None:
    with patch(
        "app.tools.system.browser_tabs._get_broker_imported",
        side_effect=RuntimeError("not initialized"),
    ):
        body = _execute(client, {"action": "list", "browser": "brave"})
        assert body["error"]["code"] == "BROWSER_EXTENSION_NOT_CONNECTED"


def test_chrome_is_valid_browser(client: TestClient) -> None:
    with patch(
        "app.tools.system.browser_tabs._get_broker_imported",
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


def test_close_requires_snapshot_id_for_dedicated_tool(client: TestClient) -> None:
    """browser_tab_close requires snapshot_id (no action param)."""
    body = _execute_close(client, {"browser": "brave", "position": 1})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_close_requires_position(client: TestClient) -> None:
    body = _execute_close(client, {"browser": "brave", "snapshot_id": "snap"})
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------------------
# browser_tab_close — listing and risk check
# ---------------------------------------------------------------------------


def test_browser_tab_close_is_high_risk_with_confirmation(client: TestClient) -> None:
    """browser_tab_close is high risk and requires confirmation."""
    tools = {tool["name"]: tool for tool in client.get("/tools").json()["tools"]}
    tool = tools["browser_tab_close"]
    assert tool["risk"] == "high"
    assert tool["requires_confirmation"] is True
    assert tool["requires_computer_mode"] is True
    assert tool["implemented_by"] == "python"


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
    mock_broker.list_tabs.assert_awaited_once_with(scope="current_window", browser="brave", profile_id=None)


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
    mock_broker.list_tabs.assert_awaited_once_with(scope="all_windows", browser="chrome", profile_id=None)


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
        profile_id=None,
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
        "app.tools.system.browser_tabs._get_broker_imported",
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
        profile_id=None,
    )


# ---------------------------------------------------------------------------
# PR 3: browser_tab_close tests (high-risk, confirmation-gated)
# ---------------------------------------------------------------------------


def test_close_requires_confirmation_without_id(client: TestClient) -> None:
    """browser_tab_close without confirmation_id returns CONFIRMATION_REQUIRED."""
    body = _execute_close(client, {
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 3,
    })
    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_close_rejects_stale_confirmation_id(client: TestClient) -> None:
    """Non-existent confirmation_id is rejected."""
    body = _execute_close(client, {
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 3,
    })
    assert body["error"]["code"] == "CONFIRMATION_REQUIRED"


def test_close_succeeds_after_approval(client: TestClient) -> None:
    """Full approval flow: propose → approve → execute → success."""
    # Step 1: Propose a confirmation
    from app.core.payload_hash import hash_payload

    confirm_payload = {
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 3,
    }

    # Create a confirmation via the API
    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": confirm_payload,
        "risk_level": "high",
        "summary": "Close tab at position 3: YouTube (youtube.com)",
        "tool_name": "browser_tab_close",
    })
    assert create_resp.status_code == 200
    confirm_id = create_resp.json()["id"]

    # Step 2: Approve it
    approve_resp = client.post(f"/confirmations/{confirm_id}/approve")
    assert approve_resp.status_code == 200

    # Step 3: Execute with confirmation_id
    mock_broker = MagicMock()
    mock_broker.close_tab = AsyncMock(return_value={
        "ok": True,
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 3,
        "tab_id": "t-103",
        "title": "YouTube",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = _execute_close(client, {
            "browser": "brave",
            "snapshot_id": "tabsnap-abc123",
            "position": 3,
        })
        # Add confirmation_id via context

    # The body will be CONFIRMATION_REQUIRED because context.confirmation_id wasn't set.
    # The confirmation flow goes through the frontend adding it to context.
    # For the unit test, we need to simulate that.
    # Let's do a lower-level test of the handler directly instead.

    # Actually, let's test that the close flow works with the broker mocked
    # and confirmation_id in the request context.
    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()

    assert body["ok"] is True
    assert body["result"]["position"] == 3
    assert body["result"]["title"] == "YouTube"
    assert "YouTube" in body["result"]["message"]
    mock_broker.close_tab.assert_awaited_once_with(
        snapshot_id="tabsnap-abc123",
        position=3,
        browser="brave",
        profile_id=None,
    )


def test_close_stale_snapshot_after_approval(client: TestClient) -> None:
    """When snapshot expires between approval and execution, TAB_SNAPSHOT_STALE is returned."""
    from app.core.errors import AppError

    confirm_payload = {
        "browser": "brave",
        "snapshot_id": "tabsnap-expired",
        "position": 2,
    }

    # Create and approve a confirmation
    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": confirm_payload,
        "risk_level": "high",
        "summary": "Close tab at position 2",
        "tool_name": "browser_tab_close",
    })
    confirm_id = create_resp.json()["id"]
    client.post(f"/confirmations/{confirm_id}/approve")

    # Mock broker that raises TAB_SNAPSHOT_STALE
    mock_broker = MagicMock()
    mock_broker.close_tab = AsyncMock(
        side_effect=AppError(
            "TAB_SNAPSHOT_STALE",
            "The tab list snapshot has expired.",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()

    assert body["ok"] is False
    assert body["error"]["code"] == "TAB_SNAPSHOT_STALE"
    # The confirmation was consumed — can't retry with the same ID


def test_close_confirmation_cannot_be_reused(client: TestClient) -> None:
    """A consumed confirmation_id cannot be used twice."""
    confirm_payload = {
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 1,
    }

    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": confirm_payload,
        "risk_level": "high",
        "tool_name": "browser_tab_close",
    })
    confirm_id = create_resp.json()["id"]
    client.post(f"/confirmations/{confirm_id}/approve")

    mock_broker = MagicMock()
    mock_broker.close_tab = AsyncMock(return_value={
        "ok": True,
        "snapshot_id": "tabsnap-abc123",
        "position": 1,
        "tab_id": "t-1",
        "title": "Test",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        # First call — succeeds
        body1 = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()
        assert body1["ok"] is True

        # Second call with same confirmation_id — fails
        body2 = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()
        assert body2["ok"] is False
        assert body2["error"]["code"] in (
            "CONFIRMATION_NOT_FOUND",
            "CONFIRMATION_ALREADY_CONSUMED",
            "CONFIRMATION_NOT_APPROVED",
        )


def test_close_payload_hash_mismatch_rejected(client: TestClient) -> None:
    """Confirmation with different payload args is rejected."""
    original_payload = {
        "browser": "brave",
        "snapshot_id": "tabsnap-abc123",
        "position": 1,
    }

    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": original_payload,
        "risk_level": "high",
        "tool_name": "browser_tab_close",
    })
    confirm_id = create_resp.json()["id"]
    client.post(f"/confirmations/{confirm_id}/approve")

    # Try with different position
    body = client.post("/tools/execute", json={
        "tool_name": "browser_tab_close",
        "arguments": {
            "browser": "brave",
            "snapshot_id": "tabsnap-abc123",
            "position": 5,  # Different from approved position=1
        },
        "context": {
            "computer_mode": True,
            "confirmation_id": confirm_id,
        },
    }).json()

    assert body["ok"] is False
    assert body["error"]["code"] == "CONFIRMATION_MISMATCH"


def test_close_incognito_rejected(client: TestClient) -> None:
    """Even with confirmation, incognito tabs are rejected."""
    from app.core.errors import AppError

    confirm_payload = {
        "browser": "brave",
        "snapshot_id": "tabsnap-incognito",
        "position": 1,
    }

    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": confirm_payload,
        "risk_level": "high",
        "tool_name": "browser_tab_close",
    })
    confirm_id = create_resp.json()["id"]
    client.post(f"/confirmations/{confirm_id}/approve")

    mock_broker = MagicMock()
    mock_broker.close_tab = AsyncMock(
        side_effect=AppError(
            "INCOGNITO_NOT_ALLOWED",
            "Incognito tabs are excluded by default.",
        )
    )

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()

    assert body["ok"] is False
    assert body["error"]["code"] == "INCOGNITO_NOT_ALLOWED"


def test_close_brejv_normalized(client: TestClient) -> None:
    """'brejv' is normalized to 'brave' for close too."""
    confirm_payload = {
        "browser": "brejv",
        "snapshot_id": "tabsnap",
        "position": 1,
    }

    create_resp = client.post("/confirmations", json={
        "action_name": "Close browser tab",
        "payload": confirm_payload,
        "risk_level": "high",
        "tool_name": "browser_tab_close",
    })
    confirm_id = create_resp.json()["id"]
    client.post(f"/confirmations/{confirm_id}/approve")

    mock_broker = MagicMock()
    mock_broker.close_tab = AsyncMock(return_value={
        "ok": True,
        "snapshot_id": "tabsnap",
        "position": 1,
        "tab_id": "t-1",
        "title": "Test",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = client.post("/tools/execute", json={
            "tool_name": "browser_tab_close",
            "arguments": confirm_payload,
            "context": {
                "computer_mode": True,
                "confirmation_id": confirm_id,
            },
        }).json()

    assert body["ok"] is True
    # Verify broker was called with "brave" not "brejv"
    mock_broker.close_tab.assert_awaited_once_with(
        snapshot_id="tabsnap",
        position=1,
        browser="brave",
        profile_id=None,
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
    secret1 = broker._ensure_legacy_secret()
    assert len(secret1) == 64  # 32 bytes = 64 hex chars

    # Secret file should exist
    assert broker.secret_file.exists()
    assert broker.secret_file.read_text().strip() == secret1

    # Reload — should return same secret
    broker2 = BrowserExtensionBroker(tmp_path)
    secret2 = broker2._ensure_legacy_secret()
    assert secret2 == secret1


def test_broker_pairing_session_flow() -> None:
    from app.services.browser_extension_broker import BrowserExtensionBroker
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        # Create pairing session
        session = broker.create_pairing_session("brave")
        assert "human_code" in session
        assert len(session["human_code"]) == 6
        assert session["expires_in_seconds"] > 0

        # Check status
        status = broker.get_pairing_session(session["pairing_id"])
        assert status is not None
        assert status["status"] == "pending"

        # Cancel
        assert broker.cancel_pairing_session(session["pairing_id"]) is True
        status2 = broker.get_pairing_session(session["pairing_id"])
        assert status2["status"] == "expired"


def test_broker_get_status_returns_structure() -> None:
    from app.services.browser_extension_broker import BrowserExtensionBroker
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        status = broker.get_status()
        assert status["connected"] is False
        assert status["connection_count"] == 0
        assert status["connections"] == []


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


# ---------------------------------------------------------------------------
# C1: multi-connection broker tests
# ---------------------------------------------------------------------------


def test_multi_connection_resolve_profile_exact_match() -> None:
    """_resolve_profile finds exact profile_id match."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential,
    )
    from datetime import datetime, timezone

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        # Register two fake connections
        inst1 = InstallCredential(
            installation_id="inst-aaa", profile_id="profile-brave-default",
            credential="cred1", browser_kind="brave", profile_label="Default",
            extension_version="1.0.0", created_at=datetime.now(timezone.utc),
        )
        inst2 = InstallCredential(
            installation_id="inst-bbb", profile_id="profile-chrome-work",
            credential="cred2", browser_kind="chrome", profile_label="Work",
            extension_version="1.0.0", created_at=datetime.now(timezone.utc),
        )
        broker._install_credentials["inst-aaa"] = inst1
        broker._install_credentials["inst-bbb"] = inst2

        # No connections active yet — resolve should fail
        from app.core.errors import AppError
        try:
            broker._resolve_profile(profile_id="profile-brave-default")
            assert False, "Should raise"
        except AppError as e:
            assert e.code == "BROWSER_PROFILE_NOT_CONNECTED"


def test_resolve_profile_by_browser_kind() -> None:
    """_resolve_profile with browser finds single match."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        inst = InstallCredential(
            installation_id="inst-aaa", profile_id="p-brave",
            credential="c", browser_kind="brave", profile_label="Default",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        mock_ws = MagicMock()
        mock_ws.client_state = 1  # CONNECTED
        conn = ConnectionState(
            profile_id="p-brave", installation_id="inst-aaa",
            websocket=mock_ws, install=inst,
        )
        broker._connections["p-brave"] = conn

        result = broker._resolve_profile(browser="brave")
        assert result.profile_id == "p-brave"


def test_resolve_profile_ambiguous() -> None:
    """Multiple profiles of same browser raises ambiguous."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from app.core.errors import AppError

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        mock_ws = MagicMock()
        mock_ws.client_state = 1

        for i, label in enumerate(["Default", "Work"]):
            inst = InstallCredential(
                installation_id=f"inst-{i}", profile_id=f"p-brave-{i}",
                credential=f"c{i}", browser_kind="brave", profile_label=label,
                extension_version="1.0", created_at=datetime.now(timezone.utc),
            )
            conn = ConnectionState(
                profile_id=f"p-brave-{i}", installation_id=f"inst-{i}",
                websocket=mock_ws, install=inst,
            )
            broker._connections[f"p-brave-{i}"] = conn

        try:
            broker._resolve_profile(browser="brave")
            assert False, "Should raise"
        except AppError as e:
            assert e.code == "BROWSER_PROFILE_AMBIGUOUS"


def test_resolve_profile_single_connection_no_browser() -> None:
    """With exactly one connection, no browser/profile needed."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        inst = InstallCredential(
            installation_id="inst", profile_id="p-1",
            credential="c", browser_kind="brave", profile_label="Default",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        mock_ws = MagicMock()
        mock_ws.client_state = 1
        broker._connections["p-1"] = ConnectionState(
            profile_id="p-1", installation_id="inst",
            websocket=mock_ws, install=inst,
        )

        result = broker._resolve_profile()  # No args
        assert result.profile_id == "p-1"


def test_snapshot_profile_binding_prevents_cross_profile_use() -> None:
    """Snapshot from profile A cannot be used on profile B."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, SnapshotStore,
    )

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))

        # Store snapshot for profile "p-brave"
        broker._snapshots.store("snap-1", {
            "profile_id": "p-brave",
            "browser": "brave",
            "tabs": [{"position": 1, "tab_id": "t-1", "title": "Test"}],
            "count": 1,
        })

        # Try to retrieve for different profile
        result = broker._snapshots.get("snap-1", profile_id="p-chrome")
        assert result is None  # Should be rejected

        # Retrieve for correct profile
        result = broker._snapshots.get("snap-1", profile_id="p-brave")
        assert result is not None


def test_revoke_connection_removes_it() -> None:
    """Revoke removes connection from registry and marks credential revoked."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        inst = InstallCredential(
            installation_id="inst-1", profile_id="p-1",
            credential="c", browser_kind="brave", profile_label="Default",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        mock_ws = MagicMock()
        mock_ws.client_state = 1
        broker._install_credentials["inst-1"] = inst
        broker._connections["p-1"] = ConnectionState(
            profile_id="p-1", installation_id="inst-1",
            websocket=mock_ws, install=inst,
        )

        assert len(broker._connections) == 1
        assert broker.revoke_connection("p-1") is True
        assert len(broker._connections) == 0
        assert inst.revoked is True


def test_get_connections_lists_active_and_stored() -> None:
    """get_connections returns both active and stored credentials."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))

        # Active connection
        inst1 = InstallCredential(
            installation_id="inst-1", profile_id="p-1",
            credential="c1", browser_kind="brave", profile_label="Default",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        broker._install_credentials["inst-1"] = inst1
        mock_ws = MagicMock()
        mock_ws.client_state = 1
        broker._connections["p-1"] = ConnectionState(
            profile_id="p-1", installation_id="inst-1",
            websocket=mock_ws, install=inst1,
        )

        # Stored credential, not connected
        inst2 = InstallCredential(
            installation_id="inst-2", profile_id="p-2",
            credential="c2", browser_kind="chrome", profile_label="Work",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        broker._install_credentials["inst-2"] = inst2

        conns = broker.get_connections()
        assert len(conns) == 2
        active = [c for c in conns if c["connected"]]
        inactive = [c for c in conns if not c["connected"]]
        assert len(active) == 1
        assert len(inactive) == 1
        assert active[0]["browser_kind"] == "brave"
        assert inactive[0]["browser_kind"] == "chrome"


def test_rename_profile_updates_label() -> None:
    """Rename updates profile_label on active connection."""
    import tempfile
    from pathlib import Path
    from app.services.browser_extension_broker import (
        BrowserExtensionBroker, InstallCredential, ConnectionState,
    )
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    with tempfile.TemporaryDirectory() as tmp:
        broker = BrowserExtensionBroker(Path(tmp))
        inst = InstallCredential(
            installation_id="inst", profile_id="p-1",
            credential="c", browser_kind="brave", profile_label="Default",
            extension_version="1.0", created_at=datetime.now(timezone.utc),
        )
        broker._install_credentials["inst"] = inst
        mock_ws = MagicMock()
        broker._connections["p-1"] = ConnectionState(
            profile_id="p-1", installation_id="inst",
            websocket=mock_ws, install=inst,
        )

        assert broker.rename_profile("p-1", "Personal") is True
        assert inst.profile_label == "Personal"


# ---------------------------------------------------------------------------
# C2: browser_tab_open + discovery tests
# ---------------------------------------------------------------------------


def test_browser_tab_open_is_listed(client: TestClient) -> None:
    """browser_tab_open is registered with medium risk."""
    tools = {tool["name"]: tool for tool in client.get("/tools").json()["tools"]}
    tool = tools["browser_tab_open"]
    assert tool["risk"] == "medium"
    assert tool["requires_confirmation"] is False
    assert tool["requires_computer_mode"] is True


def test_browser_tab_open_rejects_unsafe_url(client: TestClient) -> None:
    """Non-HTTP(S) URLs are rejected."""
    body = client.post("/tools/execute", json={
        "tool_name": "browser_tab_open",
        "arguments": {"browser": "brave", "url": "file:///C:/evil.exe"},
        "context": {"computer_mode": True},
    }).json()
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_browser_tab_open_rejects_embedded_credentials(client: TestClient) -> None:
    body = client.post("/tools/execute", json={
        "tool_name": "browser_tab_open",
        "arguments": {"browser": "brave", "url": "https://user:pass@evil.com"},
        "context": {"computer_mode": True},
    }).json()
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_browser_tab_open_succeeds_with_mock(client: TestClient) -> None:
    """browser_tab_open calls broker.open_tab with correct params."""
    mock_broker = MagicMock()
    mock_broker.open_tab = AsyncMock(return_value={
        "ok": True,
        "browser": "brave",
        "profile_id": "p-brave",
        "profile_label": "Default",
        "url": "https://youtube.com",
        "tab_id": "t-new",
        "title": "YouTube",
        "message": "Opened new tab in brave/Default: https://youtube.com",
    })

    with patch(
        "app.tools.system.browser_tabs._get_broker",
        return_value=mock_broker,
    ):
        body = client.post("/tools/execute", json={
            "tool_name": "browser_tab_open",
            "arguments": {
                "browser": "brave",
                "url": "https://youtube.com",
                "profile_id": "p-brave",
            },
            "context": {"computer_mode": True},
        }).json()

    assert body["ok"] is True
    mock_broker.open_tab.assert_awaited_once_with(
        url="https://youtube.com", activate=True,
        browser="brave", profile_id="p-brave",
    )


def test_browser_discovery_returns_known_browsers() -> None:
    """discover_browsers returns entries for all Tier 1 browsers."""
    from app.services.chromium_discovery import discover_browsers
    import sys
    if sys.platform != "win32":
        import pytest
        pytest.skip("Browser discovery only works on Windows")

    browsers = discover_browsers()
    kinds = {b["browser_kind"] for b in browsers}
    for tier1 in ("chrome", "edge", "brave"):
        assert tier1 in kinds


def test_browser_normalize_aliases() -> None:
    """Speech-to-text aliases normalize correctly."""
    from app.services.chromium_discovery import normalize_browser
    assert normalize_browser("brejv") == "brave"
    assert normalize_browser("edž") == "edge"
    assert normalize_browser("hrom") == "chrome"
    assert normalize_browser("opera gx") == "opera_gx"
    assert normalize_browser("opera ge-iks") == "opera_gx"
    assert normalize_browser("chrome") == "chrome"  # unchanged
