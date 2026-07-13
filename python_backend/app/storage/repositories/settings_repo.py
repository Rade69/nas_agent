"""SQLite repository for the key/value settings store.

Generic get/set/get_all operations — the typed SettingsService layer
above this decides which keys to expose based on UserSettings.model_fields.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.storage.db import connect, utc_now_iso


class SettingsRepository:
    """SQLite-backed key/value storage for user preferences.

    Deliberately generic (get/set/get_all on arbitrary string keys) rather
    than one column per setting — new preferences just need a new key, no
    schema migration. The typed contract (which keys exist, their defaults)
    lives one layer up in SettingsService / app.schemas.settings.UserSettings.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def get(self, key: str) -> Any | None:
        with connect(self._database_path) as connection:
            row = connection.execute(
                "SELECT value_json FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return json.loads(row["value_json"]) if row else None

    def get_all(self) -> dict[str, Any]:
        with connect(self._database_path) as connection:
            rows = connection.execute("SELECT key, value_json FROM settings").fetchall()
            return {row["key"]: json.loads(row["value_json"]) for row in rows}

    def set(self, key: str, value: Any) -> None:
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), utc_now_iso()),
            )
            connection.commit()
