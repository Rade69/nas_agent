from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class ArtifactRepository:
    """SQLite storage for artifacts (FAZA 11).

    Artifacts are structured outputs produced by tools (text, markdown, code,
    image references, notes, mermaid, tables). The `artifacts` table was
    created in FAZA 7; this repo adds the CRUD/service layer used by the
    `artifact_create` / `artifact_get` / `artifact_list` tools and the event
    bridge (artifact:created events emitted on create).
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        artifact_id: str,
        type: str,
        title: str,
        content: dict[str, Any] | str,
        created_by_tool: str | None = None,
        conversation_id: str | None = None,
    ) -> sqlite3.Row:
        created_at = utc_now_iso()
        content_json = (
            content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, sort_keys=True)
        )
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO artifacts (id, created_at, type, title, content_json, created_by_tool, conversation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, created_at, type, title, content_json, created_by_tool, conversation_id),
            )
            connection.commit()
            return self._get(connection, artifact_id)

    def get(self, artifact_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return self._get(connection, artifact_id)

    def list(self, limit: int = 50, type: str | None = None) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            if type:
                rows = connection.execute(
                    "SELECT * FROM artifacts WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                    (type, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM artifacts ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return list(rows)

    def _get(self, connection: sqlite3.Connection, artifact_id: str) -> sqlite3.Row | None:
        return connection.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
