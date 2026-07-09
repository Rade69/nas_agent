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
            "computer_open_app",
            "Open a Windows app by name (must be in PATH or have an App Execution Alias, e.g. notepad, calc, mspaint, chrome). Requires computer mode.",
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

