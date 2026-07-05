from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class EventRepository:
    """SQLite-backed event store for the backend -> UI event bridge (FAZA 11).

    Uses the existing `activity_events` table (created in FAZA 7) as the event
    store. Events are appended on tool start/complete/fail and artifact:created.
    The UI polls `GET /events` (with a `since` cursor) to render artifact
    updates and tool progress without a WebSocket dependency.

    Event types (see ARCHITECTURE_VOICE_FIRST_REVISED.md event naming):
      backend.ready, tool.started, tool.completed, tool.failed,
      artifact.created, artifact.updated, permission.confirmation_required
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def emit(
        self,
        *,
        event_type: str,
        title: str | None = None,
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> sqlite3.Row:
        timestamp = utc_now_iso()
        from uuid import uuid4

        event_id = f"evt_{uuid4().hex[:16]}"
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO activity_events (id, type, timestamp, title, details_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event_type,
                    timestamp,
                    title,
                    json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.commit()
            return connection.execute(
                "SELECT * FROM activity_events WHERE id = ?", (event_id,)
            ).fetchone()

    def list_recent(self, limit: int = 50) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM activity_events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )

    def list_since(self, since_timestamp: str, limit: int = 100) -> list[sqlite3.Row]:
        """Return events with timestamp > since_timestamp, oldest first (UI order)."""
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    """
                    SELECT * FROM activity_events
                    WHERE timestamp > ?
                    ORDER BY timestamp ASC LIMIT ?
                    """,
                    (since_timestamp, limit),
                ).fetchall()
            )
