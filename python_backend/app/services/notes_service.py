"""Notes CRUD service (FAZA 11).

Migrated from Electron's JSON database to SQLite. Handles text search
by tag and full-text content filtering.
"""
from __future__ import annotations

import json
from typing import Any

from app.storage.repositories.notes_repo import NotesRepository


class NotesService:
    """Application layer over NotesRepository (FAZA 11)."""

    def __init__(self, repository: NotesRepository) -> None:
        self._repository = repository

    def create(self, *, text: str, tags: list[str]) -> dict[str, Any]:
        from uuid import uuid4

        note_id = f"note_{uuid4().hex[:12]}"
        row = self._repository.create(note_id=note_id, text=text, tags=tags)
        return self._to_dict(row)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._to_dict(row) for row in self._repository.list(limit=limit)]

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return [self._to_dict(row) for row in self._repository.search(query=query, limit=limit)]

    def _to_dict(self, row: Any) -> dict[str, Any]:
        try:
            tags = json.loads(row["tags_json"]) if row["tags_json"] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        return {
            "id": row["id"],
            "text": row["text"],
            "tags": tags,
            "createdAt": row["created_at"],
        }
