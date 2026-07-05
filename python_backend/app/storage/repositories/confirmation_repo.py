from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class ConfirmationRepository:
    """SQLite-backed storage for confirmation records (FAZA 9).

    Confirmations are the safety/orchestration primitive used to gate risky tool
    execution. A pending confirmation is created by whoever proposes an action
    (the agent runtime, a tool bridge, or the UI directly); it is later resolved
    via approve/reject/cancel. The permission/risk layer that *issues* these
    confirmations is FAZA 10 — this module only owns storage + transitions.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        confirmation_id: str,
        action_name: str,
        payload: dict[str, Any],
        risk_level: str,
        plan_id: str | None = None,
        summary: str | None = None,
    ) -> sqlite3.Row:
        created_at = utc_now_iso()
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO confirmations (
                    id, status, created_at, resolved_at,
                    action_name, payload_json, risk_level,
                    plan_id, summary
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    confirmation_id,
                    "pending",
                    created_at,
                    action_name,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    risk_level,
                    plan_id,
                    summary,
                ),
            )
            connection.commit()
            return self._get(connection, confirmation_id)

    def get(self, confirmation_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return self._get(connection, confirmation_id)

    def list(self, status: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM confirmations WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM confirmations ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return list(rows)

    def resolve(self, confirmation_id: str, status: str) -> sqlite3.Row | None:
        """Transition a confirmation to a resolved state (approved/rejected/expired/cancelled)."""
        if status not in {"approved", "rejected", "expired", "cancelled"}:
            raise ValueError(f"Invalid resolved status: {status}")
        resolved_at = utc_now_iso()
        with connect(self._database_path) as connection:
            current = self._get(connection, confirmation_id)
            if current is None:
                return None
            if current["status"] != "pending":
                # Idempotent: return existing record unchanged if already resolved to same state.
                if current["status"] == status:
                    return current
                return current
            connection.execute(
                """
                UPDATE confirmations
                SET status = ?, resolved_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (status, resolved_at, confirmation_id),
            )
            connection.commit()
            return self._get(connection, confirmation_id)

    def list_pending(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.list(status="pending", limit=limit)

    def _get(self, connection: sqlite3.Connection, confirmation_id: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM confirmations WHERE id = ?",
            (confirmation_id,),
        ).fetchone()
