from __future__ import annotations

from typing import Any

from app.schemas.tool import ToolDefinition

"""FAZA 11 tool catalog: memory/artifact/system/web/image tool definitions and registration."""
def register_phase11_tools(registry: ToolRegistry, services: dict[str, Any]) -> None:
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
    screenshot_handlers = make_screenshot_handlers(services["screenshots_dir"], services.get("screenshot_service"))
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
            allowed_apps=allowed_apps or [],
            blocked_apps=blocked_apps or [],
            logs_action_receipt=False,
            allowed_in_background=not requires_computer_mode,
            timeout_ms=timeout_ms,
            implemented_by="python",
            enabled=enabled,
            reads_external_content=reads_external_content,
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
            reads_external_content=True,
        ),
        screenshot_handlers["screen_snapshot"],
    )
    registry.register(
        _def(
            "ui_inspect",
            "Inspect the frontmost Windows app name and window title. Requires computer mode.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            requires_computer_mode=True,
            reads_external_content=True,
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
            reads_external_content=True,
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
