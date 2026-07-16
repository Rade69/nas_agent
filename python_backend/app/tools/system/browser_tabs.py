"""browser_tabs + browser_tab_close tools — list, activate, and close browser tabs.

PR 1-2: list + activate via browser_tabs(action=...).
PR 3: close via separate browser_tab_close tool (high-risk, confirmation-gated).

Uses the BrowserExtensionBroker for authenticated localhost WebSocket
communication with the MV3 extension.
"""
from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.services.browser_extension_broker import get_broker as _get_broker_imported

_BROWSER_ALIASES: dict[str, str] = {
    "brejv": "brave",
}


def _validate_action(action: str) -> str:
    """Ensure action is one of the allowed values (list/activate only)."""
    valid = {"list", "activate"}
    if action not in valid:
        raise ValueError(f"action must be one of: {', '.join(sorted(valid))}.")
    return action


def _normalize_browser(raw: str) -> str:
    """Normalize browser name (brejv → brave)."""
    normalized = raw.strip().lower()
    return _BROWSER_ALIASES.get(normalized, normalized)


def _validate_browser(browser: str) -> str:
    """Validate browser is an allowed value."""
    allowed = {"brave", "chrome"}
    if browser not in allowed:
        raise ValueError("browser must be one of: brave, brejv, chrome.")
    return browser


def _validate_scope(scope: str | None) -> str:
    """Validate scope parameter."""
    if scope is None:
        return "current_window"
    allowed = {"current_window", "all_windows"}
    if scope not in allowed:
        raise ValueError("scope must be one of: current_window, all_windows.")
    return scope


def _get_broker():
    """Get the browser extension broker, with a helpful error if not connected."""
    try:
        return _get_broker_imported()
    except RuntimeError:
        raise AppError(
            "BROWSER_EXTENSION_NOT_CONNECTED",
            "Browser bridge is not available. The backend may need to be restarted.",
        )


# ---------------------------------------------------------------------------
# browser_tabs — list + activate (medium risk, no confirmation)
# ---------------------------------------------------------------------------


def _handle_browser_tabs(arguments: dict[str, Any]) -> dict[str, Any]:
    """Synchronous entry point for browser_tabs (list/activate)."""

    action = _validate_action(str(arguments.get("action", "list")).strip().lower())
    raw_browser = str(arguments.get("browser", "brave")).strip().lower() or "brave"
    browser = _normalize_browser(raw_browser)
    _validate_browser(browser)

    if action == "list":
        import asyncio
        broker = _get_broker()
        scope = _validate_scope(arguments.get("scope"))
        profile_id = str(arguments.get("profile_id", "")).strip() or None
        result = asyncio.run(broker.list_tabs(
            scope=scope, browser=browser, profile_id=profile_id,
        ))

        tabs_list = result.get("tabs", [])
        count = result.get("count", len(tabs_list))

        if count == 0:
            return {
                **result,
                "message": f"No tabs open in the active {browser} window.",
            }

        tab_names = ", ".join(
            f"{t['position']}. {t['title'][:40]}" for t in tabs_list[:10]
        )
        suffix = f" (+{count - 10} more)" if count > 10 else ""

        return {
            **result,
            "browser": browser,
            "message": f"{count} tab(s) in {browser}: {tab_names}{suffix}",
        }

    if action == "activate":
        snapshot_id = str(arguments.get("snapshot_id", "")).strip()
        if not snapshot_id:
            raise AppError("INVALID_ARGUMENTS", "snapshot_id is required for activate.")
        position = int(arguments.get("position", 0))
        if position < 1:
            raise AppError("INVALID_ARGUMENTS", "position must be 1 or greater.")
        import asyncio
        broker = _get_broker()
        profile_id = str(arguments.get("profile_id", "")).strip() or None
        result = asyncio.run(broker.activate_tab(
            snapshot_id=snapshot_id,
            position=position,
            browser=browser,
            profile_id=profile_id,
        ))
        title = result.get("title", "")
        result["message"] = (
            f"Aktivirao sam {position}. tab: {title}."
            if title else
            f"Aktivirao sam {position}. tab."
        )
        return result

    raise ValueError(f"Unknown action: {action}")


# ---------------------------------------------------------------------------
# browser_tab_close — close only (high risk, confirmation-gated)
# ---------------------------------------------------------------------------


def _handle_browser_tab_close(arguments: dict[str, Any]) -> dict[str, Any]:
    """Close a browser tab by snapshot_id + position.

    This tool is gated by the permission engine (requires_confirmation=True,
    risk=high). The confirmation_id is validated before this handler runs.
    On arrival, the handler:
      1. Checks the snapshot is still valid (TAB_SNAPSHOT_STALE if expired)
      2. Resolves the tab_id from the snapshot
      3. Closes the tab via the broker
      4. Returns the result with the tab title

    If the snapshot is stale, the handler returns TAB_SNAPSHOT_STALE — the
    approval was already consumed by the permission engine, so the agent
    must re-list and try again with a fresh confirmation.
    """
    import asyncio

    raw_browser = str(arguments.get("browser", "brave")).strip().lower() or "brave"
    browser = _normalize_browser(raw_browser)
    _validate_browser(browser)

    snapshot_id = str(arguments.get("snapshot_id", "")).strip()
    if not snapshot_id:
        raise AppError("INVALID_ARGUMENTS", "snapshot_id is required.")
    position = int(arguments.get("position", 0))
    if position < 1:
        raise AppError("INVALID_ARGUMENTS", "position must be 1 or greater.")

    broker = _get_broker()
    profile_id = str(arguments.get("profile_id", "")).strip() or None
    result = asyncio.run(broker.close_tab(
        snapshot_id=snapshot_id,
        position=position,
        browser=browser,
        profile_id=profile_id,
    ))
    title = result.get("title", "")
    result["message"] = (
        f"Zatvorio sam {position}. tab: {title}."
        if title else
        f"Zatvorio sam {position}. tab."
    )
    return result


def make_handler():
    """Return the browser_tabs (list/activate) handler for ToolRegistry."""
    return _handle_browser_tabs


def make_close_handler():
    """Return the browser_tab_close handler for ToolRegistry."""
    return _handle_browser_tab_close