from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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
    """Register FAZA 11 memory/artifact/system tools.

    Tool definitions follow TOOL_CONTRACTS.md (risk, requires_confirmation,
    requires_computer_mode, etc.). The permission/risk enforcement layer
    (FAZA 10) will read these flags; here we only register the tools and
    expose them through `/tools` and `/tools/execute`.
    """
    from app.tools.artifacts import make_handlers as make_artifact_handlers
    from app.tools.memory.notes import make_handlers as make_notes_handlers
    from app.tools.memory.records import make_handlers as make_records_handlers
    from app.tools.system.screenshot import make_handlers as make_screenshot_handlers
    from app.tools.system.ui_inspect import make_handlers as make_ui_inspect_handlers

    notes_handlers = make_notes_handlers(services["notes"])
    records_handlers = make_records_handlers(services["records"])
    artifact_handlers = make_artifact_handlers(services["artifact"])
    screenshot_handlers = make_screenshot_handlers(services["screenshots_dir"])
    ui_inspect_handlers = make_ui_inspect_handlers()

    def _def(
        name: str,
        description: str,
        schema: dict[str, Any],
        *,
        risk: str = "low",
        requires_confirmation: bool = False,
        requires_computer_mode: bool = False,
        enabled: bool = True,
    ) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description=description,
            input_schema=schema,
            risk=risk,
            requires_confirmation=requires_confirmation,
            requires_computer_mode=requires_computer_mode,
            requires_active_window_match=False,
            allowed_apps=[],
            blocked_apps=[],
            logs_action_receipt=False,
            allowed_in_background=not requires_computer_mode,
            timeout_ms=10000,
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
    return registry
