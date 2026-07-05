import json
import sqlite3

from app.core.config import Settings
from app.storage.db import initialize_database


EXPECTED_TABLES = {
    "settings",
    "realtime_sessions",
    "voice_turns",
    "transcripts",
    "activity_events",
    "confirmations",
    "plans",
    "plan_steps",
    "tool_runs",
    "artifacts",
}


def test_initialize_database_creates_mvp_tables(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)

    with sqlite3.connect(settings.database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_tool_runs_table_accepts_json_payloads(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)

    with sqlite3.connect(settings.database_path) as connection:
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
                duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run_1",
                "2026-07-05T00:00:00+00:00",
                "echo",
                json.dumps({"text": "hello"}),
                json.dumps({"ok": True}),
                "success",
                "low",
                0,
                0,
                1,
            ),
        )
        row = connection.execute("SELECT * FROM tool_runs WHERE id = ?", ("run_1",)).fetchone()

    assert row is not None