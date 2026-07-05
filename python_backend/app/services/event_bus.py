from __future__ import annotations

import json
from typing import Any

from app.storage.repositories.event_repo import EventRepository


class EventBus:
    """Backend -> UI event bridge service (FAZA 11).

    Thin wrapper over EventRepository that emits typed events into the
    `activity_events` table. The UI polls `GET /events?since=<timestamp>` to
    receive new events in order. Event types follow the convention from
    ARCHITECTURE_VOICE_FIRST_REVISED.md (dotted internal names):
      backend.ready, tool.started, tool.completed, tool.failed,
      artifact.created, artifact.updated, permission.confirmation_required
    """

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    def emit(
        self,
        event_type: str,
        *,
        title: str | None = None,
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = self._repository.emit(
            event_type=event_type,
            title=title,
            details=details,
            metadata=metadata,
        )
        return self._to_dict(row)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return [self._to_dict(row) for row in self._repository.list_recent(limit=limit)]

    def since(self, since_timestamp: str, limit: int = 100) -> list[dict[str, Any]]:
        return [
            self._to_dict(row)
            for row in self._repository.list_since(since_timestamp, limit=limit)
        ]

    def _to_dict(self, row: Any) -> dict[str, Any]:
        try:
            details = json.loads(row["details_json"]) if row["details_json"] else {}
        except (json.JSONDecodeError, TypeError):
            details = {}
        try:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return {
            "id": row["id"],
            "type": row["type"],
            "timestamp": row["timestamp"],
            "title": row["title"],
            "details": details,
            "metadata": metadata,
        }
