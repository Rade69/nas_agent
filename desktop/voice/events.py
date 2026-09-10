"""desktop/voice/events.py — parsiranje OpenAI Realtime događaja (OA-1).

Čiste funkcije (bez I/O) koje pretvaraju sirove Realtime JSON događaje u
strukturisane ToolCall objekte i mapiraju tip događaja u VoiceState. Centralno
mjesto za ovo mapiranje — ne duplirati u widgetima.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from desktop.ui.voice_state import VoiceState

AUDIO_DELTA_EVENTS = {"response.audio.delta", "response.output_audio.delta"}
ASSISTANT_TRANSCRIPT_DONE = {
    "response.audio_transcript.done",
    "response.output_audio_transcript.done",
}
USER_TRANSCRIPT_DONE = "conversation.item.input_audio_transcription.completed"


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


def parse_function_calls(response_done: dict[str, Any]) -> list[ToolCall]:
    """Izvuče function_call stavke iz `response.done` output niza."""
    calls: list[ToolCall] = []
    for item in response_done.get("response", {}).get("output", []):
        if item.get("type") != "function_call":
            continue
        try:
            arguments = json.loads(item.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append(
            ToolCall(
                call_id=item.get("call_id", ""),
                name=item.get("name", ""),
                arguments=arguments,
            )
        )
    return calls


def extract_audio_delta(event: dict[str, Any]) -> bytes | None:
    if event.get("type") not in AUDIO_DELTA_EVENTS:
        return None
    delta = event.get("delta")
    if not delta:
        return None
    try:
        return base64.b64decode(delta)
    except Exception:
        return None


def extract_transcript(event: dict[str, Any]) -> tuple[str, str] | None:
    """Vraća (kind, text) za transcript događaj, ili None."""
    tip = event.get("type", "")
    if tip in ASSISTANT_TRANSCRIPT_DONE:
        return ("assistant", (event.get("transcript") or "").strip())
    if tip == USER_TRANSCRIPT_DONE:
        return ("user", (event.get("transcript") or "").strip())
    return None


def map_event_to_voice_state(event_type: str) -> str | None:
    """Mapira tip Realtime događaja u VoiceState (None = ne mijenja state)."""
    if event_type == "input_audio_buffer.speech_started":
        return VoiceState.LISTENING.value
    if event_type == "input_audio_buffer.speech_stopped":
        return VoiceState.THINKING.value
    if event_type in AUDIO_DELTA_EVENTS:
        return VoiceState.SPEAKING.value
    return None


def is_failed_response(response_done: dict[str, Any]) -> bool:
    """True ako je response.done sa status=failed (ne tretirati kao običan turn)."""
    return response_done.get("response", {}).get("status") == "failed"


def failure_code(response_done: dict[str, Any]) -> str | None:
    """Kod greške iz failed response-a (None ako nije failed)."""
    if not is_failed_response(response_done):
        return None
    return (
        response_done.get("response", {})
        .get("status_details", {})
        .get("error", {})
        .get("code")
    )
