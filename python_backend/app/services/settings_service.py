from __future__ import annotations

from typing import Any

from app.schemas.settings import UserSettings
from app.storage.repositories.settings_repo import SettingsRepository


class SettingsService:
    """Typed view over the generic key/value settings store.

    Only fields declared on UserSettings are read back out (unknown stored
    keys are ignored, not an error) — adding a new preference means adding a
    field to UserSettings with a default, nothing else changes here.
    """

    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    def get(self) -> UserSettings:
        stored = self._repository.get_all()
        known = {key: value for key, value in stored.items() if key in UserSettings.model_fields}
        return UserSettings(**known)

    def update(self, **fields: Any) -> UserSettings:
        for key, value in fields.items():
            if key not in UserSettings.model_fields:
                continue
            if value is None:
                continue
            self._repository.set(key, value)
        return self.get()
