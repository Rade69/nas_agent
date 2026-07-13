"""Pydantic models for the agent runtime REST API (FAZA 15).

Request/response shapes for POST /agent/message and GET /agent/conversations.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentRole = Literal["user", "assistant", "tool"]


class AgentToolCall(BaseModel):
    id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: AgentRole
    content: str | None = None
    tool_name: str | None = None
    created_at: str


class AgentConversationResponse(BaseModel):
    id: str
    title: str | None = None
    created_at: str
    updated_at: str
    messages: list[AgentMessageResponse] = Field(default_factory=list)


class AgentSendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None
    computer_mode: bool = False


class AgentSendMessageResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
