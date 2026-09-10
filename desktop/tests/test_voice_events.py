"""Testovi za Realtime event parsing (OA-1)."""

import base64
import json

from desktop.voice.events import (
    extract_audio_delta,
    extract_transcript,
    failure_code,
    is_failed_response,
    map_event_to_voice_state,
    parse_function_calls,
)


def _response_done(output):
    return {"type": "response.done", "response": {"output": output}}


def test_parse_function_calls_extracts_tool_calls():
    dog = _response_done(
        [
            {
                "type": "function_call",
                "name": "web_search",
                "call_id": "call_1",
                "arguments": json.dumps({"q": "vrijeme"}),
            },
            {"type": "message", "content": "ignored"},
        ]
    )
    calls = parse_function_calls(dog)
    assert len(calls) == 1
    assert calls[0].name == "web_search"
    assert calls[0].call_id == "call_1"
    assert calls[0].arguments == {"q": "vrijeme"}


def test_parse_function_calls_bad_json_falls_back_to_empty():
    dog = _response_done(
        [{"type": "function_call", "name": "x", "call_id": "c", "arguments": "{not json"}]
    )
    calls = parse_function_calls(dog)
    assert calls[0].arguments == {}


def test_extract_audio_delta():
    payload = base64.b64encode(b"\x01\x02").decode()
    dog = {"type": "response.audio.delta", "delta": payload}
    assert extract_audio_delta(dog) == b"\x01\x02"


def test_extract_audio_delta_ignores_non_audio():
    assert extract_audio_delta({"type": "response.done", "delta": "x"}) is None


def test_extract_transcript():
    assert extract_transcript({"type": "response.audio_transcript.done", "transcript": "Zdravo"}) == (
        "assistant",
        "Zdravo",
    )
    assert extract_transcript(
        {"type": "conversation.item.input_audio_transcription.completed", "transcript": "Bok"}
    ) == ("user", "Bok")


def test_map_event_to_voice_state():
    assert map_event_to_voice_state("input_audio_buffer.speech_started") == "listening"
    assert map_event_to_voice_state("input_audio_buffer.speech_stopped") == "thinking"
    assert map_event_to_voice_state("response.audio.delta") == "speaking"
    assert map_event_to_voice_state("response.done") is None


def test_failed_response_detection():
    ok = {"type": "response.done", "response": {"status": "completed"}}
    assert is_failed_response(ok) is False

    failed = {
        "type": "response.done",
        "response": {"status": "failed", "status_details": {"error": {"code": "rate_limit_exceeded"}}},
    }
    assert is_failed_response(failed) is True
    assert failure_code(failed) == "rate_limit_exceeded"
    assert failure_code(ok) is None
