"""Thumbnail image helpers — prompt builders and save logic (QM-6T2, docs/
PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md).

Ports from electron/tools_legacy/legacyMedia.cjs:
- thumbnailPrompt() -> build_thumbnail_prompt()
- editThumbnailPrompt() -> build_edit_thumbnail_prompt()
- saveImageResponse() -> save_thumbnail_image()
"""
from __future__ import annotations

import base64
import uuid
from pathlib import Path


def build_thumbnail_prompt(prompt: str, has_references: bool = False) -> str:
    """Build the prompt for thumbnail generation (parity with legacyMedia.cjs
    thumbnailPrompt())."""
    parts = [
        "Use the provided reference image(s) of Riley as the identity reference."
        if has_references else "",
        "Create one 16:9 YouTube thumbnail.",
        "Follow this request literally. Do not add extra concepts, fake UI, "
        "extra text, watermarks, or unrelated elements.",
        prompt,
    ]
    return "\n".join(p for p in parts if p)


def build_edit_thumbnail_prompt(prompt: str, original_prompt: str = "") -> str:
    """Build the prompt for thumbnail editing (parity with legacyMedia.cjs
    editThumbnailPrompt())."""
    parts = [
        "Edit the provided thumbnail image.",
        "Make only this change. Preserve everything else unless the request "
        "says otherwise.",
        prompt,
    ]
    return "\n".join(p for p in parts if p)


def save_thumbnail_image(b64_json: str, thumbnails_dir: Path) -> dict[str, str]:
    """Save a base64-encoded thumbnail image to the controlled data dir.

    Returns dict with:
        path: str — absolute path to the saved file
        data_url: str — data:image/png;base64,... for inline display

    Parity with legacyMedia.cjs saveImageResponse().
    """
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    image_path = thumbnails_dir / f"thumbnail-{uuid.uuid4().hex[:12]}.png"
    image_path.write_bytes(base64.b64decode(b64_json))
    return {
        "path": str(image_path),
        "data_url": f"data:image/png;base64,{b64_json}",
    }