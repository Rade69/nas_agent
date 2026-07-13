"""SQLite repository for plans and plan_steps (FAZA 9).

CRUD + status-filtered queries — used by PlanService.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class PlanRepository:
    """SQLite-backed storage for plans and their steps (FAZA 9).

    Plans replace the legacy Notepad planning workflow: a plan is an internal DB
    record (not a .txt/.md file) composed of ordered steps. Export to a file is
    only done when the user explicitly asks — see ARCHITECTURE_VOICE_FIRST_REVISED.md
    "Plans / Proposals".
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        plan_id: str,
        title: str,
        summary: str | None = None,
        steps: list[dict[str, Any]] | None = None,
    ) -> sqlite3.Row:
        created_at = utc_now_iso()
        steps = steps or []
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO plans (id, title, status, created_at, updated_at, summary)
                VALUES (?, ?, 'proposed', ?, ?, ?)
                """,
                (plan_id, title, created_at, created_at, summary),
            )
            for index, step in enumerate(steps):
                step_id = step.get("id") or f"{plan_id}-step-{index + 1}"
                connection.execute(
                    """
                    INSERT INTO plan_steps (id, plan_id, step_index, title, status, details_json)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        step_id,
                        plan_id,
                        index,
                        step.get("title", ""),
                        json.dumps(step.get("details", {}), ensure_ascii=False, sort_keys=True),
                    ),
                )
            connection.commit()
            return self._get_with_steps(connection, plan_id)

    def get(self, plan_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return self._get_with_steps(connection, plan_id)

    def list(self, limit: int = 50) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            plan_rows = connection.execute(
                "SELECT * FROM plans ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._attach_steps(connection, row) for row in plan_rows]

    def update(
        self,
        plan_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        status: str | None = None,
    ) -> sqlite3.Row | None:
        updated_at = utc_now_iso()
        with connect(self._database_path) as connection:
            current = self._get_with_steps(connection, plan_id)
            if current is None:
                return None
            new_title = title if title is not None else current["title"]
            new_summary = summary if summary is not None else current["summary"]
            new_status = status if status is not None else current["status"]
            connection.execute(
                """
                UPDATE plans
                SET title = ?, summary = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_title, new_summary, new_status, updated_at, plan_id),
            )
            connection.commit()
            return self._get_with_steps(connection, plan_id)

    def update_step(
        self,
        plan_id: str,
        step_id: str,
        *,
        status: str | None = None,
        title: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            row = connection.execute(
                "SELECT * FROM plan_steps WHERE id = ? AND plan_id = ?",
                (step_id, plan_id),
            ).fetchone()
            if row is None:
                return None
            new_status = status if status is not None else row["status"]
            new_title = title if title is not None else row["title"]
            new_details_json = (
                json.dumps(details, ensure_ascii=False, sort_keys=True)
                if details is not None
                else row["details_json"]
            )
            connection.execute(
                """
                UPDATE plan_steps
                SET status = ?, title = ?, details_json = ?
                WHERE id = ? AND plan_id = ?
                """,
                (new_status, new_title, new_details_json, step_id, plan_id),
            )
            connection.execute(
                "UPDATE plans SET updated_at = ? WHERE id = ?",
                (utc_now_iso(), plan_id),
            )
            connection.commit()
            return self._get_with_steps(connection, plan_id)

    def _get_with_steps(self, connection: sqlite3.Connection, plan_id: str) -> sqlite3.Row | None:
        plan = connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if plan is None:
            return None
        return self._attach_steps(connection, plan)

    def _attach_steps(self, connection: sqlite3.Connection, plan_row: sqlite3.Row) -> sqlite3.Row:
        steps = connection.execute(
            "SELECT * FROM plan_steps WHERE plan_id = ? ORDER BY step_index ASC",
            (plan_row["id"],),
        ).fetchall()
        # sqlite3.Row does not allow attaching arbitrary keys at runtime; emulate a
        # combined row by constructing a dict-like view consumed by services below.
        return _PlanWithStepsRow(plan_row, steps)


class _PlanWithStepsRow:
    """Wrapper combining a plan row and its ordered step rows.

    sqlite3.Row does not support nesting, so we expose a mapping interface that
    returns the plan's columns and a synthetic `steps` column holding the list
    of step rows. Services convert this into response models.
    """

    __slots__ = ("_plan", "steps")

    def __init__(self, plan: sqlite3.Row, steps: list[sqlite3.Row]) -> None:
        self._plan = plan
        self.steps = steps

    def __getitem__(self, key: str) -> Any:
        if key == "steps":
            return self.steps
        return self._plan[key]

    def keys(self) -> list[str]:
        return list(self._plan.keys()) + ["steps"]
