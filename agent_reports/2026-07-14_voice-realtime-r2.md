# Voice Realtime R2 — Kontrolisani reconnect, outbound event queue, manual disconnect guard

**Datum:** 2026-07-14
**Agent:** pi
**Scope:** R2 stabilizacija — reconnect/backoff i outbound queue prema `docs/VOICE_COMMUNICATION_R2_BRIEF_FOR_PI.md`
**Predloženi commit naslov:** `fix(voice): add controlled reconnect, outbound queue, and manual disconnect guard (R2)`

## Prethodno stanje

R1 (Codex, 2026-07-14) je već obezbijedio:
- single-flight `connect()`, connect timeout, abort/cancel, generation guard
- transport health detekciju (PeerConnection failed/disconnected/closed, DataChannel close/error)
- error klasifikaciju (quota, billing, microphone, timeout…)

Ali R1 je transport failure tretirao kao terminalnu grešku — odmah je emitovao `error` stanje bez pokušaja oporavka. Takođe nije postojao outbound event queue — ako bi DataChannel privremeno bio zatvoren (npr. tokom reconnect-a), `sendEvent` bi tiho odbacio event.

## GitNexus impact

- `RickyRealtimeClient.disconnect`: HIGH → R2 dodaje `manualDisconnectRequested` flag + `_cleanupReconnectState` + `_cleanupOutboundQueue`
- `RickyRealtimeClient.sendEvent`: dodata outbound queue logika (enqueue ako DC nije open, ali sesija nije manualno ugašena)
- Novi simboli: `_handleTransportFailure`, `_shouldReconnect`, `_scheduleReconnect`, `_executeReconnect`, `_flushOutboundQueue`, `_enqueueEvent`, `_cleanupOutboundQueue`, `_cleanupReconnectState`
- `detect_changes` (GitNexus CLI): HIGH — 4 fajla, 34 simbola, 12 pogođenih procesa (očekivano za centralni voice modul)

## Šta je promijenjeno

### `src/lib/realtime.ts` (188 insertions, 25 deletions)

1. **Nove konstante** — `MAX_RECONNECT_ATTEMPTS = 3`, `RECONNECT_BASE_DELAY_MS = 1000`, `RECONNECT_JITTER_MS = 250`, `MAX_OUTBOUND_QUEUE_SIZE = 50`, `MAX_OUTBOUND_QUEUE_AGE_MS = 10000`

2. **Nova polja**:
   - `reconnectAttempts` — brojač pokušaja (resetuje se samo na uspješan DC open, ne u `connect()`)
   - `manualDisconnectRequested` — flag koji razlikuje korisnički Stop od transport failure-a
   - `reconnectTimer` — timer za backoff kašnjenje
   - `outboundQueue` — red za evente koji čekaju DataChannel

3. **`connect()`** — više ne resetuje `reconnectAttempts` (samo DC open handler to radi); resetuje `manualDisconnectRequested` i `outboundQueue`

4. **`disconnect()`** — postavlja `manualDisconnectRequested = true`, poziva `_cleanupReconnectState()` i `_cleanupOutboundQueue()`

5. **Transport failure handleri** — oba mjesta (`pc.onconnectionstatechange` i DataChannel `close`/`error`) sada delegiraju na `_handleTransportFailure(reason)` umjesto direktnog emitovanja error-a

6. **`_handleTransportFailure(reason)`** — čisti resurse, zatim:
   - Ako je `manualDisconnectRequested` → `idle` (nema greške, korisnik je sam prekinuo)
   - Ako `_shouldReconnect(reason)` → `_scheduleReconnect(reason)`
   - Inače → terminalni `error`

7. **`_shouldReconnect(reason)`** — vraća `true` samo za transient transport greške (`failed`, `disconnected`, `dc-close`, `dc-error`) i ako je `reconnectAttempts < MAX_RECONNECT_ATTEMPTS`

8. **`_transportFailureMessage(reason)`** — mapira interne šifre na korisnički razumljive poruke

9. **`_scheduleReconnect(reason)`** — inkrementira `reconnectAttempts`, računa eksponencijalni backoff sa jitterom (1s/2s/4s ± 250ms), emituje status `"Pokušavam ponovo N/3…"`, zakazuje `_executeReconnect`

10. **`_executeReconnect()`** — poziva `connect({ preserveOutboundQueue: true })` (isti standardni put bez brisanja queue-a), resetuje `reconnectAttempts = 0` na uspjeh, flushuje outbound queue; ako reconnect setup ne uspije, zakazuje sljedeći pokušaj do limita

11. **`_cleanupReconnectState()`** — čisti reconnect timer i resetuje `reconnectAttempts`

12. **`sendEvent()`** — proširen: ako DC nije `open`, ali sesija nije manualno ugašena, enqueue-uje event

13. **`_flushOutboundQueue()`** — šalje sve queued evente kroz DC, odbacuje starije od `MAX_OUTBOUND_QUEUE_AGE_MS`; poziva se na DC open i reconnect success

14. **`_enqueueEvent(event)`** — dodaje event u queue sa timestampom; ako je queue pun, odbacuje najstariji

15. **`_cleanupOutboundQueue()`** — briše queue (poziva se na manual disconnect i terminal error)

### `src/lib/__tests__/realtimeClient.test.ts` (164 insertions, 6 deletions)

- Ažurirana 2 postojeća R1 testa (transport health → sada provjeravaju reconnect umjesto direktnog error-a)
- Dodato 7 novih R2 testova nakon Codex review korekcije:
  - Manual disconnect ne pokreće reconnect
  - Reconnect emituje status sa brojačem pokušaja
  - Reconnect status sadrži "Pokušavam ponovo 1/3"
  - Neuspjeli reconnect pokušaj zakazuje sljedeći pokušaj
  - Outbound queue se flushuje na DC open
  - Outbound queue se čisti na manual disconnect
  - Queued event preživljava reconnect i flushuje se u novi DataChannel
- Helper `dcSpyDeps()` izdvojen na nivo fajla za ponovno korištenje

## Codex review korekcija

Nakon Pi implementacije Codex review je našao dva R2 rubna slučaja:

1. Queue se brisao na reconnect pokušaju jer je `_executeReconnect()` pozivao standardni `connect()`, a `connect()` je čistio outbound queue.
2. Ako reconnect setup sam padne (npr. network/fetch problem tokom novog SDP poziva), nije se zakazivao sljedeći pokušaj do limita od 3.

Popravka:

- `connect()` sada prima opcionalni `preserveOutboundQueue` flag;
- `_executeReconnect()` koristi `connect({ preserveOutboundQueue: true })`;
- `sendEvent()` smije queue-ovati evente i tokom reconnect delay-a (`reconnectTimer`) ili aktivnog connect pokušaja (`connectPromise`);
- dodan `_handleReconnectAttemptFailure()` koji zakazuje sljedeći pokušaj ili emituje terminalnu reconnect grešku;
- DNS/network greške iz token/SDP puta (`getaddrinfo failed`, `Errno 11001`, `ENOTFOUND`, `EAI_AGAIN`, `fetch failed`, `Network down`) mapiraju se u korisničku poruku: "Nema internet konekcije ili DNS ne radi. Provjeri mrežu i pokušaj ponovo.";
- dodana 3 review testa za ove scenarije.

### `docs/MIGRATION_PLAN.md`

Ažuriran tracker — dodat R2 status u Backlog/Future Epics red "Voice Communication Reliability".

## Zašto

- **Reconnect**: WebRTC/DataChannel može puknuti zbog mreže, sleep/wake, VPN-a, Wi-Fi prekida. Bez reconnect-a korisnik mora ručno restartovati cijelu aplikaciju.
- **Manual disconnect guard**: Ako korisnik klikne Stop, sistem ne smije pokušavati reconnect — to bi bilo zbunjujuće i nepotrebno.
- **Backoff**: Eksponencijalni backoff sprječava agresivno ponavljanje koje bi moglo preopteretiti mrežu ili OpenAI API.
- **Outbound queue**: Ako DataChannel privremeno nije dostupan (npr. tokom reconnect-a), važni eventi (tool output, response.create) ne smiju biti tiho odbačeni.
- **UI/status**: Korisnik treba znati šta se dešava — da li sistem pokušava reconnect ili je definitivno otkazao.

## Šta nije urađeno (ostaje za R3)

- Fail-safe tool lifecycle (per-call timeout, aktivni pozivi u Set-u, idempotency za `call_id`)
- Serijski event queue sa garancijom redoslijeda i determinističkim ishodom
- Detaljniji diagnostics panel
- Provider abstraction za jeftiniji/non-OpenAI voice mode
- VAD profili i push-to-talk
- Promjene u `electron/main.cjs`

## Verifikacija

```powershell
npm.cmd run test:voice   → 205/205 passed
npm.cmd run typecheck    → clean
npm.cmd run check        → clean
npm.cmd run build        → success (postojeći chunk-size warning, nevezan)
git diff --check         → bez whitespace grešaka
```

## Ručni smoke test checklist

- [ ] Normalan start voice sesije
- [ ] Normalan razgovor
- [ ] Stop tokom povezivanja — nema reconnect-a
- [ ] Stop tokom aktivne sesije — nema reconnect-a
- [ ] Simuliran DataChannel close/transport prekid — reconnect krene
- [ ] Nakon uspješnog reconnect-a razgovor se nastavlja
- [ ] Quota/billing/auth greška ne pokušava reconnect
- [ ] UI/status jasno kaže šta se desilo

## Preostali rizik

- `disconnect()` je HIGH impact simbol (4 call site-a u `App.tsx`) — R2 dodaje 2 poziva (`_cleanupReconnectState`, `_cleanupOutboundQueue`) i jedan flag (`manualDisconnectRequested`), ali ne mijenja postojeći cleanup tok.
- Backoff testiran samo indirektno (kroz status poruke) — stvarni timing zavisi od `setTimeout` implementacije.
- Outbound queue sada preživljava reconnect pokušaj i flushuje se u novi DataChannel. I dalje ostaje R3 rizik: nema punog serijskog event queue-a sa end-to-end potvrdom isporuke.

## R3 preporuka

- Fail-safe tool lifecycle: per-call timeout, aktivni pozivi u `Set<string>`, idempotency za `call_id`
- Serijski event queue sa determinističkim redoslijedom
- Detaljniji voice transport health UI indikator
