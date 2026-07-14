# Voice Realtime connect hotfix

**Datum:** 2026-07-13
**Agent:** Codex
**Scope:** uski live-connect hotfix nakon R0, nije puni R1
**Predloženi commit naslov:** `fix(voice): preserve realtime connection errors`

## Kontekst

Korisnik je prijavio da aplikacija i dalje nema glasovnu komunikaciju sa agentom. R0 je bio samo test harness i diagnostics temelj, bez promjene live ponašanja.

Pregledan je stvarni lanac: `App.connect()` -> `RickyRealtimeClient.connect()` -> `window.ricky.createRealtimeToken()` -> Electron `handleRealtimeCreateToken()` -> Python `/realtime/session` -> OpenAI Realtime WebRTC SDP.

## GitNexus impact

- `RickyRealtimeClient.connect`: LOW u grafu.
- `RickyRealtimeClient.disconnect`: HIGH, direktno utiče na `App`, `bumpIdleTimer`, `connect`, posredno `sendText`.
- `handleRealtimeCreateToken`: LOW u grafu.

Zbog HIGH nalaza na `disconnect()` promjena je namjerno minimalna: javni `disconnect()` ugovor ostaje isti; dodat je interni cleanup put koji `connect()` koristi u error grani bez emitovanja `idle`.

## Šta je promijenjeno

1. `src/lib/realtime.ts`
   - `connect()` sada dodjeljuje `this.pc`/`this.dc` čim se resursi kreiraju, da ih cleanup može zatvoriti i u djelimično uspjelom povezivanju.
   - Dodan `cleanupConnectionResources()` za zatvaranje DataChannel-a, PeerConnection-a, mic trackova, idle timera i audio meter-a.
   - `disconnect()` i dalje vraća javno stanje na `idle`.
   - `connect()` error grana više ne poziva javni `disconnect()`, pa se `error` stanje i status poruka više ne brišu odmah.

2. `electron/ipc_handlers/realtime.cjs`
   - Realtime model prebačen sa `gpt-realtime-2` na GA alias `gpt-realtime`.
   - `output_modalities: ["audio"]` je zadržan za `/realtime/client_secrets`, jer je stvarni OpenAI odgovor vratio `400 unknown_parameter` za `session.modalities`.
   - `reasoning: { effort: "low" }` je uklonjen iz Realtime session payload-a, jer je stvarni OpenAI odgovor vratio `400 invalid_value` / `Unsupported option for this model`.

3. `src/App.tsx`, `src/components/pixel/*`, `src/styles/11-pixel-shell.css`
   - `App` sada čuva Realtime status poruku umjesto da je odbacuje.
   - Pixel top bar i idle ekran prikazuju konkretnu poruku greške kada je `voiceState === "error"`.
   - Error poruka se upisuje i u Activity listu kao `Realtime povezivanje nije uspjelo`.

4. `src/lib/__tests__/realtimeClient.test.ts`
   - Testovi sada provjeravaju da je `error` zadnje emitovano stanje kad fetch/SDP povezivanje padne.

5. `docs/MIGRATION_PLAN.md`
   - Tracker ažuriran da razlikuje ovaj hotfix od punog R1 paketa.

## Zašto

Stari tok je radio ovo:

```text
connect error -> emit error -> disconnect() -> emit idle
```

Zbog toga korisnik nije mogao vidjeti stvarni razlog kvara. Ako token, model, mikrofon ili SDP padnu, UI izgleda kao da se ništa nije desilo.

Stvarni OpenAI odgovor iz korisnikove aplikacije potvrdio je da `/v1/realtime/client_secrets` u ovom payload-u ne prihvata `session.modalities`: vraća `400 unknown_parameter`. Zato je audio modality vraćen na postojeći `output_modalities: ["audio"]`, a zadržan je sigurniji model alias `gpt-realtime`.

Drugi stvarni OpenAI odgovor zatim je potvrdio da trenutni `gpt-realtime` session ne prihvata `reasoning` opciju u ovom payload-u: vraća `400 invalid_value` / `Unsupported option for this model`. Zato je `reasoning` uklonjen umjesto da se pogađa druga vrijednost.

## Šta nije urađeno

- Nije implementiran puni R1 single-flight connect.
- Nije dodat connect timeout.
- Nije dodat AbortController.
- Nije implementiran transport health za ICE/DataChannel close/error.
- Nije dodat reconnect/backoff.
- Nije mijenjan tool-call lifecycle.
- Nije diran `electron/main.cjs`.

## Verifikacija

- `npm.cmd run test:voice` -> 183/183 prolazi.
- `npm.cmd run typecheck` -> prolazi.
- `npm.cmd run build` -> prolazi, uz postojeći Vite chunk-size warning.
- `npm.cmd run check` -> prolazi.
- `node --check electron/ipc_handlers/realtime.cjs` -> prolazi.
- `python -m pytest -q tests/test_realtime.py` -> 3/3 prolazi, uz postojeća 2 warninga.
- `git diff --check` -> bez whitespace grešaka; Git i dalje prijavljuje CRLF upozorenja za ranije promijenjene dokumente.
- `gitnexus_detect_changes(scope="all")` -> CRITICAL za ukupni dirty tree zbog kombinacije ranijih nevezanih promjena i centralnog voice/UI toka; hotfix opseg je izdvojen u gore navedenim fajlovima.

## Preostali rizik

Ovaj hotfix može odmah popraviti slučaj gdje je problem bio zastarjeli model/session payload. Ako i dalje padne, UI sada mora pokazati konkretnu Realtime error poruku. Ta poruka je sljedeći dokaz za dijagnostiku.

Ovo ne garantuje stabilnu dugu glasovnu sesiju. Za to i dalje treba puni R1/R2: single-flight, timeout, generation guard, transport health i stale-session zaštita.
