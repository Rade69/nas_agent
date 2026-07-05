from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.storage.db import connect


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ToolRunRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def create(
        self,
        *,
        run_id: str,
        tool_name: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any] | None,
        status: str,
        risk_level: str,
        requires_confirmation: bool,
        computer_mode: bool,
        duration_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO tool_runs (
                    id,
                    timestamp,
                    tool_name,
                    input_json,
                    output_json,
                    status,
                    risk_level,
                    requires_confirmation,
                    computer_mode,
                    error_code,
                    error_message,
                    duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    utc_now_iso(),
                    tool_name,
                    json.dumps(input_payload, ensure_ascii=False, sort_keys=True),
                    json.dumps(output_payload, ensure_ascii=False, sort_keys=True) if output_payload is not None else None,
                    status,
                    risk_level,
                    1 if requires_confirmation else 0,
                    1 if computer_mode else 0,
                    error_code,
                    error_message,
                    duration_ms,
                ),
            )
            connection.commit()

    def get(self, run_id: str) -> sqlite3.Row | None:
        with connect(self._database_path) as connection:
            return connection.execute("SELECT * FROM tool_runs WHERE id = ?", (run_id,)).fetchone()

    def list_recent(self, limit: int = 20) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute(
                    "SELECT * FROM tool_runs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )