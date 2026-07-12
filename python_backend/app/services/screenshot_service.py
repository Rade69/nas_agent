from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

from app.storage.repositories.screenshot_repo import ScreenshotRepository

# Context: agent_reports/2026-07-12_screenshot-privacy.md — FABLE-5 GUI review
# finding #3. Fixed default rather than a Settings-configurable value for this
# first pass — keeps scope to "screenshots don't accumulate forever" without
# also designing a new settings field; can become configurable later if a
# real need shows up.
DEFAULT_RETENTION_DAYS = 30


class ScreenshotService:
    def __init__(self, repository: ScreenshotRepository, retention_days: int = DEFAULT_RETENTION_DAYS) -> None:
        self._repository = repository
        self._retention_days = retention_days

    def record(self, file_path: str) -> None:
        self._repository.record(file_path)

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        self.cleanup_expired()
        return [self._to_dict(row) for row in self._repository.list(limit=limit)]

    def delete_all(self) -> int:
        rows = self._repository.delete_all()
        for row in rows:
            self._delete_file(row["file_path"])
        return len(rows)

    def cleanup_expired(self) -> int:
        """Deletes screenshots (DB rows + files) older than the retention
        window. Called lazily on every GET /screenshots rather than run on a
        schedule — this is a single-user desktop app with no long-running
        server process guaranteed to be up at a fixed time, so "clean up
        whenever someone actually looks at the list" is simpler and just as
        effective as a cron-style scheduler, and is also run once at backend
        startup (see app/main.py) so stale files don't wait for a UI visit."""
        cutoff = (datetime.now(UTC) - timedelta(days=self._retention_days)).isoformat()
        expired = self._repository.list_older_than(cutoff)
        for row in expired:
            self._delete_file(row["file_path"])
            self._repository.delete(row["id"])
        return len(expired)

    def _delete_file(self, file_path: str) -> None:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass  # already gone — not an error, just means nothing to clean up

    def _to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "filePath": row["file_path"],
            "createdAt": row["created_at"],
            "sentToModel": bool(row["sent_to_model"]),
        }
