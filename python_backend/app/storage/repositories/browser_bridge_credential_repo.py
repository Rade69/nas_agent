"""SQLite repository for browser bridge (C0) install credentials.

Persists per-install pairing credentials so a normal app restart doesn't
force the user to re-pair the extension every time. See
agent_reports/2026-07-16_browser-bridge-wrong-broker-port-fix.md for why
this was changed from in-memory-only.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.storage.db import connect


class BrowserBridgeCredentialRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def upsert(
        self,
        *,
        installation_id: str,
        profile_id: str,
        credential: str,
        browser_kind: str,
        profile_label: str,
        extension_version: str,
        created_at: str,
        last_seen_at: str | None,
        revoked: bool,
    ) -> None:
        with connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO browser_bridge_credentials
                    (installation_id, profile_id, credential, browser_kind,
                     profile_label, extension_version, created_at, last_seen_at, revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(installation_id) DO UPDATE SET
                    profile_id = excluded.profile_id,
                    credential = excluded.credential,
                    browser_kind = excluded.browser_kind,
                    profile_label = excluded.profile_label,
                    extension_version = excluded.extension_version,
                    last_seen_at = excluded.last_seen_at,
                    revoked = excluded.revoked
                """,
                (
                    installation_id, profile_id, credential, browser_kind,
                    profile_label, extension_version, created_at, last_seen_at,
                    1 if revoked else 0,
                ),
            )
            connection.commit()

    def list(self) -> list[sqlite3.Row]:
        with connect(self._database_path) as connection:
            return list(
                connection.execute("SELECT * FROM browser_bridge_credentials").fetchall()
            )
