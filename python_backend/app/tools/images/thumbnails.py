"""Thumbnail board tool handlers (QM-6T3, docs/PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md).

Registers five model-facing tools: thumbnail_loading_prepare, thumbnail_generate,
thumbnail_edit, thumbnail_select, thumbnail_grid.

Each handler delegates to ThumbnailBoardService and returns a Realtime-compatible
response shape:
    { ok, board, artifact, silent, thumbnailReady }
"""
from __future__ import annotations

from typing import Any

from app.services.thumbnail_board_service import ThumbnailBoardService


def make_handlers(board_service: ThumbnailBoardService) -> dict[str, Any]:
    """Create thumbnail tool handlers wired to the given board service."""

    def thumbnail_loading_prepare(arguments: dict[str, Any]) -> dict[str, Any]:
        prompt = str(arguments.get("prompt") or "")
        mode = str(arguments.get("mode") or "generate")
        number = arguments.get("number")
        target_id = arguments.get("target_id")
        result = board_service.loading_prepare(
            prompt=prompt, mode=mode,
            number=int(number) if number is not None else None,
            target_id=str(target_id) if target_id else None,
        )
        return _realtime_response(result)

    def thumbnail_generate(arguments: dict[str, Any]) -> dict[str, Any]:
        prompt = str(arguments.get("prompt") or "")
        if not prompt.strip():
            raise ValueError("thumbnail_generate requires a non-empty 'prompt' argument.")
        run_id = arguments.get("run_id")
        result = board_service.generate(
            prompt=prompt,
            run_id=str(run_id) if run_id else None,
        )
        return _realtime_response(result)

    def thumbnail_edit(arguments: dict[str, Any]) -> dict[str, Any]:
        prompt = str(arguments.get("prompt") or "")
        if not prompt.strip():
            raise ValueError("thumbnail_edit requires a non-empty 'prompt' argument.")
        number = arguments.get("number")
        run_id = arguments.get("run_id")
        result = board_service.edit(
            prompt=prompt,
            number=int(number) if number is not None else None,
            run_id=str(run_id) if run_id else None,
        )
        return _realtime_response(result)

    def thumbnail_select(arguments: dict[str, Any]) -> dict[str, Any]:
        number = arguments.get("number")
        if number is None:
            raise ValueError("thumbnail_select requires a 'number' argument.")
        result = board_service.select(number=int(number))
        return _realtime_response(result)

    def thumbnail_grid(arguments: dict[str, Any]) -> dict[str, Any]:
        page = arguments.get("page", 1)
        result = board_service.grid(page=int(page) if page else 1)
        return _realtime_response(result)

    return {
        "thumbnail_loading_prepare": thumbnail_loading_prepare,
        "thumbnail_generate": thumbnail_generate,
        "thumbnail_edit": thumbnail_edit,
        "thumbnail_select": thumbnail_select,
        "thumbnail_grid": thumbnail_grid,
    }


def _realtime_response(result: dict[str, Any]) -> dict[str, Any]:
    """Normalise a board service response to Realtime-compatible shape.

    The Electron Realtime tool execution expects:
      { ok, board, artifact, silent, thumbnailReady }
    where thumbnailReady is camelCase (not snake_case) because the
    renderer-side callback (src/lib/realtime.ts) reads `thumbnailReady`.
    """
    ok = result.get("ok", True)
    if not ok:
        return {
            "ok": False,
            "error": result.get("error", "Unknown error"),
            "board": result.get("board"),
            "artifact": result.get("artifact"),
        }

    return {
        "ok": True,
        "board": result.get("board"),
        "artifact": result.get("artifact"),
        "silent": result.get("silent", True),
        "thumbnailReady": result.get("thumbnail_ready", False),
    }
