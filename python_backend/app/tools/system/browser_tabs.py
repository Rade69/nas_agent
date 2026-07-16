"""browser_tabs tool — list, activate, and close browser tabs.

PR 1 scope: action="list" only (read-only). activate and close are
stubbed and will be implemented in PRs 2 and 3.

Uses the BrowserExtensionBroker for authenticated localhost WebSocket
communication with the MV3 extension.
"""
from __future__ import annotations

from typing import Any

from app.core.errors import AppError
from app.services.browser_extension_broker import get_broker as _get_broker

_BROWSER_ALIASES: dict[str, str] = {
    "brejv": "brave",
}


def _validate_action(action: str) -> str:
    """Ensure action is one of the allowed values."""
    valid = {"list", "activate", "close"}
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


def _handle_browser_tabs(arguments: dict[str, Any]) -> dict[str, Any]:
    """Synchronous entry point for the tool registry.

    Internally delegates to the async broker via asyncio.run() because the
    ToolExecutor.execute() call tree is synchronous. This is intentional —
    only browser_tabs needs an async bridge; the rest of the tool system
    remains synchronous.
    """
    import asyncio

    action = _validate_action(str(arguments.get("action", "list")).strip().lower())
    raw_browser = str(arguments.get("browser", "brave")).strip().lower() or "brave"
    browser = _normalize_browser(raw_browser)
    _validate_browser(browser)

    try:
        broker = _get_broker()
    except RuntimeError:
        raise AppError(
            "BROWSER_EXTENSION_NOT_CONNECTED",
            "Browser bridge is not available. The backend may need to be restarted.",
        )

    # ------------------------------------------------------------------
    # PR 1: list only
    # ------------------------------------------------------------------
    if action == "list":
        scope = _validate_scope(arguments.get("scope"))
        result = asyncio.run(broker.list_tabs(scope=scope))

        tabs_list = result.get("tabs", [])
        count = result.get("count", len(tabs_list))

        if count == 0:
            return {
                **result,
                "message": f"No tabs open in the active {browser} window.",
            }

        # Build a human-friendly summary
        tab_names = ", ".join(
            f"{t['position']}. {t['title'][:40]}" for t in tabs_list[:10]
        )
        suffix = f" (+{count - 10} more)" if count > 10 else ""

        return {
            **result,
            "browser": browser,
            "message": f"{count} tab(s) in {browser}: {tab_names}{suffix}",
        }

    # ------------------------------------------------------------------
    # PR 2-3: activate / close (stubbed for now)
    # ------------------------------------------------------------------
    if action == "activate":
        snapshot_id = str(arguments.get("snapshot_id", "")).strip()
        if not snapshot_id:
            raise ValueError("snapshot_id is required for activate.")
        position = int(arguments.get("position", 0))
        if position < 1:
            raise ValueError("position must be 1 or greater.")
        result = asyncio.run(broker.activate_tab(
            snapshot_id=snapshot_id,
            position=position,
            browser=browser,
        ))
        title = result.get("title", "")
        result["message"] = (
            f"Aktivirao sam {position}. tab: {title}."
            if title else
            f"Aktivirao sam {position}. tab."
        )
        return result

    if action == "close":
        snapshot_id = str(arguments.get("snapshot_id", "")).strip()
        if not snapshot_id:
            raise ValueError("snapshot_id is required for close.")
        position = int(arguments.get("position", 0))
        if position < 1:
            raise ValueError("position must be 1 or greater.")
        result = asyncio.run(broker.close_tab(
            snapshot_id=snapshot_id,
            position=position,
            browser=browser,
        ))
        title = result.get("title", "")
        result["message"] = (
            f"Zatvorio sam {position}. tab: {title}."
            if title else
            f"Zatvorio sam {position}. tab."
        )
        return result

    # Unreachable — _validate_action guards above
    raise ValueError(f"Unknown action: {action}")


def make_handler():
    """Return the browser_tabs handler for ToolRegistry registration."""
    return _handle_browser_tabs