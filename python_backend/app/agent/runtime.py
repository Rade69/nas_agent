"""LocalDesktopAssistant — single-agent runtime (FAZA 15).

Scope (see docs/MIGRATION_PLAN.md FAZA 15 and the original spec in
docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md "Agent runtime u
Pythonu"): one agent, no multi-agent orchestration. Receives a user message,
optionally calls registered tools, and returns a reply.

Security-critical invariant: every tool call the model requests is executed
through the exact same ToolExecutor.execute() used by POST /tools/execute —
the same permission/risk engine (FAZA 10) and cancellation state machine gate
every call. The runtime has no separate/parallel path to run a tool, so it
cannot bypass the permission layer (acceptance criterion in MIGRATION_PLAN.md).

Context: agent_reports/2026-07-06_faza15-agent-runtime.md
"""
from __future__ import annotations

import json
from typing import Any

from app.agent.conversation_state import ConversationStateService
from app.agent.model_client import ModelClient
from app.agent.prompt_builder import build_messages, tools_to_openai_schema
from app.agent.tool_executor import ToolExecutor
from app.schemas.tool import ToolExecutionContext, ToolExecutionRequest

MAX_TOOL_ITERATIONS = 4


class LocalDesktopAssistant:
    def __init__(
        self,
        *,
        model_client: ModelClient,
        tool_executor: ToolExecutor,
        conversations: ConversationStateService,
    ) -> None:
        self._model_client = model_client
        self._tool_executor = tool_executor
        self._conversations = conversations

    def handle_message(
        self,
        *,
        conversation_id: str | None,
        message: str,
        computer_mode: bool = False,
    ) -> dict[str, Any]:
        resolved_conversation_id = self._conversations.get_or_create(conversation_id)
        self._conversations.append_message(
            conversation_id=resolved_conversation_id,
            role="user",
            content=message,
        )

        tools_schema = tools_to_openai_schema(self._tool_executor.registry.list())
        executed_tool_calls: list[dict[str, Any]] = []
        artifact_ids: list[str] = []
        event_ids: list[str] = []

        for _ in range(MAX_TOOL_ITERATIONS):
            history = self._conversations.raw_history_for_prompt(resolved_conversation_id)
            messages = build_messages(history=history)
            response = self._model_client.complete(messages=messages, tools=tools_schema)

            if not response.tool_calls:
                self._conversations.append_message(
                    conversation_id=resolved_conversation_id,
                    role="assistant",
                    content=response.content or "",
                )
                return {
                    "conversation_id": resolved_conversation_id,
                    "reply": response.content or "",
                    "tool_calls": executed_tool_calls,
                    "artifact_ids": artifact_ids,
                    "event_ids": event_ids,
                }

            self._conversations.append_message(
                conversation_id=resolved_conversation_id,
                role="assistant",
                content=response.content,
                tool_calls=[
                    {"id": call.id, "tool_name": call.tool_name, "arguments": call.arguments}
                    for call in response.tool_calls
                ],
            )

            for call in response.tool_calls:
                tool_response = self._tool_executor.execute(
                    ToolExecutionRequest(
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        context=ToolExecutionContext(
                            computer_mode=computer_mode,
                            conversation_id=resolved_conversation_id,
                        ),
                    )
                )
                executed_tool_calls.append(
                    {
                        "tool_name": call.tool_name,
                        "ok": tool_response.ok,
                        "execution_id": tool_response.execution_id,
                        "tool_state": tool_response.tool_state,
                        "error": tool_response.error.model_dump() if tool_response.error else None,
                    }
                )
                artifact_ids.extend(tool_response.artifact_ids)
                event_ids.extend(tool_response.event_ids)

                self._conversations.append_message(
                    conversation_id=resolved_conversation_id,
                    role="tool",
                    content=json.dumps(tool_response.model_dump(mode="json"), ensure_ascii=False),
                    tool_call_id=call.id,
                    tool_name=call.tool_name,
                )

        self._conversations.append_message(
            conversation_id=resolved_conversation_id,
            role="assistant",
            content="I couldn't finish that after several tool calls — please try again or rephrase.",
        )
        return {
            "conversation_id": resolved_conversation_id,
            "reply": "I couldn't finish that after several tool calls — please try again or rephrase.",
            "tool_calls": executed_tool_calls,
            "artifact_ids": artifact_ids,
            "event_ids": event_ids,
        }
