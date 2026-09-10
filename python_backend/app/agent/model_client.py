"""Model clients for the agent runtime (FAZA 15 + MM-3).

Thin HTTP wrappers around OpenAI-compatible Chat Completions APIs, following
the same pattern as app/services/exa_client.py (plain httpx, no SDK, API key
never logged). Two providers share the same OpenAI-compatible wire shape:

  - OpenAIModelClient  → https://api.openai.com/v1/chat/completions
  - MiniMaxModelClient → https://api.minimax.io/v1/chat/completions (MM-3,
    docs/MINIMAX_PROVIDER_FINDING.md)

ModelClient is a Protocol so tests can substitute a fake without any real
network/API call. Real API keys are never exercised by the automated suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.errors import AppError

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
MINIMAX_CHAT_COMPLETIONS_URL = "https://api.minimax.io/v1/chat/completions"


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


def _post_chat_completions(
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    try:
        response = httpx.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
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
    # MiniMax reports some errors via base_resp.status_code inside a 200 body
    # (e.g. 1002 rate limit, 1004 auth) — surface those instead of returning
    # an empty response. See docs/api-reference/errorcode.
    base_resp = data.get("base_resp") if isinstance(data, dict) else None
    if isinstance(base_resp, dict) and base_resp.get("status_code"):
        raise AppError(
            "MODEL_REQUEST_FAILED",
            f"MiniMax error {base_resp.get('status_code')}: {base_resp.get('status_msg', '')}",
            status_code=502,
        )
    return data


def _parse_chat_completion_response(data: dict[str, Any]) -> ModelResponse:
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
        data = _post_chat_completions(OPENAI_CHAT_COMPLETIONS_URL, self._api_key, payload, timeout)
        return _parse_chat_completion_response(data)


class MiniMaxModelClient:
    """MiniMax-M3 through the OpenAI-compatible Chat Completions endpoint.

    Docs: platform.minimax.io/docs/api-reference/text-chat-openai — the wire
    shape (tools/tool_calls/finish_reason) matches OpenAI's, so this reuses the
    same parsing. M3 defaults to adaptive "thinking" (returns a <think> block
    inside content); Ricky wants fast, clean replies, so thinking is disabled.
    """

    def __init__(self, api_key: str | None, model: str = "MiniMax-M3") -> None:
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
                "MINIMAX_API_KEY is not configured on the Python backend.",
                status_code=500,
            )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            # Disable M3 reasoning so replies stay concise (no <think> block).
            "thinking": {"type": "disabled"},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        data = _post_chat_completions(MINIMAX_CHAT_COMPLETIONS_URL, self._api_key, payload, timeout)
        return _parse_chat_completion_response(data)


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
