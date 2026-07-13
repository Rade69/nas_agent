"""SQLite repository for screenshot metadata (FAZA 11).

Tracks captured screenshots (path, timestamp) separately from the
artifact system — screenshots are binary files served directly, not
wrapped as artifact objects.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from app.storage.db import connect, utc_now_iso


class ScreenshotRepository:
    """SQLite storage for the screenshots retention/audit table.

    Separate from ArtifactRepository on purpose — artifacts are general
    tool-output records shown in the Artifact panel; this table exists
    specifically to answer "what screenshot files exist on disk and when do
    they need to be deleted", independent of whether any given capture was
    also (ephemerally) shown as an artifact in a particular session.
    Context: agent_reports/2026-07-12_screenshot-privacy.md
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def record(self, file_path: str) -> sqlite3.Row:
        screenshot_id = f"shot_{uuid4().hex[:12]}"
        created_at = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                "INSERT INTO screenshots (id, file_path, created_at, sent_to_model) VALUES (?, ?, ?, 0)",
                (screenshot_id, file_path, created_at),
            )
            connection.commit()
            return connection.execute(
                "SELECT * FROM screenshots WHERE id = ?", (screenshot_id,)
            ).fetchone()

    def list(self, limit: int = 200) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM screenshots ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )

    def list_older_than(self, cutoff_iso: str) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM screenshots WHERE created_at < ?",
                    (cutoff_iso,),
                ).fetchall()
            )

    def delete(self, screenshot_id: str) -> None:
        with connect(self._database_path) as connection:
            connection.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))
            connection.commit()

    def delete_all(self) -> list[sqlite3.Row]:
        """Returns the rows that were deleted, so the caller can remove their files."""
        with connect(self._database_path) as connection:
            rows = list(connection.execute("SELECT * FROM screenshots").fetchall())
            connection.execute("DELETE FROM screenshots")
            connection.commit()
            return rows
