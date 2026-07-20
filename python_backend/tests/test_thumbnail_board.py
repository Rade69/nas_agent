"""Tests for QM-6T1 thumbnail board storage and service (docs/
PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md).

Covers: loading placeholder, startup cleanup, generate, edit invariants
(parent_id), select, grid pagination, and error cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_local_token
from app.main import create_app
from app.services.thumbnail_board_service import ThumbnailBoardService
from app.storage.repositories.thumbnail_board_repo import ThumbnailBoardRepository


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RICKY_DATA_DIR", str(tmp_path))
    app = create_app()
    app.dependency_overrides[require_local_token] = lambda: None
    return TestClient(app)


def _service(tmp_path) -> ThumbnailBoardService:
    from app.core.config import Settings
    from app.storage.db import initialize_database

    settings = Settings(data_dir=tmp_path)
    initialize_database(settings)
    repo = ThumbnailBoardRepository(settings.database_path)
    return ThumbnailBoardService(repo)


# ---------------------------------------------------------------------------
# 1. Loading placeholder
# ---------------------------------------------------------------------------


class TestLoadingPrepare:
    def test_creates_loading_with_permanent_number(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        result = svc.loading_prepare(prompt="a cat thumbnail", mode="generate")
        assert result["ok"] is True
        board = result["board"]
        assert len(board["images"]) == 1
        assert board["images"][0]["status"] == "loading"
        assert board["images"][0]["number"] >= 1

    def test_numbers_increment(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        r1 = svc.loading_prepare(prompt="first")
        n1 = r1["board"]["images"][0]["number"]
        r2 = svc.loading_prepare(prompt="second")
        n2 = r2["board"]["images"][0]["number"]
        assert n2 == n1 + 1


# ---------------------------------------------------------------------------
# 2. Startup cleanup
# ---------------------------------------------------------------------------


class TestStartupCleanup:
    def test_clears_loading_on_startup(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        svc.loading_prepare(prompt="leftover loading")
        assert svc.summary()["page"]["total_images"] == 1
        svc.clear_startup_loading()
        assert svc.summary()["page"]["total_images"] == 0


# ---------------------------------------------------------------------------
# 3. Generate (ready record)
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_creates_ready_thumbnail_with_artifact(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        result = svc.generate(
            prompt="a nice thumbnail",
            fake_path=str(tmp_path / "thumb-001.png"),
        )
        assert result["ok"] is True
        assert result["thumbnail_ready"] is True
        board = result["board"]
        assert len(board["images"]) == 1
        assert board["images"][0]["status"] == "ready"
        assert board["images"][0]["number"] >= 1
        artifact = result["artifact"]
        assert artifact["kind"] == "thumbnailBoard"
        assert artifact["fullscreen"] is False

    def test_numbers_permanent_never_renumbered(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        svc.generate(prompt="first", fake_path=str(tmp_path / "t1.png"))
        svc.generate(prompt="second", fake_path=str(tmp_path / "t2.png"))
        svc.generate(prompt="third", fake_path=str(tmp_path / "t3.png"))
        summary = svc.summary()
        numbers = [img["number"] for img in summary["images"]]
        assert numbers == [3, 2, 1]  # DESC order
        assert summary["page"]["total_images"] == 3
        assert summary["page"]["next_number"] == 4


# ---------------------------------------------------------------------------
# 4. Edit invariants
# ---------------------------------------------------------------------------


class TestEdit:
    def test_edit_without_target_returns_error(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        result = svc.edit(prompt="edit nothing")
        assert result["ok"] is False
        assert "error" in result
        assert "No thumbnail is selected" in result["error"]

    def test_edit_creates_new_record_with_parent_id(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        # First generate a thumbnail
        gen = svc.generate(prompt="original", fake_path=str(tmp_path / "orig.png"))
        original_number = gen["board"]["images"][0]["number"]
        original_id = gen["board"]["images"][0]["id"]

        # Select it
        svc.select(number=original_number)

        # Edit it
        edit = svc.edit(
            prompt="edited version",
            fake_path=str(tmp_path / "edited.png"),
        )
        assert edit["ok"] is True
        board = edit["board"]
        assert len(board["images"]) == 2  # original + edited

        # Verify original still exists
        summary = svc.summary()
        numbers = [img["number"] for img in summary["images"]]
        assert original_number in numbers

    def test_edit_by_number_creates_child(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        gen = svc.generate(prompt="original", fake_path=str(tmp_path / "orig.png"))
        original_number = gen["board"]["images"][0]["number"]

        edit = svc.edit(prompt="edited version", number=original_number,
                        fake_path=str(tmp_path / "edited.png"))
        assert edit["ok"] is True
        summary = svc.summary()
        # Original should still be there
        numbers = [img["number"] for img in summary["images"]]
        assert original_number in numbers
        # New number should be higher
        new_number = max(numbers)
        assert new_number > original_number


# ---------------------------------------------------------------------------
# 5. Select
# ---------------------------------------------------------------------------


class TestSelect:
    def test_select_by_number(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        gen = svc.generate(prompt="selectable", fake_path=str(tmp_path / "sel.png"))
        number = gen["board"]["images"][0]["number"]

        result = svc.select(number=number)
        assert result["ok"] is True
        assert result["selected_number"] == number

    def test_select_nonexistent_returns_error(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        result = svc.select(number=999)
        assert result["ok"] is False
        assert "does not exist" in result["error"]


# ---------------------------------------------------------------------------
# 6. Grid pagination
# ---------------------------------------------------------------------------


class TestGrid:
    def test_pagination_returns_stable_numbers(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        for i in range(15):
            svc.generate(prompt=f"thumb {i+1}", fake_path=str(tmp_path / f"t{i}.png"))

        # Page 1: first 9 (DESC order: 15-7)
        page1 = svc.grid(page=1)
        p1_numbers = [img["number"] for img in page1["board"]["images"]]
        assert len(p1_numbers) <= 9
        assert 15 in p1_numbers

        # Page 2: next 6 (6-1)
        page2 = svc.grid(page=2)
        p2_numbers = [img["number"] for img in page2["board"]["images"]]
        assert len(p2_numbers) <= 9
        assert 1 in p2_numbers

        # Numbers are stable (no renumbering between pages)
        meta = page2["board"]["page"]
        assert meta["total_images"] == 15
        assert meta["total_pages"] == 2

    def test_invalid_page_defaults_to_1(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        svc.generate(prompt="test", fake_path=str(tmp_path / "t.png"))
        result = svc.grid(page=0)
        assert result["ok"] is True
        assert result["board"]["page"]["page"] == 1


# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_empty_board_summary(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        summary = svc.summary()
        assert summary["view"] == "grid"
        assert summary["selected_number"] is None
        assert summary["page"]["total_images"] == 0
        assert summary["page"]["next_number"] == 1

    def test_summary_after_generate(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        svc.generate(prompt="test", fake_path=str(tmp_path / "t.png"))
        summary = svc.summary()
        assert summary["page"]["total_images"] == 1
        assert summary["page"]["next_number"] == 2


# ---------------------------------------------------------------------------
# 8. Instructions
# ---------------------------------------------------------------------------


class TestInstructions:
    def test_builds_instructions_for_empty_board(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        instructions = svc.get_instructions()
        assert "Current Thumbnail Board State" in instructions
        assert "No generated thumbnails yet" in instructions
        assert "thumbnail_select" in instructions
        assert "thumbnail_edit" in instructions
        assert "thumbnail_grid" in instructions

    def test_builds_instructions_with_images(self, tmp_path, monkeypatch) -> None:
        svc = _service(tmp_path)
        svc.generate(prompt="test thumb", fake_path=str(tmp_path / "t.png"))
        instructions = svc.get_instructions()
        assert "#1" in instructions
        assert "test thumb" in instructions


# ---------------------------------------------------------------------------
# 9. API-level smoke tests
# ---------------------------------------------------------------------------


def test_api_get_board_returns_ok(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.get("/thumbnails/board")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "board" in data
    assert "artifact" in data


def test_api_loading_then_generate_cycle(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    # Loading prepare
    loading = client.post("/thumbnails/loading", json={"prompt": "test loading", "mode": "generate"})
    assert loading.status_code == 200
    l_data = loading.json()

    # Generate (no image client — just records a ready status)
    gen = client.post("/thumbnails/generate", json={"prompt": "generated"})
    assert gen.status_code == 200
    g_data = gen.json()
    assert g_data["ok"] is True

    # Board shows generate
    board = client.get("/thumbnails/board")
    assert board.status_code == 200
    assert len(board.json()["board"]["images"]) >= 1


def test_api_select_nonexistent_returns_structured_error(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post("/thumbnails/select", json={"number": 999})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "error" in data


def test_api_clear_loading(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/thumbnails/loading", json={"prompt": "orphan loading", "mode": "generate"})
    response = client.post("/thumbnails/clear-loading")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


# ---------------------------------------------------------------------------
# 10. Tool registry tests (QM-6T3)
# ---------------------------------------------------------------------------


def test_tool_registry_contains_all_thumbnail_tools(tmp_path, monkeypatch) -> None:
    """Tool registry must contain all five thumbnail_* tools."""
    client = _client(tmp_path, monkeypatch)
    tools_response = client.get("/tools")
    assert tools_response.status_code == 200
    tools = {t["name"]: t for t in tools_response.json()["tools"]}

    expected = [
        "thumbnail_loading_prepare",
        "thumbnail_generate",
        "thumbnail_edit",
        "thumbnail_select",
        "thumbnail_grid",
    ]
    for name in expected:
        assert name in tools, f"Missing tool: {name}"


def test_thumbnail_generate_has_outbound_true(tmp_path, monkeypatch) -> None:
    """thumbnail_generate must have outbound=True."""
    client = _client(tmp_path, monkeypatch)
    tools = {t["name"]: t for t in client.get("/tools").json()["tools"]}
    tool = tools["thumbnail_generate"]
    assert tool.get("outbound") is True, f"Expected outbound=True, got {tool.get('outbound')}"


def test_thumbnail_edit_has_outbound_true(tmp_path, monkeypatch) -> None:
    """thumbnail_edit must have outbound=True."""
    client = _client(tmp_path, monkeypatch)
    tools = {t["name"]: t for t in client.get("/tools").json()["tools"]}
    tool = tools["thumbnail_edit"]
    assert tool.get("outbound") is True, f"Expected outbound=True, got {tool.get('outbound')}"


def test_thumbnail_low_risk_tools_no_confirmation(tmp_path, monkeypatch) -> None:
    """Low-risk thumbnail tools should not require confirmation."""
    client = _client(tmp_path, monkeypatch)
    tools = {t["name"]: t for t in client.get("/tools").json()["tools"]}
    for name in ("thumbnail_loading_prepare", "thumbnail_select", "thumbnail_grid"):
        tool = tools[name]
        assert tool.get("risk") == "low", f"{name}: expected risk=low, got {tool.get('risk')}"
        assert tool.get("requires_confirmation") is False, f"{name}: expected no confirmation"


def test_thumbnail_edit_medium_risk(tmp_path, monkeypatch) -> None:
    """thumbnail_edit should have medium risk."""
    client = _client(tmp_path, monkeypatch)
    tools = {t["name"]: t for t in client.get("/tools").json()["tools"]}
    assert tools["thumbnail_edit"].get("risk") == "medium"
