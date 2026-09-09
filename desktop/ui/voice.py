"""desktop/ui/voice.py — OpenAI Realtime glasovni klijent u QThread (QM-3).

Port `spikes/voice_websocket_spike.py` u pravu app strukturu, sa tri ključne
razlike u odnosu na spike (koji je koristio standardni API ključ + lokalne
alate):
  1. **Ephemeral credential** — traži ga od backend-a (`POST /realtime/session`)
     umjesto da drži OPENAI_API_KEY lokalno (Security Gate 0).
  2. **Stvarni tool execution** — svaki function_call ide kroz ToolBridge →
     `POST /tools/execute` (permission/cancellation gate), nikad lokalno.
  3. **Confirmation flow** — kad tool vrati CONFIRMATION_REQUIRED, bridge
     kreira confirmation, glas čeka (model obavijesti korisnika), a odobrenje
     iz UI-ja se vraća kroz thread-safe inbox i ponavlja originalni call.

Arhitektura (QT_MIGRATION_PLAN §QM-3): QThread sa sopstvenim `asyncio.run()`;
komunikacija voice→UI ide kroz Qt signale (QueuedConnection), UI→voice kroz
thread-safe `queue.Queue` koji asyncio loop poll-uje.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import queue
import threading
from typing import Any

from PySide6.QtCore import QThread, Signal

from desktop.ui.tool_bridge import ToolBridge, to_realtime_tool
from desktop.ui.voice_state import VoiceState

log = logging.getLogger("ricky.voice")

SAMPLE_RATE = 24_000
CHANNELS = 1
DTYPE = "int16"
BLOCK = 480  # 20ms po chunku

INSTRUCTIONS = (
    "Ti si Riki, glasovni asistent. Govoriš srpski, latinicom. "
    "Odgovaraj kratko. Koristi dostupne alate kad je potrebno. "
    "Ako alat vrati da čeka potvrdu, kratko reci korisniku da čekaš "
    "njegovu potvrdu i ne pokušavaj sam ponovo."
)


class RealtimeVoiceSession(QThread):
    """Glasovna sesija: WebSocket + audio + tool calling u pozadinskoj niti."""

    voice_state_changed = Signal(str)
    user_transcript = Signal(str)
    assistant_transcript = Signal(str)
    confirmation_required = Signal(dict)  # {tool_name, arguments, risk, confirmation_id, call_id}
    error_occurred = Signal(str)

    def __init__(
        self,
        backend_client,
        tool_bridge: ToolBridge,
        model: str = "gpt-realtime",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._client = backend_client
        self._tool_bridge = tool_bridge
        self._model = model
        self._stop = threading.Event()
        self._inbox: queue.Queue[dict[str, Any]] = queue.Queue()
        self._tool_specs: list[dict[str, Any]] = []
        # pending confirmations: call_id -> podaci za retry nakon odobrenja.
        self._pending_confirmations: dict[str, dict[str, Any]] = {}

    # ── UI → voice (thread-safe) ──────────────────────────────────────────────

    def request_stop(self) -> None:
        self._inbox.put({"type": "stop"})

    def approve_confirmation(self, call_id: str, confirmation_id: str) -> None:
        self._inbox.put({"type": "approve", "call_id": call_id, "confirmation_id": confirmation_id})

    def reject_confirmation(self, call_id: str) -> None:
        self._inbox.put({"type": "reject", "call_id": call_id})

    # ── QThread ───────────────────────────────────────────────────────────────

    def run(self) -> None:  # noqa: D401
        try:
            asyncio.run(self._main())
        except Exception as exc:  # pragma: no cover - runtime audio/network
            log.exception("voice session failed")
            self.error_occurred.emit(f"{type(exc).__name__}: {exc}")

    def _set_state(self, state: str) -> None:
        self.voice_state_changed.emit(state)

    # ── Glavna asyncio petlja ─────────────────────────────────────────────────

    async def _main(self) -> None:
        try:
            import sounddevice as sd
            import websockets
            from websockets.asyncio.client import connect
        except ImportError as exc:  # pragma: no cover
            self.error_occurred.emit(f"Nedostaje biblioteka: {exc}")
            return

        token = self._resolve_credential()
        if token is None:
            self.error_occurred.emit("Nema OpenAI credential-a (backend nije dostupan).")
            return

        self._tool_specs = self._tool_bridge.fetch_tool_specs()
        tools = [to_realtime_tool(s) for s in self._tool_specs]

        mikrofon_q: queue.Queue[bytes] = queue.Queue()
        zvucnik_q: queue.Queue[bytes] = queue.Queue()
        ostatak = bytearray()

        def mikrofon_callback(indata, frames, time_info, status) -> None:
            if not status:
                mikrofon_q.put(bytes(indata))

        def zvucnik_callback(outdata, frames, time_info, status) -> None:
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

        url = f"wss://api.openai.com/v1/realtime?model={self._model}"
        try:
            async with connect(
                url,
                additional_headers={"Authorization": f"Bearer {token}"},
                max_size=None,
            ) as ws:
                await self._await_session_created(ws)
                await self._send_session_update(ws, tools)
                await self._run_loops(ws, sd, mikrofon_q, zvucnik_q, mikrofon_callback, zvucnik_callback, ostatak)
        except websockets.exceptions.InvalidStatus as exc:  # pragma: no cover
            self.error_occurred.emit(f"Server odbio konekciju: {exc}")

    def _resolve_credential(self) -> str | None:
        """Traži ephemeral Realtime credential od backend-a (Security Gate 0)."""
        try:
            resp = self._client.request(
                "/realtime/session",
                method="POST",
                json={"session": {"type": "realtime", "model": self._model}},
                timeout=15.0,
            )
            value = resp.json().get("value") or resp.json().get("client_secret", {}).get("value")
            if value:
                return value
        except Exception:  # pragma: no cover
            log.warning("ephemeral credential fetch failed", exc_info=True)
        return None

    async def _await_session_created(self, ws) -> None:
        while True:
            dog = json.loads(await ws.recv())
            if dog.get("type") == "session.created":
                return
            if dog.get("type") == "error":  # pragma: no cover
                self.error_occurred.emit(dog.get("error", {}).get("message", "session error"))
                return

    async def _send_session_update(self, ws, tools: list[dict]) -> None:
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": self._model,
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

    async def _run_loops(self, ws, sd, mikrofon_q, zvucnik_q, mikrofon_callback, zvucnik_callback, ostatak) -> None:
        async def salji() -> None:
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

        async def inbox() -> None:
            while not self._stop.is_set():
                try:
                    cmd = self._inbox.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.05)
                    continue
                await self._handle_command(cmd, ws)

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, blocksize=BLOCK, callback=mikrofon_callback
        ), sd.RawOutputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, blocksize=BLOCK, callback=zvucnik_callback
        ):
            await asyncio.gather(salji(), inbox(), self._primaj(ws, zvucnik_q, ostatak))

    async def _primaj(self, ws, zvucnik_q, ostatak) -> None:
        audio_delta = {"response.audio.delta", "response.output_audio.delta"}
        transcript_done = {"response.audio_transcript.done", "response.output_audio_transcript.done"}
        async for poruka in ws:
            if self._stop.is_set():
                break
            dog = json.loads(poruka)
            tip = dog.get("type", "")

            if tip in audio_delta:
                self._set_state(VoiceState.SPEAKING.value)
                zvucnik_q.put(base64.b64decode(dog["delta"]))

            elif tip == "input_audio_buffer.speech_started":
                self._set_state(VoiceState.LISTENING.value)

            elif tip == "input_audio_buffer.speech_stopped":
                self._set_state(VoiceState.THINKING.value)

            elif tip in transcript_done:
                self.assistant_transcript.emit(dog.get("transcript", "").strip())
                self._set_state(VoiceState.IDLE.value)

            elif tip == "conversation.item.input_audio_transcription.completed":
                self.user_transcript.emit(dog.get("transcript", "").strip())

            elif tip == "response.done":
                await self._handle_response_done(dog, ws)

            elif tip == "error":  # pragma: no cover
                self.error_occurred.emit(dog.get("error", {}).get("message", "realtime error"))

    async def _handle_response_done(self, dog: dict, ws) -> None:
        for item in dog.get("response", {}).get("output", []):
            if item.get("type") != "function_call":
                continue
            name = item.get("name", "")
            call_id = item.get("call_id", "")
            try:
                args = json.loads(item.get("arguments") or "{}")
            except json.JSONDecodeError:  # pragma: no cover
                args = {}

            risk = next((s["risk"] for s in self._tool_specs if s.get("name") == name), "high")
            result = self._tool_bridge.run_tool_call(call_id, name, args, risk)

            if result.get("waiting_confirmation"):
                # Confirmation Bridge: sačuvaj za retry, emituj signal za UI,
                # model obavijesti korisnika i čeka (NE izvršava sam).
                confirmation = result.get("confirmation_id")
                # run_tool_call je već kreirao confirmation i emituje signal
                # preko bridge-a; ovdje samo vežemo call_id za retry.
                self._pending_confirmations[call_id] = {
                    "tool_name": name,
                    "arguments": args,
                    "risk": risk,
                }
                self._set_state(VoiceState.WAITING_CONFIRMATION.value)
            elif result.get("ok"):
                self._set_state(VoiceState.THINKING.value)

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

    async def _handle_command(self, cmd: dict, ws) -> None:
        if cmd.get("type") == "stop":
            self._stop.set()
            return
        if cmd.get("type") == "approve":
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
            await self._send_retry_result(ws, call_id, result)
        elif cmd.get("type") == "reject":
            self._pending_confirmations.pop(cmd.get("call_id"), None)
            self._set_state(VoiceState.IDLE.value)

    async def _send_retry_result(self, ws, call_id: str, result: dict) -> None:
        self._set_state(VoiceState.IDLE.value if not result.get("ok") else VoiceState.THINKING.value)
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
