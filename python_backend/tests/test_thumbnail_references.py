"""Tests for S-03 thumbnail reference image handling (docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.core.errors import AppError
from app.main import create_app
from app.services.thumbnail_reference_service import ThumbnailReferenceService
from app.storage.repositories.thumbnail_reference_repo import ThumbnailReferenceRepository


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def _service(tmp_path) -> ThumbnailReferenceService:
    from app.core.config import Settings
    from app.storage.db import initialize_database

    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)
    return ThumbnailReferenceService(ThumbnailReferenceRepository(settings.database_path))


# ---------------------------------------------------------------------------
# Service-level: validation
# ---------------------------------------------------------------------------


class TestThumbnailReferenceServiceAdd:
    def test_rejects_path_outside_home(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        outside = tmp_path / "outside" / "photo.png"
        outside.parent.mkdir()
        outside.write_bytes(b"fake png bytes")

        service = _service(tmp_path)
        with pytest.raises(AppError) as excinfo:
            service.add(str(outside), None)
        assert excinfo.value.code == "PATH_NOT_ALLOWED"

    def test_rejects_non_image_extension(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        text_file = home / "notes.txt"
        text_file.write_text("not an image")

        service = _service(tmp_path)
        with pytest.raises(AppError) as excinfo:
            service.add(str(text_file), None)
        assert excinfo.value.code == "EXTENSION_NOT_ALLOWED"

    def test_rejects_oversized_file(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        big_file = home / "huge.png"
        big_file.write_bytes(b"0" * (9 * 1024 * 1024))  # 9 MB > 8 MB cap

        service = _service(tmp_path)
        with pytest.raises(AppError) as excinfo:
            service.add(str(big_file), None)
        assert excinfo.value.code == "FILE_TOO_LARGE"

    def test_rejects_missing_file(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)

        service = _service(tmp_path)
        with pytest.raises(AppError) as excinfo:
            service.add(str(home / "does-not-exist.png"), None)
        assert excinfo.value.code == "FILE_NOT_FOUND"

    def test_succeeds_and_response_never_contains_raw_path(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        photo = home / "riley.png"
        photo.write_bytes(b"fake png bytes")

        service = _service(tmp_path)
        result = service.add(str(photo), "Riley headshot")

        assert set(result.keys()) == {"id", "label", "preview_data_url"}
        assert result["id"].startswith("ref_")
        assert result["label"] == "Riley headshot"
        assert result["preview_data_url"].startswith("data:image/png;base64,")
        # The raw filesystem path must never leak into the caller-facing result.
        assert str(photo) not in str(result)


# ---------------------------------------------------------------------------
# Service-level: resolve (opaque id -> path)
# ---------------------------------------------------------------------------


class TestThumbnailReferenceServiceResolve:
    def test_resolve_returns_none_for_unknown_id(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)

        service = _service(tmp_path)
        assert service.resolve("ref_does_not_exist") is None

    def test_resolve_returns_path_for_registered_reference(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        photo = home / "riley.png"
        photo.write_bytes(b"fake png bytes")

        service = _service(tmp_path)
        added = service.add(str(photo), None)

        resolved = service.resolve(added["id"])
        assert resolved == photo.resolve()

    def test_resolve_returns_none_if_file_deleted_since_registration(self, tmp_path, monkeypatch) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)
        photo = home / "riley.png"
        photo.write_bytes(b"fake png bytes")

        service = _service(tmp_path)
        added = service.add(str(photo), None)
        photo.unlink()

        assert service.resolve(added["id"]) is None


# ---------------------------------------------------------------------------
# API-level
# ---------------------------------------------------------------------------


def test_api_add_then_resolve_round_trip(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    photo = home / "riley.png"
    photo.write_bytes(b"fake png bytes")

    client = _client(tmp_path, monkeypatch)

    created = client.post("/thumbnail-references", json={"path": str(photo), "label": "Riley"})
    assert created.status_code == 200
    body = created.json()
    assert set(body.keys()) == {"id", "label", "preview_data_url"}

    resolved = client.get(f"/thumbnail-references/{body['id']}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["canonical_path"] == str(photo.resolve())


def test_api_add_rejects_path_traversal(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"fake png bytes")

    client = _client(tmp_path, monkeypatch)
    response = client.post("/thumbnail-references", json={"path": str(outside)})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PATH_NOT_ALLOWED"


def test_api_resolve_unknown_id_returns_404(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)

    client = _client(tmp_path, monkeypatch)
    response = client.get("/thumbnail-references/ref_nope/resolve")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "THUMBNAIL_REFERENCE_NOT_FOUND"
