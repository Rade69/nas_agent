from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.storage.db import initialize_database
from app.storage.repositories.settings_repo import SettingsRepository


@pytest.fixture
def _restore_user_name():
    # `user_name` is a single shared value in the real data/ricky.sqlite file
    # (no per-test DB isolation exists in this project's test suite — see
    # agent_reports/2026-07-11_settings-panel-foundation.md), unlike
    # confirmations/plans which create uniquely-id'd rows. Without explicit
    # cleanup, a test that changes it would leak into later test runs and
    # into the developer's real app data.
    settings = get_settings()
    initialize_database(settings)
    repo = SettingsRepository(settings.database_path)
    original = repo.get("user_name")
    yield
    repo.set("user_name", original if original is not None else "Riley")


@pytest.fixture
def _restore_interface_language():
    # Same reasoning as _restore_user_name — dijeljena prava SQLite baza,
    # nema test-izolacije za ovaj endpoint. Čuva/vraća interface_language
    # da testovi koji ga mijenjaju ne procure u druge testove ili u
    # developerovu stvarnu app bazu.
    settings = get_settings()
    initialize_database(settings)
    repo = SettingsRepository(settings.database_path)
    original = repo.get("interface_language")
    yield
    repo.set("interface_language", original if original is not None else "sr-Latn")


@pytest.fixture
def _restore_quick_commands():
    # Same reasoning as _restore_user_name.
    settings = get_settings()
    initialize_database(settings)
    repo = SettingsRepository(settings.database_path)
    original = repo.get("quick_commands")
    yield
    repo.set("quick_commands", original if original is not None else [])


def test_get_settings_default_user_name(_restore_user_name) -> None:
    repo = SettingsRepository(get_settings().database_path)
    repo.set("user_name", "Riley")
    with TestClient(app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    assert response.json()["user_name"] == "Riley"


def test_patch_settings_updates_user_name(_restore_user_name) -> None:
    with TestClient(app) as client:
        response = client.patch("/settings", json={"user_name": "Radovan"})
        assert response.status_code == 200
        assert response.json()["user_name"] == "Radovan"

        follow_up = client.get("/settings")
        assert follow_up.json()["user_name"] == "Radovan"


def test_patch_settings_with_unset_field_does_not_overwrite(_restore_user_name) -> None:
    with TestClient(app) as client:
        client.patch("/settings", json={"user_name": "Radovan"})
        # Empty body: user_name is unset (not explicitly None), so it must be
        # left untouched — exercises `model_dump(exclude_unset=True)` in the
        # route, not just the service's `if value is None` guard.
        response = client.patch("/settings", json={})

    assert response.status_code == 200
    assert response.json()["user_name"] == "Radovan"


def test_unknown_stored_keys_are_ignored(_restore_user_name) -> None:
    repo = SettingsRepository(get_settings().database_path)
    repo.set("some_future_setting_not_yet_modeled", "whatever")
    with TestClient(app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    # Only declared UserSettings fields are ever returned.
    assert set(response.json().keys()) == {"user_name", "interface_language", "quick_commands"}


def test_get_settings_default_interface_language(_restore_interface_language) -> None:
    repo = SettingsRepository(get_settings().database_path)
    repo.set("interface_language", "sr-Latn")
    with TestClient(app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    assert response.json()["interface_language"] == "sr-Latn"


def test_patch_settings_updates_interface_language(_restore_interface_language) -> None:
    with TestClient(app) as client:
        response = client.patch("/settings", json={"interface_language": "en"})
        assert response.status_code == 200
        assert response.json()["interface_language"] == "en"

        follow_up = client.get("/settings")
        assert follow_up.json()["interface_language"] == "en"


def test_patch_settings_with_unset_field_does_not_overwrite_language(
    _restore_interface_language,
) -> None:
    with TestClient(app) as client:
        client.patch("/settings", json={"interface_language": "de"})
        response = client.patch("/settings", json={})

    assert response.status_code == 200
    assert response.json()["interface_language"] == "de"


def test_get_settings_default_quick_commands_is_empty(_restore_quick_commands) -> None:
    # Empty = frontend falls back to the built-in localized defaults
    # (idle.cmd* i18n keys) — see app/schemas/settings.py UserSettings docstring.
    with TestClient(app) as client:
        response = client.get("/settings")

    assert response.status_code == 200
    assert response.json()["quick_commands"] == []


def test_patch_settings_updates_quick_commands(_restore_quick_commands) -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/settings", json={"quick_commands": ["Otvori deklaracije", "Napravi izvještaj"]}
        )
        assert response.status_code == 200
        assert response.json()["quick_commands"] == ["Otvori deklaracije", "Napravi izvještaj"]

        follow_up = client.get("/settings")
        assert follow_up.json()["quick_commands"] == ["Otvori deklaracije", "Napravi izvještaj"]


def test_patch_settings_can_clear_quick_commands_back_to_empty(_restore_quick_commands) -> None:
    with TestClient(app) as client:
        client.patch("/settings", json={"quick_commands": ["Nešto"]})
        # Explicit empty list (not an unset field) must actually save as empty,
        # not be treated as "nothing provided" — exercises the `value is None`
        # vs `value == []` distinction in SettingsService.update().
        response = client.patch("/settings", json={"quick_commands": []})

    assert response.status_code == 200
    assert response.json()["quick_commands"] == []
