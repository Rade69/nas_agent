from __future__ import annotations

import json
from typing import Any

from app.storage.repositories.records_repo import RecordsRepository


class RecordsService:
    """Application layer over RecordsRepository (FAZA 11)."""

    def __init__(self, repository: RecordsRepository) -> None:
        self._repository = repository

    def create(self, *, collection: str, title: str, fields: dict[str, Any]) -> dict[str, Any]:
        from uuid import uuid4

        record_id = f"rec_{uuid4().hex[:12]}"
        row = self._repository.create(
            record_id=record_id,
            collection=collection,
            title=title,
            fields=fields,
        )
        return self._to_dict(row)

    def list_in_collection(self, collection: str, limit: int = 50) -> list[dict[str, Any]]:
        return [self._to_dict(row) for row in self._repository.list_in_collection(collection, limit=limit)]

    def search(self, *, collection: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return [
            self._to_dict(row)
            for row in self._repository.search(collection=collection, query=query, limit=limit)
        ]

    def get(self, record_id: str) -> dict[str, Any] | None:
        row = self._repository.get(record_id)
        return self._to_dict(row) if row else None

    def update(
        self,
        *,
        record_id: str,
        title: str | None = None,
        fields_merge: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        row = self._repository.update(
            record_id=record_id,
            title=title,
            fields_merge=fields_merge,
        )
        return self._to_dict(row) if row else None

    def delete(self, record_id: str) -> bool:
        return self._repository.delete(record_id)

    def _to_dict(self, row: Any) -> dict[str, Any]:
        try:
            fields = json.loads(row["fields_json"]) if row["fields_json"] else {}
        except (json.JSONDecodeError, TypeError):
            fields = {}
        return {
            "id": row["id"],
            "collection": row["collection"],
            "title": row["title"],
            "fields": fields,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
