"""Model client for the agent runtime (FAZA 15).

Thin HTTP wrapper around the OpenAI Chat Completions API, following the same
pattern as app/services/exa_client.py and app/services/openai_image_client.py
(plain httpx, no SDK dependency, API key never logged).

ModelClient is a Protocol so tests can substitute a fake without any real
network/API call — see python_backend/tests/test_agent_runtime.py. The real
OpenAI key is only ever exercised by a human running the app through
Electron, never by the automated test suite (established project rule: never
spend the user's real API budget in tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.errors import AppError

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


@dataclass
class ModelToolCall:
    id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    content: str | None
    tool_calls: list[ModelToolCall] = field(default_factory=list)


class ModelClient(Protocol):
    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse: ...


class OpenAIModelClient:
    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout: float = 30.0,
    ) -> ModelResponse:
        if not self._api_key:
            raise AppError(
                "MISSING_API_KEY",
                "OPENAI_API_KEY is not configured on the Python backend.",
                status_code=500,
            )
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = httpx.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise AppError(
                "MODEL_REQUEST_FAILED",
                f"Model request failed: {exc}",
                status_code=502,
            ) from exc

        if response.status_code >= 400:
            raise AppError(
                "MODEL_REQUEST_FAILED",
                f"Model request failed: {response.status_code} {response.text}",
                status_code=502,
            )

        data = response.json()
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise AppError(
                "MODEL_RESPONSE_INVALID",
                "Model response did not include any choices.",
                status_code=502,
            )
        message = choices[0].get("message") or {}
        content = message.get("content")
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [
            ModelToolCall(
                id=call.get("id", ""),
                tool_name=call.get("function", {}).get("name", ""),
                arguments=_parse_arguments(call.get("function", {}).get("arguments")),
            )
            for call in raw_tool_calls
        ]
        return ModelResponse(content=content, tool_calls=tool_calls)


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        import json

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}
