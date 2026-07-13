"""User-facing preferences Pydantic model.

Deliberately named UserSettings to avoid confusion with
app.core.config.Settings (process/environment config). New preferences
are added here as new fields with sensible defaults — the underlying
key/value SQLite table and generic service/API need no changes.
"""
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
    # Name the model refers to itself as / is addressed by in the system
    # prompt (electron/ipc_handlers/realtime.cjs's buildRickyInstructions) —
    # mirrors user_name's pattern exactly. Context: agent_reports/
    # 2026-07-13_agent-name-setting.md
    agent_name: str = "Ricky"
    interface_language: str = "sr-Latn"
    # Empty = use the built-in localized defaults (Napiši email/Napravi
    # screenshot/Otvori Notepad/Planiraj sastanak — see src/i18n/locales/*.json
    # idle.cmd*). Non-empty = user has customized their quick commands panel,
    # use exactly this list instead. Each string doubles as both the button
    # label and the literal text sent via onQuickCommand — same mechanism the
    # built-in defaults already use, not translated (user-authored content).
    # Context: agent_reports/2026-07-12_custom-quick-commands.md
    quick_commands: list[str] = []


class UserSettingsUpdateRequest(BaseModel):
    user_name: str | None = None
    agent_name: str | None = None
    interface_language: str | None = None
    quick_commands: list[str] | None = None
