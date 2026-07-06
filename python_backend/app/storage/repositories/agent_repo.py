from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class AgentConversationRepository:
    """SQLite storage for agent runtime conversation state (FAZA 15).

    A conversation is a linear message history (user/assistant/tool roles).
    No multi-agent orchestration or branching — single LocalDesktopAssistant
    per conversation, per the FAZA 15 scope in MIGRATION_PLAN.md.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create_conversation(self, *, conversation_id: str, title: str | None = None) -> sqlite3.Row:
        now = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                "INSERT INTO agent_conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, title, now, now),
            )
            connection.commit()
            return self._get_conversation(connection, conversation_id)

    def get_conversation(self, conversation_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return self._get_conversation(connection, conversation_id)

    def touch_conversation(self, conversation_id: str) -> None:
        with connect(self._database_path) as connection:
            connection.execute(
                "UPDATE agent_conversations SET updated_at = ? WHERE id = ?",
                (utc_now_iso(), conversation_id),
            )
            connection.commit()

    def add_message(
        self,
        *,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
    ) -> sqlite3.Row:
        created_at = utc_now_iso()
        tool_calls_json = json.dumps(tool_calls, ensure_ascii=False) if tool_calls is not None else None
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO agent_messages
                    (id, conversation_id, role, content, tool_calls_json, tool_call_id, tool_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, role, content, tool_calls_json, tool_call_id, tool_name, created_at),
            )
            connection.commit()
            return self._get_message(connection, message_id)

    def list_messages(self, conversation_id: str) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM agent_messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,),
            ).fetchall()
            return list(rows)

    def _get_conversation(self, connection: sqlite3.Connection, conversation_id: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM agent_conversations WHERE id = ?", (conversation_id,)
        ).fetchone()

    def _get_message(self, connection: sqlite3.Connection, message_id: str) -> sqlite3.Row | None:
        return connection.execute("SELECT * FROM agent_messages WHERE id = ?", (message_id,)).fetchone()
