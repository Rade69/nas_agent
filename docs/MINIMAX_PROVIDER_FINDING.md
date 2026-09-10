# MiniMax Provider — Discovery & Architecture Finding (MM-0)

**Datum:** 2026-09-09
**Branch:** `qt-desktop-migration`
**Izvori:** `platform.minimax.io/docs/llms.txt` + `platform.minimax.io/docs/api-reference/api-overview` (zvanično, učitano 2026-09-09)

## 1. Šta MiniMax trenutno zvanično podržava

| Sposobnost | Status | Izvor |
|---|---|---|
| MiniMax-M3 (agentic/tool-use, 1M context) | ✅ HTTP, Anthropic SDK (preporučeno), OpenAI SDK | `api-overview` "Large Language Model" |
| Tool calling (M3) | ✅ (`text-m3-function-call.md`) | llms.txt "Tool Use & Interleaved Thinking" |
| Streaming text (M3) | ✅ (Responses API podržava streaming) | llms.txt "Create Response" |
| Speech 2.8 streaming TTS | ✅ HTTP + WebSocket (`t2a`), pcm/mp3/flac/wav | `api-overview` "Speech Model" |
| Speech-to-Text (STT) | ✅ audio fajl → tekst, streaming, diarization | llms.txt "Speech to Text" |
| **Native Realtime speech-to-speech** | ❌ **NE postoji** (nema OpenAI-Realtime ekvivalenta u dokumentaciji) | llms.txt (odsutno) |
| Audio input kroz OpenAI-compatible endpoint | ❌ (compatibility endpoint ne podržava audio) | plan §1 tačka 5, potvrđeno odsustvom |

**Jezici TTS (40):** uključuje **Croatian (32)**, ali **NE Serbian** — plan §15 upozorenje je tačno; srpski je best-effort preko hrvatskog jezika.

## 2. Arhitektonska odluka

**PATH B — Composite MiniMax Voice Provider.** Nema nativnog speech-to-speech, ali svi dijelovi su zvanično dostupni:

```text
Microphone PCM
    ↓ Speech-to-Text (STT)
tekst
    ↓ MiniMax-M3 (tool calling / streaming text)
tekst + tool calls
    ↓ Speech 2.8 streaming TTS (WebSocket)
audio output
```

Ovo se kapsulira iza `MiniMaxVoiceProvider` tako da Ricky ne zna da li MiniMax interno koristi 1 ili 3 servisa.

## 3. Šta NE radimo

- NE izmišljamo MiniMax Realtime endpoint (STOP-1).
- NE zaobilazimo `ToolExecutor`/`PermissionEngine` (STOP-2).
- NE labelujemo OpenAI-STT + MiniMax-M3 + MiniMax-TTS kao "MiniMax" — to bi bio Hybrid (zabranjeno implicitno, plan §18).
- NE tvrdimo da je srpski native-podržan — Croatian best-effort.

## 4. Provider boundary (dva mjesta)

```text
1. Voice: desktop/voice/ → RealtimeProvider Protocol (OpenAIRealtimeProvider, MiniMaxVoiceProvider)
2. Text:  python_backend/app/agent/model_client.py → ModelClient Protocol (OpenAIModelClient, MiniMaxModelClient)
```

Oba moraju normalizovati provider-specifične događaje/protokole u zajedničke Ricky događaje; `ToolExecutor`/`PermissionEngine`/`Confirmation`/`VoiceState`/`Orb` ostaju provider-nezavisni.
