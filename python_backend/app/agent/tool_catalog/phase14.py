"""Tool definitions for computer-use v2 (UI element targeting) tools (FAZA 14).

Registers computer_find_elements, computer_click_element,
computer_set_text_element, and computer_get_element_text — all via UIA
in app/tools/system/element_target.py.
"""
from __future__ import annotations

from typing import Any

from app.agent.permission_engine import DEFAULT_BLOCKED_APPS
from app.schemas.tool import ToolDefinition

"""FAZA 14 tool catalog: UIA element-targeting tools."""
def register_phase14_tools(registry: ToolRegistry) -> None:
    """Register FAZA 14 computer-use tools (UI element targeting).

    Element-based UI automation via Windows UIA. Reduces reliance on raw
    coordinate clicks from FAZA 13.
    """
    from app.tools.system.element_target import make_handlers as make_element_handlers

    handlers = make_element_handlers()

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
        timeout_ms: int = 15000,
        reads_external_content: bool = False,
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
            reads_external_content=reads_external_content,
        )

    registry.register(
        _def(
            "computer_find_elements",
            "Find UI elements in a Windows application by app name, window title, control type, element name, automation ID, or class name. Returns basic properties of matched elements (name, control_type, automation_id, class_name, bounding_rect, enabled state). Requires computer mode.",
            {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Process name (e.g. notepad.exe, chrome.exe)"},
                    "title_contains": {"type": "string", "description": "Substring match on window title"},
                    "control_type": {"type": "string", "description": "UIA control type name (e.g. Edit, Button, Window, MenuItem)"},
                    "name": {"type": "string", "description": "Element name (substring match)"},
                    "automation_id": {"type": "string", "description": "Exact AutomationId"},
                    "class_name": {"type": "string", "description": "Exact ClassName"},
                    "max_results": {"type": "number", "minimum": 1, "maximum": 50},
                },
                "required": [],
                "additionalProperties": False,
            },
            reads_external_content=True,
        ),
        handlers["computer_find_elements"],
    )

    registry.register(
        _def(
            "computer_click_element",
            "Click a UI element identified by its properties (app name, window title, control type, etc.). Prefer this over coordinate clicks (computer_click) when a specific UI element can be identified. Requires computer mode.",
            {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Process name (e.g. notepad.exe)"},
                    "title_contains": {"type": "string", "description": "Substring match on window title"},
                    "control_type": {"type": "string", "description": "UIA control type name"},
                    "name": {"type": "string", "description": "Element name"},
                    "automation_id": {"type": "string", "description": "Exact AutomationId"},
                    "class_name": {"type": "string", "description": "Exact ClassName"},
                },
                "required": [],
                "additionalProperties": False,
            },
            risk="high",
            requires_confirmation=True,
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_click_element"],
    )

    registry.register(
        _def(
            "computer_set_text_element",
            "Set text value on a UI element (Edit fields, etc.) identified by its properties. Uses UIA ValuePattern when available, falls back to keyboard simulation. Requires computer mode and an approved confirmation.",
            {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to set"},
                    "app": {"type": "string"},
                    "title_contains": {"type": "string"},
                    "control_type": {"type": "string"},
                    "name": {"type": "string"},
                    "automation_id": {"type": "string"},
                    "class_name": {"type": "string"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            risk="high",
            requires_confirmation=True,
            requires_active_window_match=True,
            blocked_apps=DEFAULT_BLOCKED_APPS,
        ),
        handlers["computer_set_text_element"],
    )

    registry.register(
        _def(
            "computer_get_element_text",
            "Read text value from a UI element (Edit fields, labels, etc.) identified by its properties. Requires computer mode.",
            {
                "type": "object",
                "properties": {
                    "app": {"type": "string"},
                    "title_contains": {"type": "string"},
                    "control_type": {"type": "string"},
                    "name": {"type": "string"},
                    "automation_id": {"type": "string"},
                    "class_name": {"type": "string"},
                },
                "required": [],
                "additionalProperties": False,
            },
            reads_external_content=True,
        ),
        handlers["computer_get_element_text"],
    )
