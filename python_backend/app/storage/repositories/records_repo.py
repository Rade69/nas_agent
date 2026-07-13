"""SQLite repository for records (FAZA 11).

CRUD + collection-scoped search for the RecordsService.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class RecordsRepository:
    """SQLite storage for Ricky's structured records (FAZA 11).

    Replaces the Electron JSON `db.records` array. A record is a titled item in
    a named collection with arbitrary JSON fields. records_delete is the only
    one flagged for confirmation in the tool definition (destructive = critical).
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        record_id: str,
        collection: str,
        title: str,
        fields: dict[str, Any],
    ) -> sqlite3.Row:
        created_at = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO records (id, collection, title, fields_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    collection,
                    title,
                    json.dumps(fields, ensure_ascii=False, sort_keys=True),
                    created_at,
                    created_at,
                ),
            )
            connection.commit()
            return self._get(connection, record_id)

    def list_in_collection(self, collection: str, limit: int = 50) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM records WHERE collection = ? ORDER BY created_at DESC LIMIT ?",
                    (collection, limit),
                ).fetchall()
            )

    def search(self, collection: str, query: str, limit: int = 50) -> list[sqlite3.Row]:
        pattern = f"%{query.lower()}%" if query else "%"
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM records
                    WHERE collection = ?
                      AND (LOWER(title) LIKE ? OR LOWER(fields_json) LIKE ?)
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (collection, pattern, pattern, limit),
                ).fetchall()
            )

    def get(self, record_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return self._get(connection, record_id)

    def update(
        self,
        *,
        record_id: str,
        title: str | None = None,
        fields_merge: dict[str, Any] | None = None,
    ) -> sqlite3.Row | None:
        updated_at = utc_now_iso()
        with connect(self._database_path) as connection:
            current = self._get(connection, record_id)
            if current is None:
                return None
            new_title = title if title is not None else current["title"]
            if fields_merge is not None:
                existing = json.loads(current["fields_json"] or "{}")
                merged = {**existing, **fields_merge}
            else:
                merged = json.loads(current["fields_json"] or "{}")
            connection.execute(
                """
                UPDATE records SET title = ?, fields_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, json.dumps(merged, ensure_ascii=False, sort_keys=True), updated_at, record_id),
            )
            connection.commit()
            return self._get(connection, record_id)

    def delete(self, record_id: str) -> bool:
        with connect(self._database_path) as connection:
            cursor = connection.execute("DELETE FROM records WHERE id = ?", (record_id,))
            connection.commit()
            return cursor.rowcount > 0

    def _get(self, connection: sqlite3.Connection, record_id: str) -> sqlite3.Row | None:
        return connection.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
