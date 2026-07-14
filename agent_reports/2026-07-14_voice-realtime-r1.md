# Voice Realtime R1 — Single-flight, timeout, generation guard, transport health

**Datum:** 2026-07-14
**Agent:** pi
**Scope:** R1 stabilizacija Realtime voice konekcije prema `docs/VOICE_COMMUNICATION_R1_BRIEF_FOR_PI.md`
**Predloženi commit naslov:** `fix(voice): add single-flight connect, timeout, generation guard, and transport health (R1)`

## Prethodno stanje

R0 (test harness + diagnostics) i live-connect hotfix (Codex, 2026-07-13) su već bili primijenjeni. Ključni problemi prije R1:

- `connect()` nije imao single-flight zaštitu — više poziva je moglo otvoriti više PeerConnection-a
- Nije postojao connect timeout — WebRTC setup je mogao ostati zaglavljen
- `disconnect()` tokom connecting stanja nije abortovao aktivni pokušaj
- Async callback-ovi iz stare konekcije su mogli emitovati `connected` nakon `disconnect()`
- Nije bilo transport health detekcije (DataChannel close/error, PeerConnection failed)
- Greške nisu bile klasifikovane za korisnika (quota, microphone, timeout, itd.)

## GitNexus impact

- `RickyRealtimeClient.connect`: LOW u grafu → R1 ga značajno mijenja (single-flight wrapper + delegacija na `_connectInternal`)
- `RickyRealtimeClient.disconnect`: HIGH, direktno utiče na `App` (4 call site-a), `bumpIdleTimer`, `connect` → R1 dodaje AbortController abort + generation invalidation
- `RickyRealtimeClient.handleServerEvent`: dodan `generation` parametar → poziva se iz `_doWebrtcConnect` (novo)
- `RickyRealtimeClient.executeFunctionCalls`: dodan `generation` parametar → poziva se iz `handleServerEvent`
- `detect_changes` (GitNexus CLI): CRITICAL — 11 fajlova, 40 simbola, 20 pogođenih procesa (očekivano za centralni voice modul)

## Šta je promijenjeno

### `src/lib/realtime.ts` (316 insertions, 79 deletions iz diff-a)

1. **Nova polja** — `connectPromise`, `connectionGeneration`, `connectAbortController`
2. **Nova konstanta** — `DEFAULT_CONNECT_TIMEOUT_MS = 30000`
3. **`connect()` prepisan** — single-flight guard (`connectPromise` + `dc.readyState === "open"`), delegacija na `_connectInternal()`
4. **`_connectInternal()`** — novi privatni metod: postavlja connecting stanje, pokreće `Promise.race` između `_doWebrtcConnect` i `_timeoutPromise`, hvata greške kroz `_classifyError`
5. **`_doWebrtcConnect()`** — izvučen iz starog `connect()`: core WebRTC setup + transport health listeneri + generation guard provjere na async tačkama
6. **`_timeoutPromise()`** — odbijajući promise sa abort cleanup-om; provjerava `generation === this.connectionGeneration` prije reject-a
7. **`_classifyError()`** — klasifikuje greške u korisnički razumljive srpske poruke:
   - `insufficient_quota`/`quota` → "OpenAI kvota je potrošena"
   - `billing`/`payment` → "OpenAI billing problem"
   - `microphone`/`NotAllowedError`/`Permission denied` → "Mikrofon nije dostupan"
   - `notfound`/`not found` → "Mikrofon nije pronađen"
   - `unauthorized`/`401` → "Autentikacija nije uspjela"
   - `timeout`/`isteklo` → "Realtime povezivanje je isteklo"
   - `abort`/`prekinuto` → "Povezivanje je prekinuto"
   - Fallback: truncate na 200 karaktera
8. **`disconnect()` roziren** — dodato `connectAbortController?.abort()`, `connectionGeneration++`, `connectPromise = null`
9. **`handleServerEvent(raw, generation)`** — dodati `generation` parametar + guard na početku: `if (generation !== this.connectionGeneration) return;`
10. **`executeFunctionCalls(items, generation)`** — dodati `generation` parametar + guard na početku i prije `response.create`
11. **Transport health** — `pc.onconnectionstatechange` detektuje `failed`/`disconnected`/`closed`; DataChannel `close`/`error` handleri emituju error stanje

### `src/lib/__tests__/realtimeClient.test.ts` (383 insertions)

14 novih R1 testova nakon Codex review korekcije:

| Grupa | Testovi |
|---|---|
| Single-flight | 2 testa — paralelni connect dijeli isti pokušaj, connect kad je već connected je no-op |
| Timeout | 1 test — never-resolving fetch + immediate setTimeout → timeout error |
| Abort/cancel | 3 testa — disconnect tokom connecting abortuje + stale connect completion ne emituje connected + `connect()` se završava i kada setup promise-i sami ne settle-uju |
| Generation guard | 1 test — stale DataChannel message nakon disconnect-a se ignoriše |
| Transport health | 2 testa — DataChannel close i error nakon connected emituju error |
| Error klasifikacija | 5 testova — insufficient_quota, NotAllowedError, NotFoundError, billing, generic fallback |

Postojeća 2 testa ažurirana za novu `_classifyError` semantiku.

Ukupno: **197 testova** (183 postojećih + 14 novih).

## Codex review korekcija

Nakon Pi implementacije Codex review je našao jedan R1 rubni slučaj:

```text
disconnect() tokom connect-a abortuje signal,
ali _timeoutPromise() je na abort samo čistio timer i nije reject/resolve-ovao promise.
```

Ako bi neka setup operacija koja ne prima AbortSignal ostala pending (npr. token IPC ili mic prompt), originalni `connect()` promise je mogao ostati pending zauvijek. Popravka:

- dodan eksplicitni abort reject u `_timeoutPromise()`;
- dodano centralno čišćenje connect timeout timera/listenera;
- dodan test `disconnect resolves an in-flight connect even when setup promises do not settle`.

## Zašto

Svaka R1 stavka adresira konkretan failure mode:

- **Single-flight**: sprječava duple PeerConnection-e, DataChannel-e i mic stream-ove kad korisnik brzo klikne na voice dugme
- **Timeout**: sprječava vječno `connecting` stanje kad token fetch, SDP exchange, ICE ili DataChannel open zaglave
- **Abort/cancel**: sprječava da zakašnjeli `connect()` emitovati `connected` nakon što je korisnik već kliknuo Stop
- **Generation guard**: sprječava stale DataChannel/PeerConnection callback-ove da mijenjaju stanje nove sesije
- **Transport health**: sprječava lažno `connected` stanje kad DataChannel pukne ili PeerConnection padne
- **Error klasifikacija**: daje korisniku razumljive poruke umjesto sirovih engleskih grešaka

## Šta nije urađeno (ostaje za R2/R3)

- Automatski reconnect/backoff
- Fallback na drugi LLM provider
- Serijski event queue i pouzdan outbound transport
- Fail-safe tool lifecycle (aktivni pozivi, per-call wrapper)
- VAD profili i push-to-talk
- Lokalni Whisper/Ollama/Piper voice engine
- UI promjene osim onih koje su već postojale iz hotfix-a
- Promjene u `electron/main.cjs`

## Verifikacija

```powershell
npm.cmd run test:voice   → 197/197 passed
npm.cmd run typecheck    → clean
npm.cmd run check        → clean
npm.cmd run build        → success (postojeći chunk-size warning, nevezan)
git diff --check         → bez whitespace grešaka (CRLF upozorenja za ranije dokumente)
python -m pytest -q python_backend/tests/test_realtime.py → 3/3 passed, 1 postojeći Starlette warning
node --check electron/ipc_handlers/realtime.cjs → clean (nepromijenjeno)
```

## Preostali rizik

- `disconnect()` je HIGH impact simbol sa 4 call site-a u `App.tsx`. R1 promjene su minimalne: samo dodaju abort + generation invalidation, ne mijenjaju postojeći cleanup tok. Ipak, ručni smoke test je neophodan.
- R1 ne dira `electron/main.cjs`, `App.tsx` logiku, tool lifecycle, confirmation/cancellation — ovi slojevi su netaknuti.
- GitNexus detect_changes je CRITICAL — očekivano za centralni voice modul.

## R2 preporuka

Nakon R1 logičan sljedeći paket:

- Kontrolisani reconnect/backoff (do 3 pokušaja, eksponencijalni backoff sa jitterom)
- Serijski event queue za pouzdan outbound transport
- Detaljniji voice transport health indicator u UI-u
- Fail-safe tool lifecycle (per-call timeout, aktivni pozivi u Set-u, idempotency za call_id)
