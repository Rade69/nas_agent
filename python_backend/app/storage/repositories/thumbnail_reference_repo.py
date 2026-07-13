"""SQLite repository for thumbnail reference images (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md).

Stores validated reference-image metadata under an opaque id — canonical_path
is only ever read back by thumbnail_reference_service.resolve(), never
returned to a model or the renderer directly.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from app.storage.db import connect, utc_now_iso


class ThumbnailReferenceRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        canonical_path: str,
        label: str | None,
        mime_type: str | None,
        size_bytes: int | None,
    ) -> sqlite3.Row:
        reference_id = f"ref_{uuid4().hex[:12]}"
        created_at = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO thumbnail_references
                    (id, canonical_path, label, mime_type, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (reference_id, canonical_path, label, mime_type, size_bytes, created_at),
            )
            connection.commit()
            return connection.execute(
                "SELECT * FROM thumbnail_references WHERE id = ?", (reference_id,)
            ).fetchone()

    def get(self, reference_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return connection.execute(
                "SELECT * FROM thumbnail_references WHERE id = ?", (reference_id,)
            ).fetchone()

    def list(self, limit: int = 100) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM thumbnail_references ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )
