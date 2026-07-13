"""Tests for the filesystem_search tool (agent_reports/2026-07-13_
filesystem-search-tool.md) — folder/file discovery that replaces blind
Explorer clicking. _search_roots is monkeypatched to a single tmp_path so
tests never touch the real home directory or drives (fast, deterministic).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        "app.tools.system.filesystem_search._search_roots",
        lambda data_dir: [tmp_path],
    )
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def test_filesystem_search_finds_matching_folder(client: TestClient, tmp_path) -> None:
    (tmp_path / "thumbnails").mkdir()
    (tmp_path / "unrelated").mkdir()
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "thumb"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    names = [r["name"] for r in body["result"]["results"]]
    assert names == ["thumbnails"]
    assert body["result"]["truncated"] is False


def test_filesystem_search_finds_matching_file(client: TestClient, tmp_path) -> None:
    (tmp_path / "notes.txt").write_text("hi")
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "notes", "type": "file"}},
    )
    body = response.json()["result"]
    assert [r["name"] for r in body["results"]] == ["notes.txt"]


def test_filesystem_search_requires_query(client: TestClient) -> None:
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": ""}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "INVALID_ARGUMENTS"


def test_filesystem_search_caps_results_and_marks_truncated(client: TestClient, tmp_path) -> None:
    for i in range(45):
        (tmp_path / f"findme-{i}").mkdir()
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "findme"}},
    )
    body = response.json()["result"]
    assert len(body["results"]) == 40
    assert body["truncated"] is True


def test_filesystem_search_is_case_insensitive(client: TestClient, tmp_path) -> None:
    (tmp_path / "ThumbNails").mkdir()
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "THUMBnails"}},
    )
    body = response.json()["result"]
    assert [r["name"] for r in body["results"]] == ["ThumbNails"]


def test_filesystem_search_defaults_to_any_type(client: TestClient, tmp_path) -> None:
    # Real-world regression (agent_reports/2026-07-13_filesystem-search-tool.md
    # "Revision 2"): this app's actual thumbnails are loose files directly in
    # data_dir (thumbnail-<id>.png), not inside a "thumbnails" subfolder — a
    # folder-only default would report zero matches for exactly the request
    # that motivated this tool.
    (tmp_path / "thumbnail-abc123.png").write_text("x")
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "thumbnail"}},
    )
    body = response.json()["result"]
    assert [r["name"] for r in body["results"]] == ["thumbnail-abc123.png"]


def test_filesystem_search_falls_back_to_singular_on_no_match(client: TestClient, tmp_path) -> None:
    # A spoken "find the thumbnails folder" naturally produces query=
    # "thumbnails" (plural), but real files are named "thumbnail-<id>.png"
    # (no trailing "s") — the plural query alone must still find them.
    (tmp_path / "thumbnail-abc123.png").write_text("x")
    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "thumbnails"}},
    )
    body = response.json()["result"]
    assert [r["name"] for r in body["results"]] == ["thumbnail-abc123.png"]


def test_filesystem_search_finds_shallow_match_past_deep_decoy(client: TestClient, tmp_path, monkeypatch) -> None:
    # Regression test for the original bug (agent_reports/2026-07-13_
    # filesystem-search-tool.md "Revision" note): a depth-first walk could
    # exhaust the whole time budget descending into one huge/deep subtree
    # (e.g. AppData, alphabetically before Desktop) before ever reaching a
    # shallow match in a different branch. A very deep, alphabetically-first
    # decoy must not prevent a shallow match a few levels into a different
    # branch from being found, even under a tight time budget — BFS finds it
    # in a handful of scandir calls regardless of how deep the decoy goes.
    monkeypatch.setattr("app.tools.system.filesystem_search.MAX_SECONDS", 0.05)
    decoy = tmp_path / "aaaa_decoy"
    for i in range(500):
        decoy = decoy / f"level{i}"
    decoy.mkdir(parents=True)
    (tmp_path / "zzzz_home_like" / "desktop_analog" / "target_folder").mkdir(parents=True)

    response = client.post(
        "/tools/execute",
        json={"tool_name": "filesystem_search", "arguments": {"query": "target_folder"}},
    )
    body = response.json()["result"]
    names = [r["name"] for r in body["results"]]
    assert "target_folder" in names
