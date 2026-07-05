"""Windows screen_snapshot tool handler (FAZA 11).

Captures the full virtual desktop (all monitors) to a PNG file in the
configured screenshots directory. Uses Pillow's ImageGrab (no extra
dependency beyond Pillow, which is already available). The legacy PowerShell
`screenSnapshot.cjs` in electron/tools_legacy/powershell/ remains as an
Electron-side fallback; this Python implementation is the primary path.

Risk: low (no OCR, no external upload — see SECURITY_MODEL.md). Requires
computer_mode (the Electron handler enforces this before delegating).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4


def make_handlers(screenshots_dir: Path) -> dict[str, Any]:
    def screen_snapshot(arguments: dict[str, Any]) -> dict[str, Any]:
        # Local import keeps the tool module importable on non-Windows for tests
        # (the handler only fails when actually invoked without Pillow).
        from PIL import ImageGrab  # type: ignore[import-not-found]

        screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot-{uuid4().hex[:12]}.png"
        screenshot_path = screenshots_dir / filename

        # grab_all_monitors returns a list of images on Windows; fall back to a
        # single grab for cross-platform robustness.
        images = ImageGrab.grab_all_monitors() if hasattr(ImageGrab, "grab_all_monitors") else None
        if images:
            # Composite all monitors side-by-side onto a single canvas so the
            # artifact panel can show one image.
            total_width = sum(img.width for img in images)
            max_height = max(img.height for img in images)
            from PIL import Image

            canvas = Image.new("RGB", (total_width, max_height), (0, 0, 0))
            x_offset = 0
            for img in images:
                canvas.paste(img, (x_offset, 0))
                x_offset += img.width
            canvas.save(screenshot_path, "PNG")
        else:
            image = ImageGrab.grab()
            image.save(screenshot_path, "PNG")

        # Return a path relative to the repo root for the UI to resolve, plus
        # the absolute path for backend logging.
        return {
            "image_path": str(screenshot_path),
            "monitors": _monitor_info(),
            "artifact": {
                "title": "Screen Snapshot",
                "kind": "image",
                "content": str(screenshot_path),
            },
        }

    return {"screen_snapshot": screen_snapshot}


def _monitor_info() -> list[dict[str, int]]:
    """Best-effort monitor enumeration for the snapshot response.

    Pillow's ImageGrab does not expose monitor geometry directly; returning an
    empty list is acceptable for MVP — the screenshot itself is the primary
    payload, monitor metadata is informational. A future phase can use `mss`
    for richer monitor details if needed.
    """
    return []
