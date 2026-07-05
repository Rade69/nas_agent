from __future__ import annotations

import json
from typing import Any

from app.storage.repositories.artifact_repo import ArtifactRepository


class ArtifactService:
    """Application layer over ArtifactRepository (FAZA 11).

    Creating an artifact also emits an `artifact.created` event through the
    event bus so the UI artifact panel can refresh via the event bridge.
    """

    def __init__(self, repository: ArtifactRepository, event_bus: "EventBus | None" = None) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def create(
        self,
        *,
        type: str,
        title: str,
        content: str,
        created_by_tool: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        from uuid import uuid4

        artifact_id = f"art_{uuid4().hex[:12]}"
        row = self._repository.create(
            artifact_id=artifact_id,
            type=type,
            title=title,
            content=content,
            created_by_tool=created_by_tool,
            conversation_id=conversation_id,
        )
        data = self._to_dict(row)
        if self._event_bus is not None:
            self._event_bus.emit(
                "artifact.created",
                title=f"Artifact: {title}",
                details={"artifact_id": artifact_id, "type": type},
            )
        return data

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        row = self._repository.get(artifact_id)
        return self._to_dict(row) if row else None

    def list(self, limit: int = 50, type: str | None = None) -> list[dict[str, Any]]:
        rows = self._repository.list(limit=limit, type=type)
        return [self._to_dict(row) for row in rows]

    def _to_dict(self, row: Any) -> dict[str, Any]:
        content_json = row["content_json"]
        try:
            content = json.loads(content_json) if content_json else ""
        except (json.JSONDecodeError, TypeError):
            content = content_json
        return {
            "id": row["id"],
            "type": row["type"],
            "title": row["title"],
            "content": content,
            "createdByTool": row["created_by_tool"],
            "conversationId": row["conversation_id"],
            "createdAt": row["created_at"],
        }
