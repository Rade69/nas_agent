from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agent.permission_engine import DEFAULT_BLOCKED_APPS
from app.schemas.tool import ToolDefinition

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class RegisteredTool:
    definition: ToolDefinition
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._tools[definition.name] = RegisteredTool(definition=definition, handler=handler)

    def list(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)


def echo_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    text = arguments.get("text")
    if not isinstance(text, str):
        raise ValueError("echo requires a string argument named 'text'.")
    return {"text": text}


def _register_phase11_tools(registry: ToolRegistry, services: dict[str, Any]) -> None:
    """Register FAZA 11 memory/artifact/system tools."""
    from app.tools.artifacts import make_handlers as make_artifact_handlers
    from app.tools.images.generate import make_handlers as make_image_handlers
    from app.tools.memory.notes import make_handlers as make_notes_handlers
    from app.tools.memory.records import make_handlers as make_records_handlers
    from app.tools.system.screenshot import make_handlers as make_screenshot_handlers
    from app.tools.system.ui_inspect import make_handlers as make_ui_inspect_handlers
    from app.tools.web.search import make_handlers as make_web_handlers

    notes_handlers = make_notes_handlers(services["notes"])
    records_handlers = make_records_handlers(services["records"])
    artifact_handlers = make_artifact_handlers(services["artifact"])
    screenshot_handlers = make_screenshot_handlers(services["screenshots_dir"])
    ui_inspect_handlers = make_ui_inspect_handlers()
    web_handlers = make_web_handlers(services["exa_client"])
    image_handlers = make_image_handlers(services["openai_image_client"], services["images_dir"])

    def _def(
        name: str,
        description: str,
        schema: dict[str, Any],
        *,
        risk: str = "low",
        requires_confirmation: bool = False,
        requires_computer_mode: bool = False,
        enabled: bool = True,
        timeout_ms: int = 10000,
        requires_active_window_match: bool = False,
        allowed_apps: list[str] | None = None,
        blocked_apps: list[str] | None = None,
    ) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description=description,
            input_schema=schema,
            risk=risk,
            requires_confirmation=requires_confirmation,
            requires_computer_mode=requires_computer_mode,
            requires_active_window_match=requires_active_window_match,
            allowed_apps=allowed_apps or [],
            blocked_apps=blocked_apps or [],
            logs_action_receipt=False,
            allowed_in_background=not requires_computer_mode,
            timeout_ms=timeout_ms,
            implemented_by="python",
            enabled=enabled,
        )

    # --- Memory tools (low risk, no confirmation) ---
    registry.register(
        _def(
            "note_add",
            "Add a note to Ricky's fun local notes list.",
            {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
        notes_handlers["note_add"],
    )
    registry.register(
        _def(
            "note_search",
            "Search Ricky's fun local notes by text or tag.",
            {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
        ),
        notes_handlers["note_search"],
    )
    registry.register(
        _def(
            "note_list",
            "List Ricky's recent fun local notes.",
            {
                "type": "object",
                "properties": {"limit": {"type": "number"}},
                "required": [],
                "additionalProperties": False,
            },
        ),
        notes_handlers["note_list"],
    )

    # --- Records tools ---
    registry.register(
        _def(
            "records_create",
            "Create a local database record in a named collection.",
            {
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "title": {"type": "string"},
                    "fields": {"type": "object", "additionalProperties": True},
                },
                "required": ["collection", "title"],
                "additionalProperties": False,
            },
        ),
        records_handlers["records_create"],
    )
    registry.register(
        _def(
            "records_search",
            "Search local database records by collection and query.",
            {
                "type": "object",
                "properties": {
                    "collection": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["collection"],
                "additionalProperties": False,
            },
        ),
        records_handlers["records_search"],
    )
    registry.register(
        _def(
            "records_update",
            "Update a local database record. Ask for confirmation first if the change is sensitive.",
            {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "fields": {"type": "object", "additionalProperties": True},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
        records_handlers["records_update"],
    )
    registry.register(
        _def(
            "records_delete",
            "Delete a local database record. Always ask for explicit confirmation first, then call with confirmed=true.",
            {
                "type": "object",
                "properties": {"id": {"type": "string"}, "confirmed": {"type": "boolean"}},
                "required": ["id", "confirmed"],
                "additionalProperties": False,
            },
            risk="critical",
            requires_confirmation=True,
        ),
        records_handlers["records_delete"],
    )

    # --- Artifact tools ---
    registry.register(
        _def(
            "artifact_create",
            "Create a structured artifact (text, markdown, code, image ref) in the backend.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["text", "markdown", "code", "table", "notes", "mermaid", "image", "progress"],
                    },
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
        ),
        artifact_handlers["artifact_create"],
    )
    registry.register(
        _def(
            "artifact_get",
            "Fetch a stored artifact by id.",
            {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
        artifact_handlers["artifact_get"],
    )
    registry.register(
        _def(
            "artifact_list",
            "List recent artifacts, optionally filtered by type.",
            {
                "type": "object",
                "properties": {"limit": {"type": "number"}, "type": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
        ),
        artifact_handlers["artifact_list"],
    )
    registry.register(
        _def(
            "artifact_show",
            "Store and display a full artifact payload (title, kind, content) in the artifact panel.",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "kind": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title"],
                "additionalProperties": True,
            },
        ),
        artifact_handlers["artifact_show"],
    )

    # --- System tools (require computer_mode) ---
    registry.register(
        _def(
            "screen_snapshot",
            "Capture the current screen and return the local screenshot path. Requires computer mode.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            requires_computer_mode=True,
        ),
        screenshot_handlers["screen_snapshot"],
    )
    registry.register(
        _def(
            "ui_inspect",
            "Inspect the frontmost Windows app name and window title. Requires computer mode.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            requires_computer_mode=True,
        ),
        ui_inspect_handlers["ui_inspect"],
    )

    # --- Web / AI integrations (FAZA 16) ---
    registry.register(
        _def(
            "web_search",
            "Search the web with Exa. Use for current facts, links, research, and source gathering. Results are shown as a clean Markdown research brief in the artifact panel.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "numResults": {"type": "number", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            timeout_ms=30000,
        ),
        web_handlers["web_search"],
    )
    registry.register(
        _def(
            "image_generate",
            "Generate a standalone image with GPT Image and show it in the artifact panel. Do not use for YouTube thumbnails; use thumbnail_generate or thumbnail_edit instead.",
            {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "size": {"type": "string"},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
            timeout_ms=90000,
        ),
        image_handlers["image_generate"],
    )


def _register_phase13_tools(registry: ToolRegistry) -> None:
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


def _register_phase14_tools(registry: ToolRegistry) -> None:
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
        ),
        handlers["computer_get_element_text"],
    )


def create_default_registry(services: dict[str, Any] | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Return the provided text unchanged.",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo back.",
                    }
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            risk="low",
            requires_confirmation=False,
            requires_computer_mode=False,
            requires_active_window_match=False,
            allowed_apps=[],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=True,
            timeout_ms=5000,
            implemented_by="python",
            enabled=True,
        ),
        echo_tool,
    )
    if services is not None:
        _register_phase11_tools(registry, services)
        _register_phase13_tools(registry)
        _register_phase14_tools(registry)
    return registry