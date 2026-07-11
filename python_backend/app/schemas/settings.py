from __future__ import annotations

from pydantic import BaseModel

# User-facing preferences (name displayed in the prompt, future STT engine
# choice, etc.) — NOT app.core.config.Settings, which is process/environment
# configuration (host, tokens, API keys). Deliberately named UserSettings to
# avoid confusion between the two. Stored as individual key/value rows in the
# `settings` SQLite table (see app/storage/db.py SCHEMA_STATEMENTS — the table
# has existed since FAZA 7 but was never wired to a repository/API until now).
# New preferences are added here as new fields with sensible defaults; no
# database migration is needed since the underlying table is key/value.
class UserSettings(BaseModel):
    user_name: str = "Riley"
    interface_language: str = "sr-Latn"


class UserSettingsUpdateRequest(BaseModel):
    user_name: str | None = None
    interface_language: str | None = None
