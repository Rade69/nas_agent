"""Tool definitions for computer-use v1 (coordinate-based) tools (FAZA 13).

Registers computer_open_app, computer_type_text, computer_press_key,
computer_click, and computer_scroll — all implemented via ctypes + Win32 API
in app/tools/system/computer.py, no external dependencies.
"""
from __future__ import annotations

from typing import Any

from app.agent.permission_engine import DEFAULT_BLOCKED_APPS
from app.schemas.tool import ToolDefinition

"""FAZA 13 tool catalog: coordinate-based computer-use tools."""
def register_phase13_tools(registry: ToolRegistry) -> None:
    """Register FAZA 13 computer-use tools (coordinate-based).

    These are 1:1 Python replacements for the legacy PowerShell computer_*
    tools. All require computer_mode; click and type_text are high risk.
    """
    from app.tools.system.computer import make_handlers as make_computer_handlers
    from app.tools.system.browser import make_handler as make_browser_handler
    from app.tools.system.browser_tabs import make_handler as make_browser_tabs_handler
    from app.tools.system.browser_tabs import make_close_handler as make_browser_tab_close_handler

    handlers = make_computer_handlers()

    def _def(
        name: str,
        description: str,
        schema: dict[str, Any],
        *,
        risk: str = "medium",
        requires_confirmation: bool = False,
        requires_computer_mode: bool = True,
        requires_active_window_match: bool = False,
        blocked_apps: list[str] | None = None,
        timeout_ms: int = 10000,
    ) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description=description,
            input_schema=schema,
            risk=risk,
            requires_confirmation=requires_confirmation,
            requires_computer_mode=requires_computer_mode,
            requires_active_window_match=requires_active_window_match,
            allowed_apps=[],
            blocked_apps=blocked_apps or [],
            logs_action_receipt=False,
            allowed_in_background=False,
            timeout_ms=timeout_ms,
            implemented_by="python",
            enabled=True,
        )

    registry.register(
        _def(
            "browser_open",
            "Open the default browser or an explicitly selected installed browser, optionally at an absolute HTTP(S) URL. Use this instead of computer_open_app for browsers. Serbian/Bosnian/Croatian speech 'Brejv' means Brave and may be passed as browser='brejv'. Never claim success unless this tool returns ok=true.",
            {
                "type": "object",
                "properties": {
                    "browser": {"type": "string", "enum": ["default", "brave", "brejv", "chrome", "edge", "firefox"]},
                    "url": {"type": "string"},
                },
                "additionalProperties": False,
            },
        ),
        make_browser_handler(),
    )

    registry.register(
        _def(
            "computer_open_app",
            "Open a Windows app by name. Only a fixed set of common apps is allowed: notepad, calc/calculator, mspaint/paint, wordpad, explorer, chrome, edge. Requires computer mode.",
            {
                "type": "object",
                "properties": {"appName": {"type": "string"}},
                "required": ["appName"],
                "additionalProperties": False,
            },
        ),
        handlers["computer_open_app"],
    )

    registry.register(
        _def(
            "computer_type_text",
            "Type text into the active app. Requires computer mode and an approved confirmation for anything beyond trivial, low-risk text — see the 'confirmed'/'risk' fields.",
            {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                    "risk": {"type": "string", "enum": ["low", "may_send_or_modify", "private_or_sensitive"]},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            risk="high",
            requires_confirmation=True,
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_type_text"],
    )

    registry.register(
        _def(
            "computer_press_key",
            "Press a keyboard key in the active app. Requires computer mode. Use enter/return after typing when the user asks to send a prompt.",
            {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "enum": ["enter", "return", "tab", "escape", "delete", "space", "up", "down", "left", "right"]},
                    "repeat": {"type": "number", "minimum": 1, "maximum": 20},
                },
                "required": ["key"],
                "additionalProperties": False,
            },
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_press_key"],
    )

    registry.register(
        _def(
            "computer_click",
            "Click screen coordinates. Requires computer mode and an approved confirmation.",
            {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "confirmed": {"type": "boolean"},
                    "risk": {"type": "string", "enum": ["low", "may_send_or_modify", "private_or_sensitive"]},
                },
                "required": ["x", "y"],
                "additionalProperties": False,
            },
            risk="high",
            requires_confirmation=True,
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_click"],
    )

    registry.register(
        _def(
            "computer_scroll",
            "Scroll the active app. Requires computer mode.",
            {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                    "amount": {"type": "number", "minimum": 1, "maximum": 20},
                },
                "required": ["direction"],
                "additionalProperties": False,
            },
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_scroll"],
    )

    registry.register(
        _def(
            "browser_tabs",
            "List or activate browser tabs in an already-open Brave or Chrome window. Always call action=\"list\" FIRST — never guess tab numbers or titles. action=\"activate\" switches to an existing tab by its 1-based position from the most recent snapshot (use the snapshot_id from the list result). 'Open the fifth tab' means ACTIVATE tab #5, not create a new tab. After success say exactly: 'Aktivirao sam N. tab: Title.' On TAB_SNAPSHOT_STALE, re-list and confirm the target. If BROWSER_EXTENSION_NOT_CONNECTED, tell the user and do NOT try keyboard shortcuts. Serbian 'Brejv' = Brave.",
            {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "activate"], "description": "What to do with the tabs."},
                    "browser": {"type": "string", "enum": ["brave", "brejv", "chrome"], "description": "Target browser. 'brejv' normalizes to 'brave'."},
                    "scope": {"type": "string", "enum": ["current_window", "all_windows"], "description": "Tab scope. Default is current_window."},
                    "profile_id": {"type": "string", "description": "Optional stable profile ID from the snapshot. Use when multiple profiles of the same browser are connected."},
                    "snapshot_id": {"type": "string", "description": "REQUIRED for activate. The snapshot_id from the most recent list result."},
                    "position": {"type": "number", "minimum": 1, "description": "REQUIRED for activate. 1-based tab position in the snapshot."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            risk="medium",
            requires_confirmation=False,
            timeout_ms=15000,
        ),
        make_browser_tabs_handler(),
    )

    registry.register(
        _def(
            "browser_tab_close",
            "Close a Brave or Chrome browser tab by its 1-based position from a snapshot. This tool requires explicit user confirmation — the user will see a confirmation dialog before the tab is closed. Always call browser_tabs(action=\"list\") first to get a fresh snapshot_id, profile_id, and current positions. Pass the profile_id from the snapshot to ensure the close targets the correct browser profile. Never guess tab numbers. On TAB_SNAPSHOT_STALE or TAB_PROFILE_MISMATCH, re-list and try again. Serbian 'Brejv' = Brave.",
            {
                "type": "object",
                "properties": {
                    "browser": {"type": "string", "enum": ["brave", "brejv", "chrome"], "description": "Target browser."},
                    "profile_id": {"type": "string", "description": "Stable profile ID from the list snapshot. Ensures close targets the right profile."},
                    "snapshot_id": {"type": "string", "description": "The snapshot_id from the most recent browser_tabs list call."},
                    "position": {"type": "number", "minimum": 1, "description": "1-based position of the tab to close."},
                },
                "required": ["snapshot_id", "position"],
                "additionalProperties": False,
            },
            risk="high",
            requires_confirmation=True,
            timeout_ms=15000,
        ),
        make_browser_tab_close_handler(),
    )
