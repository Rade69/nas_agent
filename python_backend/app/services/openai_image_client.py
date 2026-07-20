"""OpenAI image generation client (FAZA 16).

Thin HTTP wrapper around the OpenAI Images API (gpt-image). Migrated from the
Electron-side `generateImage()` function in electron/main.cjs so that AI/external
API calls live in the Python backend.

API key is read from settings.openai_api_key (env: OPENAI_API_KEY). It is never
logged. The backend already holds this key for the FAZA 6 realtime session flow;
this client reuses it for image generation.
"""
from __future__ import annotations

import pathlib
from typing import Any

import httpx

from app.core.errors import AppError

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGES_EDIT_URL = "https://api.openai.com/v1/images/edits"


class OpenAIImageClient:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def generate(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "medium",
        model: str = "gpt-image-2",
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise AppError(
                "MISSING_API_KEY",
                "OPENAI_API_KEY is not configured on the Python backend.",
                status_code=500,
            )
        try:
            response = httpx.post(
                OPENAI_IMAGES_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "quality": quality,
                },
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise AppError(
                "IMAGE_REQUEST_FAILED",
                f"Image generation request failed: {exc}",
                status_code=502,
            ) from exc

        if response.status_code >= 400:
            raise AppError(
                "IMAGE_REQUEST_FAILED",
                f"Image generation failed: {response.status_code} {response.text}",
                status_code=502,
            )

        data = response.json()
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list) or not items:
            raise AppError(
                "IMAGE_RESPONSE_INVALID",
                "Image response did not include image data.",
                status_code=502,
            )
        first = items[0]
        return {
            "b64_json": first.get("b64_json"),
            "url": first.get("url"),
        }

    def edit_with_inputs(
        self,
        *,
        prompt: str,
        input_paths: list[str],
        size: str = "1536x1024",
        quality: str = "medium",
        model: str = "gpt-image-2",
        timeout: float = 90.0,
    ) -> dict[str, Any]:
        """Edit an image using the OpenAI Images Edits API (multipart form).

        Mirrors the legacy editImageWithInputs() from electron/tools_legacy/
        legacyMedia.cjs: first tries with "image[]" (multiple images), falls
        back to "image" (single image) if that fails.

        input_paths are local filesystem paths — the caller is responsible
        for ensuring they are app-internal generated thumbnails or validated
        reference paths (never raw model-supplied paths).
        """
        if not self._api_key:
            raise AppError(
                "MISSING_API_KEY",
                "OPENAI_API_KEY is not configured on the Python backend.",
                status_code=500,
            )

        def _build_form(image_field: str) -> httpx._types.MultipartTypes:
            files = []
            for input_path in input_paths[:10]:
                p = pathlib.Path(input_path)
                if not p.is_file():
                    continue
                mime = _mime_for_path(p)
                files.append((image_field, (p.name, p.read_bytes(), mime)))
            return [
                ("model", (None, model)),
                ("prompt", (None, prompt)),
                ("size", (None, size)),
                ("quality", (None, quality)),
                *files,
            ]

        # Try with "image[]" first (supports multiple reference images).
        # On failure, fall back to "image" (single image field).
        first_error: str | None = None
        for field_name in ("image[]", "image"):
            try:
                response = httpx.post(
                    OPENAI_IMAGES_EDIT_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files=_build_form(field_name),
                    timeout=timeout,
                )
            except httpx.HTTPError as exc:
                if field_name == "image[]":
                    first_error = str(exc)
                    continue
                raise AppError(
                    "IMAGE_EDIT_REQUEST_FAILED",
                    f"Image edit request failed: {exc}",
                    status_code=502,
                ) from exc

            if response.status_code < 400:
                data = response.json()
                items = data.get("data") if isinstance(data, dict) else None
                if not isinstance(items, list) or not items:
                    raise AppError(
                        "IMAGE_RESPONSE_INVALID",
                        "Image edit response did not include image data.",
                        status_code=502,
                    )
                first = items[0]
                return {
                    "b64_json": first.get("b64_json"),
                    "url": first.get("url"),
                }

            if field_name == "image[]":
                first_error = response.text
            else:
                raise AppError(
                    "IMAGE_EDIT_FAILED",
                    f"Image edit failed: {response.status_code} {response.text}",
                    status_code=502,
                )

        # Should not reach here — at least one fallback should have succeeded
        # or raised. Defensive exception.
        raise AppError(
            "IMAGE_EDIT_FAILED",
            f"Image edit failed: {first_error or 'unknown error'}",
            status_code=502,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mime_for_path(image_path: pathlib.Path) -> str:
    """Determine MIME type from file extension (parity with legacyMedia.cjs mimeForPath)."""
    ext = image_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".webp":
        return "image/webp"
    return "image/png"
