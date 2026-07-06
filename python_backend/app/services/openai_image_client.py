"""OpenAI image generation client (FAZA 16).

Thin HTTP wrapper around the OpenAI Images API (gpt-image). Migrated from the
Electron-side `generateImage()` function in electron/main.cjs so that AI/external
API calls live in the Python backend.

API key is read from settings.openai_api_key (env: OPENAI_API_KEY). It is never
logged. The backend already holds this key for the FAZA 6 realtime session flow;
this client reuses it for image generation.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import AppError

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


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
