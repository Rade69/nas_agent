"""Thumbnail reference image validation and opaque-ID lookup (S-03, docs/
SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md).

Registration only ever happens from a path the user picked via Electron's
native file dialog (electron/ipc_handlers/thumbnails.cjs) — there is no tool
a model can call to supply a path here. This service's job is to validate
that picked path (app/core/path_sandbox.py) and hand back an opaque id;
Electron stores the id, never the raw path, in its own thumbnail board
state. Only resolve() — called by Electron itself, never exposed to the
model or renderer — ever turns an id back into a real filesystem path.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.core.path_sandbox import (
    ensure_file_size_allowed,
    ensure_image_extension_allowed,
    resolve_within_roots,
)
from app.storage.repositories.thumbnail_reference_repo import ThumbnailReferenceRepository

# Tighter than path_sandbox's general DEFAULT_MAX_FILE_SIZE_BYTES (25 MB) —
# add() base64-encodes the whole file into the API response as an immediate
# preview, and a reference photo has no legitimate reason to be large.
MAX_REFERENCE_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


class ThumbnailReferenceService:
    def __init__(self, repository: ThumbnailReferenceRepository) -> None:
        self._repository = repository

    def add(self, raw_path: str, label: str | None) -> dict[str, Any]:
        allowed_roots = [Path.home()]
        resolved = resolve_within_roots(raw_path, allowed_roots)
        ensure_image_extension_allowed(resolved)
        if not resolved.is_file():
            raise AppError("FILE_NOT_FOUND", f"File not found: {raw_path}", status_code=404)
        ensure_file_size_allowed(resolved, max_bytes=MAX_REFERENCE_IMAGE_BYTES)

        mime_type = _MIME_TYPES[resolved.suffix.lower()]
        data = resolved.read_bytes()
        size_bytes = len(data)
        preview_data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"

        row = self._repository.create(
            canonical_path=str(resolved),
            label=label or resolved.name,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        return {
            "id": row["id"],
            "label": row["label"],
            "preview_data_url": preview_data_url,
        }

    def resolve(self, reference_id: str) -> Path | None:
        """Turn an opaque id back into a real path — Electron-only caller.
        Re-validates on every call (not just at registration time) so a file
        moved, deleted, or relocated outside the allowed roots since
        registration can't be used, even though the id itself still exists.
        """
        row = self._repository.get(reference_id)
        if row is None:
            return None
        try:
            resolved = resolve_within_roots(row["canonical_path"], [Path.home()])
            ensure_image_extension_allowed(resolved)
        except AppError:
            return None
        if not resolved.is_file():
            return None
        return resolved

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {
                "id": row["id"],
                "label": row["label"],
                "created_at": row["created_at"],
            }
            for row in self._repository.list(limit=limit)
        ]
