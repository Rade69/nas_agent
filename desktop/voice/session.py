"""desktop/voice/session.py — RealtimeSession (OA-1).

Asyncio glasovna sesija: WebSocket na OpenAI Realtime, audio streamovi, tool
calling kroz ToolBridge, reconnect (ReconnectPolicy), guards (ToolLoopGuard/
DuplicateCallGuard/GenerationGuard) i audio-level (AudioLevelTracker). Business
security logika NIJE ovdje — sve ide kroz backend ToolExecutor (INV-1).

Komunicira sa worker-om kroz `callbacks` (jednostavan objekat sa callable
poljima), tako da session ostaje testabilan bez Qt signala.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import queue
import threading
from typing import Any

from desktop.ui.tool_bridge import ToolBridge, to_realtime_tool
from desktop.ui.voice_state import VoiceState
from desktop.voice.audio import AudioLevelTracker, rms_level
from desktop.voice.events import (
    extract_audio_delta,
    extract_transcript,
    failure_code,
    is_failed_response,
    map_event_to_voice_state,
    parse_function_calls,
)
from desktop.voice.guards import DuplicateCallGuard, GenerationGuard, ToolLoopGuard
from desktop.voice.state import ReconnectPolicy

log = logging.getLogger("ricky.voice.session")

SAMPLE_RATE = 24_000
CHANNELS = 1
DTYPE = "int16"
BLOCK = 480

INSTRUCTIONS = (
    "Ti si Riki, glasovni asistent. Govoriš srpski, latinicom. "
    "Odgovaraj kratko. Koristi dostupne alate kad je potrebno. "
    "Ako alat vrati da čeka potvrdu, kratko reci korisniku da čekaš "
    "njegovu potvrdu i ne pokušavaj sam ponovo."
)


class VoiceCallbacks:
    """Callable polja koja worker povezuje na Qt signale."""

    def __init__(self) -> None:
        self.on_state: callable = lambda _state: None
        self.on_audio_input_level: callable = lambda _lvl: None
        self.on_audio_output_level: callable = lambda _lvl: None
        self.on_user_transcript: callable = lambda _t: None
        self.on_assistant_transcript: callable = lambda _t: None
        self.on_confirmation_required: callable = lambda _d: None
        self.on_error: callable = lambda _e: None
        self.on_connected: callable = lambda _b: None
        self.on_reconnecting: callable = lambda: None
        # PC-1 mic health: stream open + frame warning (agregirano, ne per-frame).
        self.on_input_stream_open: callable = lambda _device_name: None
        self.on_input_warning: callable = lambda _msg: None


class RealtimeSession:
    """Glasovna sesija (pokreće je RealtimeWorker u asyncio loop-u)."""

    def __init__(
        self,
        client,
        tool_bridge: ToolBridge,
        callbacks: VoiceCallbacks,
        model: str = "gpt-realtime-2.1-mini",
        max_tool_rounds: int = 8,
        input_device: int | None = None,
        output_device: int | None = None,
    ) -> None:
        self._client = client
        self._tool_bridge = tool_bridge
        self._cb = callbacks
        self._model = model
        self._input_device = input_device
        self._output_device = output_device
        self._stop = threading.Event()
        self._inbox: queue.Queue[dict[str, Any]] = queue.Queue()

        self.policy = ReconnectPolicy()
        self.tool_loop = ToolLoopGuard(max_rounds=max_tool_rounds)
        self.dup = DuplicateCallGuard()
        self.gen = GenerationGuard()
        self.input_level = AudioLevelTracker()
        self.output_level = AudioLevelTracker()

        self._tool_specs: list[dict[str, Any]] = []
        self._pending_confirmations: dict[str, dict[str, Any]] = {}
        self._first_audio_logged = False
        self._speaker_logged = False

    # ── UI → session (thread-safe) ────────────────────────────────────────────

    def request_stop(self) -> None:
        self._inbox.put({"type": "stop"})

    def approve_confirmation(self, call_id: str, confirmation_id: str) -> None:
        self._inbox.put({"type": "approve", "call_id": call_id, "confirmation_id": confirmation_id})

    def approve_by_confirmation_id(self, confirmation_id: str) -> None:
        """React dialog zna samo confirmation_id; nađi call_id i retry."""
        for call_id, pending in list(self._pending_confirmations.items()):
            if pending.get("confirmation_id") == confirmation_id:
                self.approve_confirmation(call_id, confirmation_id)
                return

    def reject_by_confirmation_id(self, confirmation_id: str) -> None:
        for call_id, pending in list(self._pending_confirmations.items()):
            if pending.get("confirmation_id") == confirmation_id:
                self.reject_confirmation(call_id)
                return

    def send_text(self, text: str) -> None:
        self._inbox.put({"type": "send_text", "text": text})

    def set_dictation_mode(self, enabled: bool) -> None:
        self._inbox.put({"type": "dictation", "enabled": enabled})

    def reject_confirmation(self, call_id: str) -> None:
        self._inbox.put({"type": "reject", "call_id": call_id})

    # ── Glavni loop sa reconnect-om ───────────────────────────────────────────

    async def run(self) -> None:
        try:
            while not self._stop.is_set():
                generation = self.gen.next_generation()
                try:
                    await self._connect_and_run(generation)
                except asyncio.CancelledError:
                    break
                except Exception as exc:  # pragma: no cover - runtime network
                    if self._stop.is_set():
                        break
                    code = type(exc).__name__
                    should, delay = self.policy.on_disconnect(code)
                    self._cb.on_error(f"{code}: {exc}")
                    if not should:
                        break
                    self._cb.on_reconnecting()
                    await asyncio.sleep(delay)
        finally:
            self._cb.on_connected(False)

    async def _connect_and_run(self, generation: int) -> None:
        import sounddevice as sd
        from websockets.asyncio.client import connect

        cred = self._resolve_credential()
        if cred is None:
            return
        token, model = cred

        self._tool_specs = self._tool_bridge.fetch_tool_specs()
        tools = [to_realtime_tool(s) for s in self._tool_specs]

        mikrofon_q: queue.Queue[bytes] = queue.Queue()
        zvucnik_q: queue.Queue[bytes] = queue.Queue()
        ostatak = bytearray()

        def mikrofon_callback(indata, frames, time_info, status) -> None:
            if status:
                # PC-1: transient overflow/underflow → warning, ne tihi drop.
                self._cb.on_input_warning(str(status))
            pcm = bytes(indata)
            mikrofon_q.put(pcm)
            self._cb.on_audio_input_level(self.input_level.update(rms_level(pcm)))

        def zvucnik_callback(outdata, frames, time_info, status) -> None:
            if status:
                self._cb.on_input_warning(f"speaker: {status}")
            if not self._speaker_logged:
                self._speaker_logged = True
                from desktop.core.debug_log import debugLog as _log

                _log("[voice] speaker callback first call")
            potrebno = frames * CHANNELS * 2
            while len(ostatak) < potrebno:
                try:
                    ostatak.extend(zvucnik_q.get_nowait())
                except queue.Empty:
                    break
            if len(ostatak) >= potrebno:
                outdata[:] = bytes(ostatak[:potrebno])
                del ostatak[:potrebno]
            else:
                n = len(ostatak)
                outdata[:n] = bytes(ostatak)
                outdata[n:] = b"\x00" * (potrebno - n)
                del ostatak[:]

        # PC-1: eksplicitni device izbor (nema tihog default koji se mijenja).
        from desktop.voice.devices import AudioDeviceService

        _devices = AudioDeviceService()
        _in = _devices.resolve_input(self._input_device)
        _out = _devices.resolve_output(self._output_device)
        from desktop.core.debug_log import debugLog as _log

        _log("[voice] input device:", _in.name if _in else "default")
        _log("[voice] output device:", _out.name if _out else "default")
        self._cb.on_input_stream_open(_in.name if _in else "system default")

        url = f"wss://api.openai.com/v1/realtime?model={model}"
        async with connect(
            url,
            additional_headers={"Authorization": f"Bearer {token}"},
            max_size=None,
        ) as ws:
            await self._await_session_created(ws)
            await self._send_session_update(ws, tools, model)
            self.policy.reset()
            self._cb.on_connected(True)
            self._cb.on_state(VoiceState.IDLE.value)

            with sd.RawInputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, blocksize=BLOCK,
                device=(_in.index if _in else None), callback=mikrofon_callback,
            ), sd.RawOutputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, blocksize=BLOCK,
                device=(_out.index if _out else None), callback=zvucnik_callback,
            ):
                from desktop.core.debug_log import debugLog as _log

                _log("[voice] audio streams open (in+out)")
                await asyncio.gather(
                    self._send_mic(ws, mikrofon_q),
                    self._handle_inbox(ws, generation),
                    self._receive(ws, zvucnik_q, ostatak, generation),
                )

    def _resolve_credential(self) -> tuple[str, str] | None:
        """Traži ephemeral Realtime credential + authoritative model od backend-a.

        RTM-5 + C-1/C-3: model je backend-owned — desktop NE bira model i NE
        smije pretpostaviti model ako ga backend nije vratio. Vraća
        (value, model) samo ako su OBA prisutna; inače fail-closed (None +
        on_error). Nema fallbacka na `gpt-realtime`.
        """
        try:
            resp = self._client.request(
                "/realtime/session",
                method="POST",
                json={"session": {"type": "realtime"}},
                timeout=15.0,
            )
        except Exception:  # pragma: no cover
            log.warning("ephemeral credential fetch failed", exc_info=True)
            self._cb.on_error("Realtime credential fetch failed.")
            return None

        try:
            body = resp.json()
        except Exception:  # pragma: no cover
            self._cb.on_error("Realtime session response invalid (no JSON).")
            return None

        value = body.get("value") or body.get("client_secret", {}).get("value")
        model = body.get("model")

        if not value:
            self._cb.on_error("Realtime session response missing credential.")
            return None
        if not model:
            # C-1: fail-closed — bez authoritative modela session ne počinje.
            self._cb.on_error("Realtime session response missing authoritative model.")
            return None

        return (value, model)

    async def _await_session_created(self, ws) -> None:
        while True:
            dog = json.loads(await ws.recv())
            if dog.get("type") == "session.created":
                return
            if dog.get("type") == "error":  # pragma: no cover
                raise RuntimeError(dog.get("error", {}).get("message", "session error"))

    async def _send_session_update(self, ws, tools: list[dict], model: str) -> None:
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": model,
                        "output_modalities": ["audio"],
                        "instructions": INSTRUCTIONS,
                        "tool_choice": "auto",
                        "tools": tools,
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                                "noise_reduction": {"type": "near_field"},
                                "turn_detection": {
                                    "type": "semantic_vad",
                                    "eagerness": "medium",
                                    "create_response": True,
                                    "interrupt_response": True,
                                },
                                "transcription": {"model": "whisper-1", "language": "sr"},
                            },
                            "output": {
                                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                                "voice": "cedar",
                            },
                        },
                    },
                }
            )
        )

    async def _send_mic(self, ws, mikrofon_q: queue.Queue) -> None:
        while not self._stop.is_set():
            try:
                chunk = mikrofon_q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.005)
                continue
            await ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode(),
                    }
                )
            )

    async def _handle_inbox(self, ws, generation: int) -> None:
        while not self._stop.is_set():
            try:
                cmd = self._inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            if self.gen.is_stale(generation):
                continue
            if cmd.get("type") == "stop":
                self._stop.set()
            elif cmd.get("type") == "approve":
                await self._on_approve(ws, cmd)
            elif cmd.get("type") == "send_text":
                await self._send_text(ws, cmd.get("text", ""))
            elif cmd.get("type") == "dictation":
                await self._set_dictation(ws, bool(cmd.get("enabled")))
            elif cmd.get("type") == "reject":
                self._pending_confirmations.pop(cmd.get("call_id"), None)
                self._cb.on_state(VoiceState.IDLE.value)

    async def _on_approve(self, ws, cmd: dict) -> None:
        call_id = cmd["call_id"]
        pending = self._pending_confirmations.pop(call_id, None)
        if pending is None:
            return
        result = self._tool_bridge.retry_with_confirmation(
            call_id,
            pending["tool_name"],
            pending["arguments"],
            cmd["confirmation_id"],
        )
        await self._send_tool_output(ws, call_id, result)
        self._cb.on_state(VoiceState.IDLE.value if not result.get("ok") else VoiceState.THINKING.value)

    async def _send_text(self, ws, text: str) -> None:
        """Tekstualni prompt kroz aktivnu Realtime sesiju (CR-4)."""
        if not text.strip():
            return
        await ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": text}],
                    },
                }
            )
        )
        await ws.send(json.dumps({"type": "response.create"}))

    async def _set_dictation(self, ws, enabled: bool) -> None:
        """Diktiranje: isključi auto-response VAD-a dok korisnik diktira (CR-4)."""
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "audio": {
                            "input": {
                                "turn_detection": {
                                    "type": "semantic_vad",
                                    "eagerness": "medium",
                                    "create_response": not enabled,
                                    "interrupt_response": True,
                                }
                            }
                        }
                    },
                }
            )
        )

    async def _receive(self, ws, zvucnik_q: queue.Queue, ostatak: bytearray, generation: int) -> None:
        async for poruka in ws:
            if self._stop.is_set():
                break
            dog = json.loads(poruka)
            if self.gen.is_stale(generation):
                continue
            tip = dog.get("type", "")

            state = map_event_to_voice_state(tip)
            if state is not None:
                self._cb.on_state(state)

            audio = extract_audio_delta(dog)
            if audio is not None:
                if not self._first_audio_logged:
                    self._first_audio_logged = True
                    from desktop.core.debug_log import debugLog as _log

                    _log("[voice] first output audio delta:", len(audio), "bytes")
                zvucnik_q.put(audio)
                self._cb.on_audio_output_level(self.output_level.update(rms_level(audio)))

            transcript = extract_transcript(dog)
            if transcript is not None:
                kind, text = transcript
                if kind == "user":
                    self._cb.on_user_transcript(text)
                else:
                    self._cb.on_assistant_transcript(text)
                    self._cb.on_state(VoiceState.IDLE.value)

            if tip == "input_audio_buffer.speech_started":
                # Barge-in: korisnik prekida agenta → isprazni playback buffer.
                ostatak.clear()
                with zvucnik_q.mutex:
                    zvucnik_q.queue.clear()

            elif tip == "response.done":
                if is_failed_response(dog):
                    # OA-1 §7.4: failed response nije običan završen turn —
                    # ne ostavi UI u "thinking", javi grešku.
                    self._cb.on_error(f"response failed: {failure_code(dog)}")
                    self._cb.on_state(VoiceState.ERROR.value)
                else:
                    await self._handle_response_done(dog, ws)

            elif tip == "error":  # pragma: no cover
                self._cb.on_error(dog.get("error", {}).get("message", "realtime error"))

    async def _handle_response_done(self, dog: dict, ws) -> None:
        for call in parse_function_calls(dog):
            if self.gen.is_stale(self.gen.current):
                return
            if not self.dup.start(call.call_id):
                # duplicate call_id — ne izvršavaj dvaput
                await self._send_tool_output(
                    ws,
                    call.call_id,
                    {"ok": False, "duplicate": True, "message": "Alat je već izvršen."},
                )
                continue
            if self.tool_loop.exhausted:
                await self._send_tool_output(
                    ws,
                    call.call_id,
                    {"ok": False, "error": "tool_loop_limit", "message": "Previše alata u ovom zahtjevu."},
                )
                self.dup.finish(call.call_id)
                continue
            self.tool_loop.on_tool_round()

            risk = next((s["risk"] for s in self._tool_specs if s.get("name") == call.name), "high")
            result = self._tool_bridge.run_tool_call(call.call_id, call.name, call.arguments, risk)

            if result.get("waiting_confirmation"):
                self._pending_confirmations[call.call_id] = {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "confirmation_id": result.get("confirmation_id"),
                }
                self._cb.on_confirmation_required(
                    {
                        "call_id": call.call_id,
                        "tool_name": call.name,
                        "arguments": call.arguments,
                        "risk": result.get("risk"),
                        "confirmation_id": result.get("confirmation_id"),
                    }
                )
                self._cb.on_state(VoiceState.WAITING_CONFIRMATION.value)
                # NE šalji confirmation_id/arguments modelu — samo sanitizovan status
                # (INV-3: confirmation je vezan za originalni payload, model ga ne vidi).
                await self._send_tool_output(
                    ws,
                    call.call_id,
                    {
                        "ok": False,
                        "waiting_confirmation": True,
                        "message": result.get("message", ""),
                    },
                )
                continue

            self.dup.finish(call.call_id)
            await self._send_tool_output(ws, call.call_id, result)

    async def _send_tool_output(self, ws, call_id: str, result: dict) -> None:
        await ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    },
                }
            )
        )
        await ws.send(json.dumps({"type": "response.create"}))
