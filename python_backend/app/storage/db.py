from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS realtime_sessions (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        model TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS voice_turns (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        role TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        status TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(session_id) REFERENCES realtime_sessions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transcripts (
        id TEXT PRIMARY KEY,
        voice_turn_id TEXT,
        session_id TEXT,
        kind TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(voice_turn_id) REFERENCES voice_turns(id),
        FOREIGN KEY(session_id) REFERENCES realtime_sessions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS activity_events (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        title TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS confirmations (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        action_name TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        risk_level TEXT NOT NULL,
        plan_id TEXT,
        summary TEXT,
        tool_name TEXT,
        payload_hash TEXT,
        expires_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plans (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        summary TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plan_steps (
        id TEXT PRIMARY KEY,
        plan_id TEXT NOT NULL,
        step_index INTEGER NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        details_json TEXT NOT NULL DEFAULT '{}',
        FOREIGN KEY(plan_id) REFERENCES plans(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_runs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        input_json TEXT NOT NULL,
        output_json TEXT,
        status TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        requires_confirmation INTEGER NOT NULL,
        computer_mode INTEGER NOT NULL,
        error_code TEXT,
        error_message TEXT,
        duration_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        content_json TEXT NOT NULL,
        created_by_tool TEXT,
        conversation_id TEXT
    )
    """,
]


def _existing_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add a column to an existing table if missing (idempotent dev migration).

    The SQLite schema uses CREATE TABLE IF NOT EXISTS, so columns added in later
    phases would never appear on an already-created dev database. This helper
    keeps the local dev DB in sync without introducing a full migration framework
    (which is intentionally out of scope for the MVP — see MIGRATION_PLAN.md).
    """
    if column not in _existing_columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


MIGRATIONS = [
    ("confirmations", "plan_id", "TEXT"),
    ("confirmations", "summary", "TEXT"),
    # FAZA 10: permission engine binds confirmations to a specific tool call so an
    # approved confirmation can't be replayed against a different tool/payload/app.
    ("confirmations", "tool_name", "TEXT"),
    ("confirmations", "payload_hash", "TEXT"),
    ("confirmations", "expires_at", "TEXT"),
]


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with connect(settings.database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        for table, column, definition in MIGRATIONS:
            _ensure_column(connection, table, column, definition)
        connection.commit()