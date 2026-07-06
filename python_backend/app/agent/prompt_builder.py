"""Prompt construction for the agent runtime (FAZA 15).

Converts ToolDefinition entries into OpenAI function-calling "tools" schema
and conversation history into an OpenAI-style messages array. Pure functions,
no I/O — kept separate from runtime.py so the prompt shape can be tested and
changed independently of the orchestration loop.
"""
from __future__ import annotations

from typing import Any

from app.schemas.tool import ToolDefinition

SYSTEM_PROMPT = (
    "You are Ricky, a local desktop assistant (LocalDesktopAssistant) running "
    "entirely on the user's own Windows machine. You can call the provided "
    "tools to look things up, remember notes/records, create artifacts, and "
    "(if Computer Mode is enabled) inspect or act on the user's screen. "
    "Tools that require confirmation or Computer Mode will be rejected by the "
    "backend if the required approval/mode is missing — do not claim an "
    "action succeeded unless the tool result says so. Keep replies concise."
)


def tools_to_openai_schema(definitions: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.input_schema,
            },
        }
        for definition in definitions
        if definition.enabled
    ]


def build_messages(
    *,
    history: list[dict[str, Any]],
    new_user_message: str | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for entry in history:
        messages.append(_history_entry_to_message(entry))
    if new_user_message is not None:
        messages.append({"role": "user", "content": new_user_message})
    return messages


def _history_entry_to_message(entry: dict[str, Any]) -> dict[str, Any]:
    role = entry["role"]
    if role == "assistant" and entry.get("tool_calls"):
        return {
            "role": "assistant",
            "content": entry.get("content"),
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {"name": call["tool_name"], "arguments": call.get("arguments", {})},
                }
                for call in entry["tool_calls"]
            ],
        }
    if role == "tool":
        return {
            "role": "tool",
            "tool_call_id": entry.get("tool_call_id"),
            "content": entry.get("content") or "",
        }
    return {"role": role, "content": entry.get("content") or ""}
