"""Tool registry factory (FAZA 11 + later phases).

Builds a ToolRegistry populated from the phase-specific catalog modules.
Used by app/main.py's create_app() to produce app.state.tool_registry.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agent.tool_catalog import (
    register_phase11_tools,
    register_phase13_tools,
    register_phase14_tools,
)
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
        register_phase11_tools(registry, services)
        register_phase13_tools(registry)
        register_phase14_tools(registry)
    return registry