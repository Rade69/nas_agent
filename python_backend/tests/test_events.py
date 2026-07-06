"""Events endpoint edge-case tests (FAZA 18).

Pokriva `/events` endpoint za situacije koje regularni testovi ne pogađaju:
prazan response (bez događaja), cursor sa nepostojećim timestampom,
cursor sa budućim timestampom, limit validacija.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RICKY_LOCAL_TOKEN", raising=False)
    app = create_app()
    return TestClient(app)


def test_events_returns_backend_ready_on_fresh_start(client: TestClient) -> None:
    """Najmanje jedan event (backend.ready) mora postojati nakon create_app()."""
    response = client.get("/events")
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) >= 1
    assert any(e["type"] == "backend.ready" for e in body["events"])


def test_events_since_far_future_returns_empty(client: TestClient) -> None:
    """Cursor u dalekoj budućnosti vraća praznu listu."""
    far_future = "2099-12-31T00:00:00.000000+00:00"
    response = client.get(f"/events?since={far_future}")
    assert response.status_code == 200
    body = response.json()
    assert body["events"] == []
    assert body["next_cursor"] is None


def test_events_since_empty_returns_one_event(client: TestClient) -> None:
    """Cursor prazan string — treba da vrati najmanje jedan event (backend.ready)."""
    response = client.get("/events?since=")
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) >= 1


def test_events_bad_since_format_is_handled(client: TestClient) -> None:
    """Nevalidan timestamp — endpoint ne smije crash-ati sa 500."""
    response = client.get("/events?since=not-a-timestamp")
    assert response.status_code in (200, 422)


def test_events_pagination_with_cursor(client: TestClient) -> None:
    """Kreiraj artifact, dohvati sa cursor-om prije, zatim sa cursor-om poslije.
    Prvi poziv treba da sadrži artifact.created, drugi da bude prazan ili
    da ima konzistentne timestampove (isti milisekund je edge case)."""
    # Prvo dohvati početni cursor
    initial = client.get("/events").json()
    initial_cursor = initial["next_cursor"]
    assert initial_cursor is not None, "Prvi poziv mora vratiti cursor"

    # Kreiraj artifact
    client.post(
        "/tools/execute",
        json={
            "tool_name": "artifact_create",
            "arguments": {"title": "Pagination test", "kind": "text", "content": "x"},
        },
    )

    # Dohvati sa cursor-om od prvog poziva — treba bar artifact.created
    after = client.get(f"/events?since={initial_cursor}").json()
    assert len(after["events"]) >= 1
    assert any(e["type"] == "artifact.created" for e in after["events"])

    # Cursor napreduje
    after_cursor = after["next_cursor"]
    assert after_cursor is not None
    # Provjera: svi eventi imaju timestamp ≥ cursor (konzistentnost)
    for event in after["events"]:
        assert event["timestamp"] >= initial_cursor
