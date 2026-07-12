from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app
from app.storage.repositories.screenshot_repo import ScreenshotRepository


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def test_list_screenshots_empty(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.get("/screenshots")
    assert response.status_code == 200
    assert response.json() == {"screenshots": []}


def test_list_screenshots_returns_recorded_rows(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    repo = ScreenshotRepository(client.app.state.settings.database_path)
    repo.record(str(tmp_path / "shot1.png"))
    repo.record(str(tmp_path / "shot2.png"))

    response = client.get("/screenshots")
    body = response.json()["screenshots"]
    assert len(body) == 2
    # Newest first.
    assert body[0]["filePath"] == str(tmp_path / "shot2.png")
    assert all(row["sentToModel"] is False for row in body)


def test_delete_all_removes_rows_and_files(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    repo = ScreenshotRepository(client.app.state.settings.database_path)
    real_file = tmp_path / "shot.png"
    real_file.write_bytes(b"fake png bytes")
    repo.record(str(real_file))

    response = client.delete("/screenshots")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "deletedCount": 1}
    assert not real_file.exists()

    follow_up = client.get("/screenshots")
    assert follow_up.json() == {"screenshots": []}


def test_delete_all_survives_already_missing_file(tmp_path, monkeypatch) -> None:
    # A row whose file was already deleted out-of-band shouldn't crash delete-all.
    client = _client(tmp_path, monkeypatch)
    repo = ScreenshotRepository(client.app.state.settings.database_path)
    repo.record(str(tmp_path / "never-actually-written.png"))

    response = client.delete("/screenshots")
    assert response.status_code == 200
    assert response.json()["deletedCount"] == 1


def test_cleanup_expired_deletes_old_rows_and_files_on_list(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    repo = ScreenshotRepository(client.app.state.settings.database_path)

    old_file = tmp_path / "old.png"
    old_file.write_bytes(b"old")
    recent_file = tmp_path / "recent.png"
    recent_file.write_bytes(b"recent")

    # Insert directly with a backdated timestamp — repo.record() always uses "now".
    old_cutoff = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    from app.storage.db import connect

    with connect(client.app.state.settings.database_path) as connection:
        connection.execute(
            "INSERT INTO screenshots (id, file_path, created_at, sent_to_model) VALUES (?, ?, ?, 0)",
            ("shot_old", str(old_file), old_cutoff),
        )
        connection.commit()
    repo.record(str(recent_file))

    response = client.get("/screenshots")
    body = response.json()["screenshots"]

    assert len(body) == 1
    assert body[0]["filePath"] == str(recent_file)
    assert not old_file.exists()  # 30-day default retention — 40 days old is expired
    assert recent_file.exists()


def test_screen_snapshot_tool_records_a_row(tmp_path, monkeypatch) -> None:
    """End-to-end: the actual screen_snapshot tool handler persists a row,
    not just the ephemeral inline artifact in its own response."""
    client = _client(tmp_path, monkeypatch)

    from unittest.mock import MagicMock, patch

    fake_image = MagicMock()
    fake_image.width = 100
    fake_image.height = 100
    with patch("PIL.ImageGrab.grab", return_value=fake_image), patch(
        "PIL.ImageGrab.grab_all_monitors", return_value=None, create=True
    ):
        response = client.post(
            "/tools/execute",
            json={"tool_name": "screen_snapshot", "arguments": {}, "context": {"computer_mode": True}},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    listing = client.get("/screenshots").json()["screenshots"]
    assert len(listing) == 1
