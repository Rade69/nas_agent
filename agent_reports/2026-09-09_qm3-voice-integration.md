# QM-3 — Glasovna integracija (WebSocket)

## Datum

2026-09-09

## Scope

QM-3 iz `docs/QT_MIGRATION_PLAN_2026-07-20.md` — prenijeti `spikes/voice_websocket_spike.py` u pravu app strukturu: dinamički tool registry, stvarni tool execution kroz permission engine, realan confirmation dijalog, idempotency, voice-state emitovanje.

## GitNexus impact

GitNexus MCP alati nisu dostupni. Ručna analiza: **čisto aditivna promjena** u `desktop/ui/` + `desktop/tests/` + `desktop/main.py`. `python_backend/`, `electron/`, `src/` netaknuti (0 izmjena). Nova arhitektonska odluka (voice state = lokalni bus, ne backend) ne dira postojeći kod — samo odstupa od QM-2 plan-teksta koji je pretpostavio `GET /voice/state` u backend-u. Rizik ~nula za postojeći sistem.

## Šta je urađeno

1. **`desktop/ui/voice_bus.py`** — `VoiceStateBus` (QObject + `state_changed` signal, emituje samo na promjenu). Lokalni izvor istine za glasovno stanje u Qt procesu.
2. **`desktop/ui/tool_bridge.py`** — `ToolBridge` (QObject): `execute_tool` (POST `/tools/execute`, normalizovan rezultat), `create_confirmation`/`approve_confirmation`/`reject_confirmation` (POST `/confirmations*`), `run_tool_call` (idempotency `completed_call_ids` + auto-create-confirmation na `CONFIRMATION_REQUIRED` + `confirmation_required` signal), `retry_with_confirmation` (retry sa `context.confirmation_id`), `build_realtime_tools`/`to_realtime_tool` (ToolDefinition → OpenAI function schema).
3. **`desktop/ui/confirmation_dialog.py`** — `ConfirmationDialog` (QDialog): prikaz akcije/rizika/payload-a, "Odobri" disable-ovano tokom `ARM_DELAY_MS=250` (S-4/S30), Escape = odbijanje (nikad odobravanje), `approved`/`rejected` signali.
4. **`desktop/ui/voice.py`** — `RealtimeVoiceSession` (QThread + `asyncio.run()`): ephemeral credential iz backend-a (`POST /realtime/session`), WebSocket na OpenAI Realtime, `sounddevice` RawInputStream/OutputStream, tool calling kroz ToolBridge, confirmation flow (pending + retry kroz thread-safe inbox), voice-state emitovanje.
5. **Refaktor `orb_window.py`** — prešao sa HTTP polling-a na `VoiceStateBus` pretplatu (uklonjeni `HttpVoiceStateProvider`/`VoiceStatePoller` — bile su zasnovane na pogrešnoj pretpostavci da je voice state u backend-u).
6. **Testovi** — `test_tool_bridge.py` (8), `test_confirmation_dialog.py` (4), ažuriran `test_orb.py` (bus testovi) → ukupno **34 desktop testa**.

## Zašto je urađeno

Glas je jedina stvar koja može ubiti migraciju; spike je dokazao izvodljivost, ali je koristio standardni API ključ direktno i lokalne alate — oboje suprotno Security Gate 0 i permission-engine arhitekturi. Ovo ga pretvara u ispravan tok: ključ ostaje na backend-u (ephemeral token), svaki tool call prolazi kroz pravi `POST /tools/execute` gate.

## Kako je urađeno (ključne odluke)

- **Voice state = lokalni bus, ne backend.** Glas živi u Qt procesu (`desktop/ui/voice.py`, mikrofon je klijentski resurs), pa `GET /voice/state` u backend-u bi bio bespotreban HTTP roundtrip. Ovo odstupa od QM-2 plan-teksta (koji je pretpostavio backend polling) — ispravljeno jer je arhitektonski čistije.
- **Confirmation Bridge port** (obrazac iz `src/lib/realtime.ts`): tool → `CONFIRMATION_REQUIRED` → bridge kreira confirmation + emituje signal → model obavijesti korisnika → UI odobri → `retry_with_confirmation` sa `confirmation_id`. Idempotency `completed_call_ids` port iz realtime.ts R3.
- **QThread + asyncio** (plan §QM-3 odluka): voice→UI kroz Qt signale, UI→voice kroz thread-safe `queue.Queue` inbox (bez `qasync`).

## Šta nije dirano

- `python_backend/` — netaknut. NIJE dodat `/voice/state` endpoint (namjerno — lokalni bus). Ephemeral-credential put koristi postojeći `POST /realtime/session`.
- `electron/`, `src/` — netaknuti (reference za port, ostaju do QM-9).

## Verifikacija

- `python -m pytest desktop/tests -m "not integration"` → **34 passed**.
- ToolBridge: normalize (ok/error_code), idempotency (isti call_id → `duplicate`, samo 1 stvarni execute), CONFIRMATION_REQUIRED → kreirana confirmation + emitovan signal + `waiting_confirmation`, retry koristi `confirmation_id` u context.
- ConfirmationDialog: approve disabled do armed, approve/reject signali, Escape=reject.
- VoiceStateBus: emituje samo na promjenu; OrbWindow pretplata radi (bus → widget state).
- `voice.py` se čisto importuje (lazy import `sounddevice`/`websockets`, dostupni 0.5.5/16.0).

## Rizici/ograničenja (iskreno)

- **End-to-end glas NIJE testiran** — headless okruženje nema mikrofon ni OpenAI Realtime ključ. Gate-ovi "glasom pokrenut stvaran alat", "high-risk preko glasa otvara dijalog" i "mjerenje latencije" se ne mogu potvrditi odavde.
- **Ephemeral-credential-za-WebSocket** — `POST /realtime/session` (backend) je pisan za WebRTC `client_secrets`; da li isti ephemeral key radi kao `Authorization: Bearer` za WebSocket konekciju nije potvrđeno na stvarnom ključu. Možda treba poseban backend put za WebSocket credential (follow-up).
- **Audio device izbor** nije implementiran (default sistemski) — plan ga je označio kao ne-blokirajući.
- `voice.py` "organski" puls i AEC/eho su sa spike-a; potvrda na korisnikovom hardveru je dio QM-9a.

## Potreban follow-up

- Korisničko runtime testiranje glasa (`OPENAI_API_KEY` + mikrofon): stvarni tool call, confirmation dijalog, latencija (<~2s prosjek je kriterijum).
- Potvrditi/prilagoditi ephemeral credential za WebSocket (možda novi backend endpoint).
- QM-4 — Glavni prozor, navigacija, composition root (povezuje voice.py + bus + orb + backend u jednu app).

## Potrebna korisnička potvrda

- Runtime test glasa na stvarnoj mašini (sa API ključem + mikrofonom).
- Odluka o tome da li lokalni bus (moja odluka) umjesto backend `GET /voice/state` — potvrda da je prihvatljiva.
