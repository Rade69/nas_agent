# Qt Voice Runtime — Contract Freeze (OA-0)

**Datum:** 2026-09-09
**Branch:** `qt-desktop-migration`
**HEAD:** `6e9f774`
**Status:** contract freeze za OA-1…OA-4 (Omarchy lessons plan)

Ovaj dokument zamrzava stvarne kontrakte na koje se oslanjaju naredne faze.
Ako se bilo koji oblik promijeni, ovdje se mora ažurirati u istom commitu.

## Baseline

```text
backend tests:  412 passed (pytest, python_backend/)
desktop tests:  35 passed (pytest desktop/tests, uklj. 1 integration)
working tree:   samo untracked ovaj plan fajl
```

## 1. VoiceState (kanonski, 9)

Izvor: `desktop/ui/voice_state.py` (`VoiceState` enum, vrijednosti identične `src/lib/voiceState.ts`).

```text
idle, listening, transcribing, thinking, speaking,
waiting_confirmation, interrupted, muted, error
```

Mapiranje u 7 vizuelnih orb stanja (`map_voice_state_to_orb_state`):

```text
listening + transcribing   → listening
thinking                   → thinking
speaking                   → speaking
waiting_confirmation + interrupted → warning
error                      → error
muted                      → muted
idle (i nepoznato)         → idle
```

## 2. Tool execution contract

`GET /tools` → `{"tools": [ToolDefinition]}` gdje `ToolDefinition` ima najmanje:
`name, description, input_schema, risk, requires_confirmation, requires_computer_mode, enabled, reads_external_content, outbound`.

`POST /tools/execute` body:
```json
{"tool_name": "...", "arguments": {...}, "context": {"computer_mode": false, "confirmation_id": null, "external_content_seen": false}}
```

Response (uvijek HTTP 200, čak i za greške — `response_model`):
```json
{"ok": false, "tool_name": "...", "error": {"code": "CONFIRMATION_REQUIRED", "message": "..."}, "tool_state": "failed", "execution_id": "...", "action_log_id": "...", "duration_ms": 0}
```

**CONFIRMATION_REQUIRED** = `ok=false` + `error.code == "CONFIRMATION_REQUIRED"` + `tool_state="failed"`. NE vraća se kao HTTP 403.

Retry zahtijeva `context.confirmation_id` (approved, nepotrošena, neexpired).

## 3. Confirmation contract

```text
POST   /confirmations                {action_name, payload, risk_level, tool_name, ttl_seconds?} → {id, status, ...}
POST   /confirmations/{id}/approve   → status="approved"
POST   /confirmations/{id}/reject    → status="rejected"
DELETE /confirmations/{id}           → status="cancelled"
```

Binding (permission_engine): `confirmation_id` je vezan za `tool_name` + `payload_hash` + `expires_at`. Promijenjen payload ili prošla expiry ⇒ odbijeno. Confirmation je single-use (postaje `consumed` nakon izvršenja).

## 4. Realtime tool schema (različito od Chat Completions)

Realtime (`desktop/ui/tool_bridge.py:to_realtime_tool`, tačno prema spike-u):
```json
{"type": "function", "name": "...", "description": "...", "parameters": {...}}
```
**BEZ** `function` omotača.

Chat Completions (`prompt_builder.tools_to_openai_schema`, za text agent):
```json
{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
```
**SA** `function` omotačem.

Ne miješati ova dva oblika — Realtime odbacuje `function` omotač.

## 5. VoiceSignals contract (cilj OA-2)

Jedan signal owner objekat (naziv još ne fiksiran), centralni signali:

```text
state_changed(str)
audio_input_level_changed(float)    0..1
audio_output_level_changed(float)   0..1
user_transcript(str)
assistant_transcript(str)
connected_changed(bool)
error(str)
confirmation_required(object)
```

## 6. Neprekršive invarijante (INV-1…INV-8 iz plana)

- Glas i tekst → isti `ToolExecutor` (nema paralelnog puta).
- Model nikad ne potvrđuje sam svoju akciju.
- Approval vezan za originalni payload (`confirmation_id` + `tool_name` + `payload_hash` + expiry).
- UI nema trajni OpenAI ključ (ephemeral credential od backend-a).
- Audio level iz postojećeg PCM streama, ne drugi capture.
