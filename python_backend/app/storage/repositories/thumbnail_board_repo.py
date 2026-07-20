"""SQLite repository for thumbnail board storage (QM-6T1, docs/
PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md).

Manages thumbnail_images and thumbnail_board_state tables, migrated from
the Electron legacy JSON DB (thumbnailBoard). `number` is permanent and
never renumbered. `parent_id` chains edit operations. `run_id` groups
loading placeholders with their eventual ready images.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.storage.db import connect, utc_now_iso

# Default board state singleton id — there is always exactly one row.
_BOARD_STATE_ID = "default"


class ThumbnailBoardRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    # ------------------------------------------------------------------ #
    # Image CRUD
    # ------------------------------------------------------------------ #

    def create_image(self, *, number: int, type_: str, status: str, path: str | None,
                     prompt: str, size: str, parent_id: str | None,
                     run_id: str | None) -> sqlite3.Row:
        image_id = uuid4().hex[:12]
        now = utc_now_iso()
        with connect(self._database_path) as conn:
            conn.execute(
                """
                INSERT INTO thumbnail_images
                    (id, number, type, status, path, prompt, size,
                     parent_id, run_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (image_id, number, type_, status, path, prompt, size,
                 parent_id, run_id, now, now),
            )
            conn.commit()
            return conn.execute(
                "SELECT * FROM thumbnail_images WHERE id = ?", (image_id,)
            ).fetchone()

    def get_image(self, image_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as conn:
            return conn.execute(
                "SELECT * FROM thumbnail_images WHERE id = ?", (image_id,)
            ).fetchone()

    def get_image_by_number(self, number: int) -> sqlite3.Row | None:
        with connect(self._database_path) as conn:
            return conn.execute(
                "SELECT * FROM thumbnail_images WHERE number = ?", (number,)
            ).fetchone()

    def update_image_status(self, image_id: str, *, status: str,
                            path: str | None = None) -> None:
        now = utc_now_iso()
        with connect(self._database_path) as conn:
            if path is not None:
                conn.execute(
                    "UPDATE thumbnail_images SET status=?, path=?, updated_at=? WHERE id=?",
                    (status, path, now, image_id),
                )
            else:
                conn.execute(
                    "UPDATE thumbnail_images SET status=?, updated_at=? WHERE id=?",
                    (status, now, image_id),
                )
            conn.commit()

    def delete_images_by_run_id(self, run_id: str, *, status: str | None = None) -> None:
        with connect(self._database_path) as conn:
            if status:
                conn.execute(
                    "DELETE FROM thumbnail_images WHERE run_id=? AND status=?",
                    (run_id, status),
                )
            else:
                conn.execute(
                    "DELETE FROM thumbnail_images WHERE run_id=?",
                    (run_id,),
                )
            conn.commit()

    def delete_loading_images(self) -> None:
        """Delete all loading-status images (startup cleanup)."""
        with connect(self._database_path) as conn:
            conn.execute("DELETE FROM thumbnail_images WHERE status='loading'")
            conn.commit()

    def list_images(self, page: int = 1, page_size: int = 9,
                    status: str | None = None) -> list[sqlite3.Row]:
        offset = (page - 1) * page_size
        with connect(self._database_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM thumbnail_images WHERE status=? ORDER BY number DESC LIMIT ? OFFSET ?",
                    (status, page_size, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM thumbnail_images ORDER BY number DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()
            return list(rows)

    def count_images(self, status: str | None = None) -> int:
        with connect(self._database_path) as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM thumbnail_images WHERE status=?",
                    (status,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM thumbnail_images",
                ).fetchone()
            return row["cnt"] if row else 0

    def get_max_number(self) -> int:
        with connect(self._database_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(number), 0) AS max_num FROM thumbnail_images"
            ).fetchone()
            return row["max_num"] if row else 0

    # ------------------------------------------------------------------ #
    # Board state
    # ------------------------------------------------------------------ #

    def get_or_create_board_state(self) -> sqlite3.Row:
        with connect(self._database_path) as conn:
            row = conn.execute(
                "SELECT * FROM thumbnail_board_state WHERE id=?",
                (_BOARD_STATE_ID,),
            ).fetchone()
            if row is not None:
                return row
            now = utc_now_iso()
            conn.execute(
                """
                INSERT INTO thumbnail_board_state
                    (id, selected_id, view, page, page_size, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (_BOARD_STATE_ID, None, "grid", 1, 9, now),
            )
            conn.commit()
            return conn.execute(
                "SELECT * FROM thumbnail_board_state WHERE id=?",
                (_BOARD_STATE_ID,),
            ).fetchone()

    def update_board_state(self, *, selected_id: str | None = None,
                           view: str | None = None,
                           page: int | None = None,
                           page_size: int | None = None) -> None:
        now = utc_now_iso()
        fields = {"updated_at": now}
        if selected_id is not None:
            fields["selected_id"] = selected_id
        if view is not None:
            fields["view"] = view
        if page is not None:
            fields["page"] = page
        if page_size is not None:
            fields["page_size"] = page_size

        set_clause = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())
        values.append(_BOARD_STATE_ID)

        with connect(self._database_path) as conn:
            conn.execute(
                f"UPDATE thumbnail_board_state SET {set_clause} WHERE id=?",
                values,
            )
            conn.commit()