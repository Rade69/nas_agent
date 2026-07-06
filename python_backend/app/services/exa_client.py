"""Exa web search client (FAZA 16).

Thin HTTP wrapper around the Exa search API. Migrated from the Electron-side
`webSearch()` function in electron/main.cjs so that AI/external API calls live
in the Python backend, not in the Electron main process (architecture rule:
Electron is only shell/IPC/process-manager).

API key is read from settings.exa_api_key (env: EXA_API_KEY). It is never
logged. Errors are surfaced as structured AppError, not raw HTTP text.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import AppError

EXA_SEARCH_URL = "https://api.exa.ai/search"


class ExaClient:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def search(
        self,
        *,
        query: str,
        num_results: int = 5,
        max_characters: int = 900,
        timeout: float = 20.0,
    ) -> list[dict[str, Any]]:
        if not self._api_key:
            raise AppError(
                "MISSING_API_KEY",
                "EXA_API_KEY is not configured on the Python backend.",
                status_code=500,
            )
        count = max(1, min(10, int(num_results)))
        try:
            response = httpx.post(
                EXA_SEARCH_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self._api_key,
                },
                json={
                    "query": query,
                    "type": "auto",
                    "numResults": count,
                    "contents": {"text": {"maxCharacters": max_characters}},
                },
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise AppError(
                "EXA_REQUEST_FAILED",
                f"Exa search request failed: {exc}",
                status_code=502,
            ) from exc

        if response.status_code >= 400:
            raise AppError(
                "EXA_REQUEST_FAILED",
                f"Exa search failed: {response.status_code} {response.text}",
                status_code=502,
            )

        data = response.json()
        results = data.get("results") if isinstance(data, dict) else None
        return results if isinstance(results, list) else []
