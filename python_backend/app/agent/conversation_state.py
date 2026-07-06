from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.schemas.agent import AgentConversationResponse, AgentMessageResponse
from app.storage.repositories.agent_repo import AgentConversationRepository


class ConversationStateService:
    """Application layer over AgentConversationRepository (FAZA 15).

    Owns conversation/message ID generation and row->dict/model mapping. The
    agent runtime (app/agent/runtime.py) is the only caller that appends
    messages; this service has no knowledge of tools, models, or prompts.
    """

    def __init__(self, repository: AgentConversationRepository) -> None:
        self._repository = repository

    def get_or_create(self, conversation_id: str | None) -> str:
        if conversation_id:
            existing = self._repository.get_conversation(conversation_id)
            if existing is not None:
                return conversation_id
        new_id = f"conv_{uuid4().hex[:12]}"
        self._repository.create_conversation(conversation_id=new_id)
        return new_id

    def append_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
    ) -> AgentMessageResponse:
        message_id = f"msg_{uuid4().hex[:12]}"
        row = self._repository.add_message(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
        )
        self._repository.touch_conversation(conversation_id)
        return self._message_to_model(row)

    def history(self, conversation_id: str) -> list[AgentMessageResponse]:
        rows = self._repository.list_messages(conversation_id)
        return [self._message_to_model(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> AgentConversationResponse | None:
        row = self._repository.get_conversation(conversation_id)
        if row is None:
            return None
        return AgentConversationResponse(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=self.history(conversation_id),
        )

    def _message_to_model(self, row: Any) -> AgentMessageResponse:
        return AgentMessageResponse(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            tool_name=row["tool_name"] if "tool_name" in row.keys() else None,
            created_at=row["created_at"],
        )

    def raw_history_for_prompt(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return message rows as plain dicts (role/content/tool_calls/tool_call_id)
        in the shape prompt_builder.py needs to reconstruct an OpenAI-style
        messages array, including tool_calls_json for assistant tool-call turns.
        """
        rows = self._repository.list_messages(conversation_id)
        history: list[dict[str, Any]] = []
        for row in rows:
            tool_calls_json = row["tool_calls_json"] if "tool_calls_json" in row.keys() else None
            tool_calls = json.loads(tool_calls_json) if tool_calls_json else None
            history.append(
                {
                    "role": row["role"],
                    "content": row["content"],
                    "tool_calls": tool_calls,
                    "tool_call_id": row["tool_call_id"] if "tool_call_id" in row.keys() else None,
                    "tool_name": row["tool_name"] if "tool_name" in row.keys() else None,
                }
            )
        return history
