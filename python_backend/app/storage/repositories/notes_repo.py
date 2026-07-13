"""SQLite repository for notes (FAZA 11).

CRUD + tag-search for the NotesService.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class NotesRepository:
    """SQLite storage for Ricky's fun notes (FAZA 11).

    Replaces the Electron JSON `db.notes` array. Notes are low-risk memory items
    (text + tags) — no confirmation or computer_mode required. See
    SECURITY_MODEL.md risk levels.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(self, *, note_id: str, text: str, tags: list[str]) -> sqlite3.Row:
        created_at = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO notes (id, text, tags_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (note_id, text, json.dumps(tags, ensure_ascii=False, sort_keys=True), created_at),
            )
            connection.commit()
            return self._get(connection, note_id)

    def list(self, limit: int = 50) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )

    def search(self, query: str, limit: int = 50) -> list[sqlite3.Row]:
        pattern = f"%{query.lower()}%"
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM notes
                    WHERE LOWER(text) LIKE ? OR LOWER(tags_json) LIKE ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (pattern, pattern, limit),
                ).fetchall()
            )

    def _get(self, connection: sqlite3.Connection, note_id: str) -> sqlite3.Row | None:
        return connection.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
