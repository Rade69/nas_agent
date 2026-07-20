"""Thumbnail board service (QM-6T1, docs/PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md).

Manages the thumbnail board lifecycle — loading placeholders, generate, edit,
select, grid pagination, and artifact construction. Migrated from Electron
legacyMedia.cjs thumbnail board functions into the Python backend.

Key invariants:
- `number` is permanent and never renumbered.
- `selected_id` always points to an existing ready image or is null.
- Loading placeholders are cleaned up on startup.
- Edit creates a new record with `parent_id`, never overwrites the original.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.thumbnail_image_helper import (
    build_edit_thumbnail_prompt,
    build_thumbnail_prompt,
    save_thumbnail_image,
)
from app.storage.repositories.thumbnail_board_repo import ThumbnailBoardRepository


class ThumbnailBoardService:
    """High-level board operations that produce Realtime-compatible responses."""

    def __init__(
        self,
        repo: ThumbnailBoardRepository,
        image_client: Any | None = None,  # OpenAIImageClient, optional
        thumbnails_dir: Path | None = None,
    ) -> None:
        self._repo = repo
        self._image_client = image_client
        self._thumbnails_dir = thumbnails_dir

    # ------------------------------------------------------------------ #
    # Public API — each returns a dict usable as tool/API response
    # ------------------------------------------------------------------ #

    def loading_prepare(self, *, prompt: str, mode: str = "generate",
                        number: int | None = None,
                        target_id: str | None = None) -> dict[str, Any]:
        """Create a loading placeholder and return board state."""
        max_num = self._repo.get_max_number()
        next_number = max_num + 1

        # Determine if this is an edit (needs a target)
        target = None
        actual_mode = mode
        if actual_mode == "edit":
            target = self._resolve_target(number, target_id)
            if target is None:
                # No target — treat as generate instead
                actual_mode = "generate"

        image_type = "edited" if actual_mode == "edit" else "generated"
        parent_id = target["id"] if target else None

        now = self._repo.create_image(
            number=next_number,
            type_=image_type,
            status="loading",
            path=None,
            prompt=prompt,
            size="1536x1024",
            parent_id=parent_id,
            run_id=None,
        )

        board_state = self._repo.get_or_create_board_state()
        if board_state["view"] != "selected" or not board_state["selected_id"]:
            self._repo.update_board_state(selected_id=None, view="grid", page=1)

        return self._response(grid_view=True)

    def generate(
        self,
        *,
        prompt: str,
        run_id: str | None = None,
        references: list[str] | None = None,
        fake_path: str | None = None,
        fake_data_url: str | None = None,
    ) -> dict[str, Any]:
        """Record a generated thumbnail (ready status).

        If fake_path is provided (testing), uses it directly. Otherwise uses
        the image client to generate a real thumbnail.
        """
        if fake_path is not None:
            return self._generate_from_path(prompt, fake_path, run_id)

        if self._image_client is not None and self._image_client.available:
            return self._generate_via_api(prompt, references or [], run_id)

        return {
            "ok": False,
            "error": "Image client is not available. Configure OPENAI_API_KEY to generate thumbnails.",
            "board": self._summary(),
            "artifact": self._error_artifact(
                "Image client is not available. Configure OPENAI_API_KEY to generate thumbnails."
            ),
        }

    def edit(
        self,
        *,
        prompt: str,
        number: int | None = None,
        target_id: str | None = None,
        run_id: str | None = None,
        references: list[str] | None = None,
        fake_path: str | None = None,
        fake_data_url: str | None = None,
    ) -> dict[str, Any]:
        """Create an edited thumbnail as a new record with parent_id.

        Edit never overwrites the original — it creates a new record
        referencing the original via parent_id.
        """
        target = self._resolve_target(number, target_id)
        if target is None:
            return {
                "ok": False,
                "error": "No thumbnail is selected. Generate a thumbnail first or specify a number.",
                "board": self._summary(),
                "artifact": self._error_artifact(
                    "No thumbnail is selected. Generate a thumbnail first or specify a number."
                ),
            }

        if fake_path is not None:
            return self._edit_from_path(prompt, target, fake_path, run_id)

        if self._image_client is not None and self._image_client.available:
            return self._edit_via_api(prompt, target, references or [], run_id)

        return {
            "ok": False,
            "error": "Image client is not available. Configure OPENAI_API_KEY to edit thumbnails.",
            "board": self._summary(),
            "artifact": self._error_artifact(
                "Image client is not available. Configure OPENAI_API_KEY to edit thumbnails."
            ),
        }

    def select(self, *, number: int) -> dict[str, Any]:
        """Select a thumbnail by permanent number and show fullscreen."""
        image = self._repo.get_image_by_number(number)
        if image is None:
            return {
                "ok": False,
                "error": f"Thumbnail number {number} does not exist yet.",
                "board": self._summary(),
                "artifact": self._error_artifact(
                    f"Thumbnail number {number} does not exist yet."
                ),
            }
        if image["status"] == "loading":
            return {
                "ok": False,
                "error": f"Thumbnail number {number} is still generating.",
                "board": self._summary(),
                "artifact": self._error_artifact(
                    f"Thumbnail number {number} is still generating."
                ),
            }

        self._repo.update_board_state(selected_id=image["id"], view="selected")

        return {
            "ok": True,
            "selected": self._image_to_dict(image),
            "selected_number": number,
            "board": self._summary(),
            "artifact": self._build_artifact(view="selected"),
            "message": f"Selected thumbnail {number}.",
        }

    def grid(self, *, page: int = 1) -> dict[str, Any]:
        """Show a paginated page of the thumbnail board."""
        p = max(1, page)
        self._repo.update_board_state(view="grid", page=p)

        return {
            "ok": True,
            "board": self._summary(),
            "artifact": self._build_artifact(view="grid"),
        }

    def summary(self) -> dict[str, Any]:
        """Compact board state summary (no artifact)."""
        return self._summary()

    def clear_startup_loading(self) -> None:
        """Delete any leftover loading placeholders from a previous session."""
        self._repo.delete_loading_images()

    def get_instructions(self) -> str:
        """Build Markdown instructions for the Realtime prompt (parity with
        legacyMedia.cjs buildThumbnailBoardInstructions)."""
        summary = self._summary()
        images = summary["images"]
        if images:
            image_lines = "\n".join(
                f"- #{img['number']}: {img['status']}"
                f"{' ' + img['type'] if img['status'] == 'ready' else ''}"
                f"{', prompt: ' + img['prompt'][:120] if img.get('prompt') else ''}"
                for img in images
            )
        else:
            image_lines = "- No generated thumbnails yet."

        meta = summary["page"]
        return (
            f"# Current Thumbnail Board State\n"
            f"Reference images loaded: {summary['references']}\n"
            f"Current view: {summary['view']}\n"
            f"Selected thumbnail number: {summary.get('selected_number') or 'none'}\n"
            f"Current page: {meta['page']}/{meta['total_pages']}\n"
            f"Total thumbnails: {meta['total_images']}\n"
            f"Next new thumbnail number: {meta['next_number']}\n"
            f"Visible permanent thumbnail numbers:\n"
            f"{image_lines}\n\n"
            f"When Riley says \"pull up number N\", \"select N\", or \"show N\", call "
            f"thumbnail_select with that permanent number. When Riley says \"edit this\", "
            f"use thumbnail_edit with no number if a selected thumbnail number exists. "
            f"When Riley says \"edit number N\", call thumbnail_edit with that permanent "
            f"number. When he asks for older thumbnails or another page, call thumbnail_grid "
            f"with the requested page. Do not claim you cannot see prior thumbnails; this "
            f"board state is persistent and paginated."
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _resolve_target(self, number: int | None,
                        target_id: str | None) -> dict[str, Any] | None:
        """Resolve a thumbnail target by number, id, or selected."""
        if target_id:
            row = self._repo.get_image(target_id)
        elif number:
            row = self._repo.get_image_by_number(number)
        else:
            board_state = self._repo.get_or_create_board_state()
            selected_id = board_state["selected_id"]
            if not selected_id:
                return None
            row = self._repo.get_image(selected_id)

        if row is None:
            return None
        if row["status"] == "loading":
            return None
        return dict(row)

    def _summary(self) -> dict[str, Any]:
        """Build a compact summary (same shape as legacyMedia.cjs thumbnailBoardSummary)."""
        board_state = self._repo.get_or_create_board_state()
        total_images = self._repo.count_images()
        max_num = self._repo.get_max_number()
        page_size = board_state["page_size"] or 9
        page = board_state["page"] or 1
        total_pages = max(1, (total_images + page_size - 1) // page_size)

        selected_number = None
        if board_state["selected_id"]:
            selected = self._repo.get_image(board_state["selected_id"])
            if selected:
                selected_number = selected["number"]

        visible = self._repo.list_images(page=page, page_size=page_size)
        images = [
            {
                "number": img["number"],
                "id": img["id"],
                "status": "ready" if img["status"] != "loading" else "loading",
                "type": img["type"],
                "prompt": img["prompt"] or "",
            }
            for img in visible
        ]

        return {
            "view": board_state["view"],
            "selected_number": selected_number,
            "references": 0,  # References count; QM-6T4/T5 will wire real count
            "page": {
                "page": page,
                "page_size": page_size,
                "total_images": total_images,
                "total_pages": total_pages,
                "next_number": max_num + 1,
            },
            "images": images,
        }

    def _build_artifact(self, view: str = "grid") -> dict[str, Any]:
        """Build a thumbnailBoard artifact (same shape as legacyMedia.cjs
        thumbnailBoardArtifact). Compatible with ArtifactPanel.tsx."""
        board_state = self._repo.get_or_create_board_state()
        page = board_state["page"] or 1
        page_size = board_state["page_size"] or 9

        selected = None
        if board_state["selected_id"]:
            selected = self._repo.get_image(board_state["selected_id"])

        visible_images = []
        if view == "selected" and selected:
            visible_images = [dict(selected)]
        else:
            rows = self._repo.list_images(page=page, page_size=page_size)
            visible_images = [dict(r) for r in rows]

        total_images = self._repo.count_images()
        max_num = self._repo.get_max_number()
        total_pages = max(1, (total_images + page_size - 1) // page_size)

        images_json = []
        for img in visible_images:
            image_entry = {
                "id": img["id"],
                "number": img["number"],
                "src": None,  # QM-6T2 will populate with data URL or path
                "path": img.get("path"),
                "prompt": img.get("prompt") or "",
                "type": img.get("type") or "thumbnail",
                "status": img.get("status") or "ready",
                "selected": selected is not None and img["id"] == selected["id"],
            }
            images_json.append(image_entry)

        board_summary = self._summary()
        view_title = f"Thumbnail {selected['number']}" if view == "selected" and selected else "Thumbnail Board"

        artifact_content = json.dumps({
            "view": view,
            "selectedId": board_state["selected_id"],
            "references": [],
            "page": {
                "page": page,
                "page_size": page_size,
                "total_images": total_images,
                "total_pages": total_pages,
                "next_number": max_num + 1,
            },
            "images": images_json,
        })

        return {
            "title": view_title,
            "kind": "thumbnailBoard",
            "fullscreen": view == "selected",
            "content": artifact_content,
        }

    def _response(self, grid_view: bool = True) -> dict[str, Any]:
        """Build a standard tool/API response with board summary + artifact."""
        return {
            "ok": True,
            "board": self._summary(),
            "artifact": self._build_artifact(view="grid" if grid_view else "selected"),
            "silent": True,
        }

    def _error_artifact(self, error_text: str) -> dict[str, Any]:
        return {
            "title": "Thumbnail Board",
            "kind": "thumbnailBoard",
            "fullscreen": False,
            "content": json.dumps({
                "view": "grid",
                "selectedId": None,
                "references": [],
                "page": {},
                "images": [],
                "error": error_text,
            }),
        }

    @staticmethod
    def _image_to_dict(row: Any) -> dict[str, Any]:
        raw = dict(row)
        return {
            "id": raw["id"],
            "number": raw["number"],
            "type": raw["type"],
            "status": "ready" if raw["status"] != "loading" else "loading",
            "prompt": raw.get("prompt", ""),
            "path": raw.get("path"),
        }

    # ------------------------------------------------------------------ #
    # Image generation helpers (QM-6T2: real API calls vs testing)
    # ------------------------------------------------------------------ #

    def _generate_from_path(self, prompt: str, path: str,
                            run_id: str | None) -> dict[str, Any]:
        """Record a generated thumbnail from an existing file path (testing)."""
        max_num = self._repo.get_max_number()
        next_number = max_num + 1
        self._repo.create_image(
            number=next_number, type_="generated", status="ready",
            path=path, prompt=prompt, size="1536x1024",
            parent_id=None, run_id=run_id,
        )
        self._reset_view_to_grid()
        result = self._response(grid_view=True)
        result["thumbnail_ready"] = True
        result["silent"] = True
        return result

    def _generate_via_api(self, prompt: str, references: list[str],
                          run_id: str | None) -> dict[str, Any]:
        """Generate a thumbnail via OpenAI API."""
        has_refs = len(references) > 0
        api_prompt = build_thumbnail_prompt(prompt, has_references=has_refs)

        input_paths = references[:4]
        try:
            if input_paths:
                result = self._image_client.edit_with_inputs(
                    prompt=api_prompt, input_paths=input_paths, size="1536x1024",
                )
            else:
                result = self._image_client.generate(
                    prompt=api_prompt, size="1536x1024",
                )
        except Exception as exc:
            if run_id:
                self._repo.delete_images_by_run_id(run_id)
            return {
                "ok": False,
                "error": f"Thumbnail generation failed: {exc}",
                "board": self._summary(),
                "artifact": self._error_artifact(f"Thumbnail generation failed: {exc}"),
            }

        b64 = result.get("b64_json")
        if not b64:
            if run_id:
                self._repo.delete_images_by_run_id(run_id)
            return {
                "ok": False,
                "error": "Image response did not include image data.",
                "board": self._summary(),
                "artifact": self._error_artifact("Image response did not include image data."),
            }

        saved = save_thumbnail_image(b64, self._thumbnails_dir)
        max_num = self._repo.get_max_number()
        next_number = max_num + 1
        self._repo.create_image(
            number=next_number, type_="generated", status="ready",
            path=saved["path"], prompt=prompt, size="1536x1024",
            parent_id=None, run_id=run_id,
        )
        self._reset_view_to_grid()
        result = self._response(grid_view=True)
        result["thumbnail_ready"] = True
        result["silent"] = True
        return result

    def _edit_from_path(self, prompt: str, target: dict[str, Any],
                        path: str, run_id: str | None) -> dict[str, Any]:
        """Record an edited thumbnail from an existing file path (testing)."""
        max_num = self._repo.get_max_number()
        next_number = max_num + 1
        self._repo.create_image(
            number=next_number, type_="edited", status="ready",
            path=path, prompt=prompt, size="1536x1024",
            parent_id=target["id"], run_id=run_id,
        )
        self._reset_view_to_grid()
        result = self._response(grid_view=True)
        result["thumbnail_ready"] = True
        result["silent"] = True
        return result

    def _edit_via_api(self, prompt: str, target: dict[str, Any],
                      references: list[str], run_id: str | None) -> dict[str, Any]:
        """Edit a thumbnail via OpenAI API."""
        api_prompt = build_edit_thumbnail_prompt(prompt, target.get("prompt") or "")

        input_paths = [target["path"]] if target.get("path") else []
        input_paths.extend(references[:3])
        input_paths = [p for p in input_paths if p]

        if not input_paths:
            return {
                "ok": False,
                "error": "Target thumbnail has no file path to edit.",
                "board": self._summary(),
                "artifact": self._error_artifact("Target thumbnail has no file path to edit."),
            }

        try:
            result = self._image_client.edit_with_inputs(
                prompt=api_prompt, input_paths=input_paths, size="1536x1024",
            )
        except Exception as exc:
            if run_id:
                self._repo.delete_images_by_run_id(run_id)
            return {
                "ok": False,
                "error": f"Thumbnail edit failed: {exc}",
                "board": self._summary(),
                "artifact": self._error_artifact(f"Thumbnail edit failed: {exc}"),
            }

        b64 = result.get("b64_json")
        if not b64:
            if run_id:
                self._repo.delete_images_by_run_id(run_id)
            return {
                "ok": False,
                "error": "Image edit response did not include image data.",
                "board": self._summary(),
                "artifact": self._error_artifact("Image edit response did not include image data."),
            }

        saved = save_thumbnail_image(b64, self._thumbnails_dir)
        max_num = self._repo.get_max_number()
        next_number = max_num + 1
        self._repo.create_image(
            number=next_number, type_="edited", status="ready",
            path=saved["path"], prompt=prompt, size="1536x1024",
            parent_id=target["id"], run_id=run_id,
        )
        self._reset_view_to_grid()
        result = self._response(grid_view=True)
        result["thumbnail_ready"] = True
        result["silent"] = True
        return result

    def _reset_view_to_grid(self) -> None:
        """Ensure board view is reset to grid after generate/edit."""
        board_state = self._repo.get_or_create_board_state()
        if board_state["view"] != "selected" or not board_state["selected_id"]:
            self._repo.update_board_state(selected_id=None, view="grid", page=1)
