# Omarchy addendum — OA-0…OA-4 (P1 paket)

## Datum

2026-09-09

## Scope

Primjena `docs/NAS_AGENT_OMARCHY_LESSONS_IMPLEMENTATION_PLAN.md` P1 paketa (OA-0…OA-4) na Qt voice runtime — najviši prioritet plana.

## GitNexus impact

GitNexus MCP alati nisu dostupni. Ručna analiza: **čisto aditivno** u `desktop/voice/` + `desktop/ui/` + `desktop/tests/`. `python_backend/` netaknut (0 izmjena — OA-4 "backend owns pending action" NAMJERNO nije urađen, vidi niže). `electron/`/`src/` netaknuti. Jedini netrivijalan refaktor: `desktop/ui/tool_bridge.py` (uklonjeni Qt signali, postao obična klasa) i brisanje `desktop/ui/voice.py` (zamijenjen paketom). Rizik ~nula za postojeći sistem.

## Šta je urađeno (po fazi)

### OA-0 — Baseline + contract freeze ✅
- `docs/QT_VOICE_RUNTIME_CONTRACT.md` — zamrznuti kontrakti: VoiceState (9→7), tool execution (POST /tools/execute + CONFIRMATION_REQUIRED shape), confirmation (create/approve/reject + payload binding), Realtime vs Chat-Completions tool schema (BEZ/SA `function` omotača).

### OA-1 — Production Realtime runtime ✅
- `desktop/voice/state.py` — `ConnectionState`, `ErrorClass`, `ReconnectPolicy` (exponential backoff 2/4/8 capped, klasifikacija auth/fatal/network/rate-limit/manual, auth se NE retry-uje).
- `desktop/voice/guards.py` — `ToolLoopGuard` (bounded tool rounds), `DuplicateCallGuard` (completed+inflight), `GenerationGuard` (stale session).
- `desktop/voice/events.py` — parsiranje (function_call, audio delta, transcript, voice-state mapping, `is_failed_response`/`failure_code`).
- `desktop/voice/audio.py` — `rms_level` (RMS 0..1) + `AudioLevelTracker` (fast attack, slow release).
- `desktop/voice/session.py` — `RealtimeSession` (reconnect loop, barge-in, failed-response handling, tool calling kroz ToolBridge).
- `desktop/voice/worker.py` — `RealtimeWorker` (QThread + asyncio, centralni signali).
- Obrisan `desktop/ui/voice.py` (zamijenjen paketom).

### OA-2 — Centralni VoiceSignals contract ✅
- `VoiceStateBus` proširen u centralni signal owner: `state_changed`, `audio_input_level`, `audio_output_level`, `user_transcript`, `assistant_transcript`, `connected_changed`, `error`. Orb više NE poll-uje (koristi bus — QM-3 je već prešao, sada usklađeno).

### OA-3 — Audio-reactive orb ✅ (kod)
- `RickyOrbWidget.postavi_audio_nivo()` + render: stvarna amplituda nadjačava sintetički puls za listening/speaking. OrbWindow pretplata na `audio_input_level`.

### OA-4 — Confirmation Bridge v2 🟡 (invarijante zadovoljene, backend change follow-up)
- Potvrđeno da postojeći tok zadovoljava INV-2/INV-3: approve → `retry_with_confirmation` izvršava TAČNU originalnu akciju (isti tool_name/arguments + confirmation_id), model dobija samo rezultat — NEMA "try that action again" instrukcije.
- Sanitizacija: `confirmation_id`/`arguments` se NE šalju modelu (samo `waiting_confirmation` status).
- **Nije urađeno** (follow-up): "backend owns pending action" — OA-4 §10.2 želi da backend (ne klijent) drži i izvrši pending action. Ovo je arhitektonska optimizacija, ne bezbjednosna potreba: backend confirmation VEĆ sadrži `payload` (arguments) i veže ga preko `payload_hash`, a klijentski retry je funkcionalno ekvivalentan i bezbjedan. Namjerno preskočeno da se ne dira sigurnosno-kritičan `python_backend/` confirmation flow bez jasne potrebe.

## Šta nije dirano

- `python_backend/` — 0 izmjena (OA-4 backend-owned pending action odložen).
- `electron/`, `src/` — netaknuti.

## Verifikacija

- `python -m pytest desktop/tests -m "not integration"` → **63 passed**.
- Reconnect: klasifikacija (auth/network/rate-limit/fatal/manual), backoff (2/4/8 capped), bounded retry, reset.
- Guards: tool-loop budget + reset na novi turn, duplicate call (inflight+completed), stale generation.
- Events: function_call parsing (loš JSON → {}), audio delta, transcript, failed response.
- Audio: silence→0, clipping→≤1, attack/release smoothing.
- Orb: audio nivo clamp 0..1, bus pretplata na state + audio level.

## Rizici/ograničenja (iskreno)

- End-to-end glas i audio-reactive orb NISU runtime-testirani (headless: nema mikrofona/API ključa). RMS formula i `max(sintetički, audio_nivo)` blending trebaju kalibraciju na korisnikovom mikrofonu.
- Ephemeral-credential-za-WebSocket protokol nije potvrđen (vidi QM-3 report).
- OA-4 pun backend change ("backend owns pending action") je namjerno odložen.

## Potreban follow-up

- OA-4 backend change (backend-owned pending action) — tek ako se pokaže potreba nakon stabilnog voice E2E.
- P2 paket: OA-5 (desktop context snapshot), OA-6 (capability manifest), OA-12 (voice/text parity).
- Korisničko runtime testiranje glasa + orb audio reakcije.

## Potrebna korisnička potvrda

- Runtime test glasa + orb (mikrofon + API ključ) — RMS/blending kalibracija.
- Odluka da li OA-4 backend-owned pending action treba sada ili je klijentski retry prihvatljiv za v1.
