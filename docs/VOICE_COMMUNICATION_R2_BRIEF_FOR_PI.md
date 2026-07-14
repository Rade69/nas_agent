# Voice Communication Reliability — R2 brief za Pi agenta

**Datum:** 2026-07-14
**Namjena:** implementacioni brief za Pi agenta
**Status ulaza:** R1 je implementiran, review-an, komitovan i ručno potvrđen — glasovna komunikacija je uspješno ostvarena.

## Kratki cilj

R2 treba da učini postojeću OpenAI Realtime glasovnu komunikaciju otpornijom na prekide, bez uvođenja novih providera i bez velikog refaktora.

R2 obim:

1. kontrolisani reconnect/backoff,
2. outbound event queue za DataChannel,
3. jasniji transport/reconnect status u UI-u,
4. testovi za reconnect/queue/fail-soft scenarije,
5. update `docs/MIGRATION_PLAN.md` i novi `agent_reports/YYYY-MM-DD_voice-realtime-r2.md`.

Ovo nije R3 i nije provider abstraction.

## Kako se Pi mora ponašati tokom implementacije

Pi mora raditi usko i konzervativno.

- Ne uvoditi novi LLM/STT/TTS provider.
- Ne mijenjati OpenAI Realtime session payload osim ako se pojavi konkretna runtime greška.
- Ne mijenjati `electron/main.cjs`.
- Ne raditi veći UI redesign.
- Ne mijenjati confirmation bridge, permission engine ili tool registry osim ako test direktno pokaže da R2 promjena lomi postojeći tok.
- Ne uvoditi beskonačni reconnect.
- Ne reconnectovati nakon korisničkog Stop/Disconnect.
- Ne reconnectovati na quota/billing/auth/API-key greške.
- Ne gutati greške tiho — korisnik mora vidjeti smislen status.
- Ne commitovati `.env`, logove, lokalne baze, `node_modules`, `dist`, niti `nul`.

Prije izmjena Pi mora uraditi:

```bash
git status --short
git log -5 --oneline
```

Zatim pročitati:

```text
docs/MIGRATION_PLAN.md
docs/VOICE_COMMUNICATION_R1_BRIEF_FOR_PI.md
agent_reports/2026-07-14_voice-realtime-r1.md
```

Ako se plan i kod razlikuju, kod je jači dokaz, ali `docs/MIGRATION_PLAN.md` mora biti ažuriran na kraju.

## Trenutno poznato stanje poslije R1

R1 je već riješio:

- single-flight `connect()`,
- connect timeout,
- AbortController disconnect/cancel tokom povezivanja,
- `connectionGeneration` guard protiv stale callback-ova,
- osnovni transport health za PeerConnection/DataChannel,
- user-friendly error klasifikaciju,
- 197 voice testova.

R2 ne smije pokvariti ove garancije.

## Primarni fajlovi

Očekivani glavni fajlovi:

- `src/lib/realtime.ts`
- `src/lib/__tests__/realtimeClient.test.ts`
- eventualno `src/App.tsx` samo za novi status/reconnect signal
- eventualno `src/components/pixel/*` samo za minimalni prikaz reconnect/queue statusa
- `docs/MIGRATION_PLAN.md`
- `agent_reports/YYYY-MM-DD_voice-realtime-r2.md`

Ne dirati:

- `electron/main.cjs`
- backend provider/config fajlove, osim ako se ne pokaže direktna potreba
- tool permission sistem
- confirmation bridge
- legacy computer-use toolove

## R2 funkcionalni zahtjevi

### 1. Kontrolisani reconnect/backoff

Problem:

R1 detektuje transport prekid, ali ne pokušava kontrolisano vratiti sesiju. U realnoj upotrebi WebRTC/DataChannel može puknuti zbog mreže, sleep/wake, VPN-a, Wi-Fi prekida ili kratkog OpenAI/transport problema.

Očekivano ponašanje:

- Ako je konekcija već bila uspješno uspostavljena i transport pukne zbog network/transport razloga, klijent smije pokušati reconnect.
- Reconnect mora biti ograničen.
- Reconnect ne smije raditi ako je korisnik ručno pritisnuo Stop/Disconnect.
- Reconnect ne smije raditi za trajne/account greške.

Preporučena pravila:

```text
maxReconnectAttempts = 3
baseDelayMs = 1000
delays: 1s, 2s, 4s
jitter: mali, npr. 0-250ms
```

Reconnectovati samo za:

- PeerConnection `failed`,
- neočekivani DataChannel `close`,
- DataChannel `error`,
- network-ish fetch/WebRTC greške gdje klasifikacija nije quota/auth/billing/microphone.

Ne reconnectovati za:

- korisnički Stop/Disconnect,
- `insufficient_quota`,
- billing/payment greške,
- `401`/unauthorized/API key problem,
- microphone permission/not found,
- explicit abort,
- connect timeout dok korisnik ručno prekida.

Status poruke:

```text
Veza je prekinuta. Pokušavam ponovo 1/3...
Veza je prekinuta. Pokušavam ponovo 2/3...
Veza je prekinuta. Pokušavam ponovo 3/3...
Reconnect nije uspio. Pokreni glas ponovo.
```

Testovi:

- transport close nakon connected pokreće reconnect pokušaj;
- nakon 3 neuspjela pokušaja više nema novih pokušaja;
- korisnički `disconnect()` ne pokreće reconnect;
- quota/billing/auth greška ne pokreće reconnect;
- uspješan reconnect vraća stanje u connected/idle.

### 2. Razlikovati korisnički disconnect od transport failure-a

Problem:

`disconnect()` sada čisti resurse i vraća idle. R2 mora znati da li je prekid namjeran ili neočekivan.

Preporuka:

- Uvesti interni flag tipa `manualDisconnectRequested`.
- `disconnect()` ga postavlja na `true`.
- Interni transport failure handleri ga ne postavljaju.
- Reconnect handler provjerava taj flag.

Paziti:

- novi `connect()` mora resetovati flag;
- stale generation callback-ovi ne smiju pokrenuti reconnect.

Testovi:

- `disconnect()` zatvara DataChannel, ali close event koji se desi zbog tog zatvaranja ne smije pokrenuti reconnect;
- close event iz stare generacije ne smije pokrenuti reconnect.

### 3. Outbound event queue za DataChannel

Problem:

`sendEvent()` trenutno šalje samo ako je `dc.readyState === "open"`. Ako event dođe dok DataChannel još nije otvoren ili je privremeno u reconnect-u, event se može izgubiti.

R2 cilj:

Minimalan queue koji čuva važne outgoing evente dok kanal nije spreman.

Queue treba koristiti za:

- `response.create`,
- `conversation.item.create` za tool output,
- `session.update` za dictation mode,
- tekstualni prompt evente iz `sendText()`.

Preporučeni dizajn:

```ts
type QueuedRealtimeEvent = {
  event: Record<string, unknown>;
  createdAt: number;
  reason: string;
};
```

Pravila:

- max queue size: npr. 50 eventova;
- max event age: npr. 10 sekundi;
- flush samo kada je DataChannel `open`;
- ako queue overflow-a, fail-soft: odbaci najstariji ili odbij novi uz status;
- nikad ne queue-ovati beskonačno;
- nikad ne queue-ovati ako je korisnik ručno disconnectovao;
- nikad ne queue-ovati nakon finalne fatal greške.

Preporuka:

- postojeći `sendEvent()` ostaje javni interni ulaz;
- dodati privatni `enqueueOrSendEvent(event, reason)` ili proširiti `sendEvent()`;
- `dc.open` handler poziva `flushOutboundQueue()`;
- reconnect success takođe poziva `flushOutboundQueue()`.

Testovi:

- event poslat dok DataChannel nije open ulazi u queue;
- `open` flushuje queue redom;
- queue ne šalje evente nakon manual disconnect;
- queue poštuje max size;
- stale generation ne flushuje queue u pogrešnu sesiju.

### 4. Jasniji UI/status za reconnect i queue

Problem:

Korisnik treba razlikovati:

- normalno povezivanje,
- transport prekid,
- reconnect pokušaj,
- konačni reconnect failure,
- trajnu billing/auth/quota grešku.

Minimalno očekivanje:

- status string iz `RealtimeCallbacks.onStatus` mora biti dovoljan da UI pokaže šta se dešava;
- ako već postoji Activity timeline, dodati activity event za reconnect pokušaje;
- ne raditi veliki UI redesign.

Primjeri statusa:

```text
Veza je prekinuta.
Pokušavam ponovo 1/3...
Ponovo povezano.
Reconnect nije uspio. Pokreni glas ponovo.
OpenAI kvota je potrošena. Provjeri stanje naloga i billing.
```

Testovi:

- reconnect attempt emituje status;
- final failure emituje error status;
- successful reconnect emituje success/status activity.

### 5. Reconnect policy helper

Da kod ne postane pun `if` grananja, poželjno je dodati mali privatni helper:

```ts
private shouldReconnect(reason: RealtimeDisconnectReason): boolean
```

Ili, ako je jednostavnije:

```ts
private isPermanentConnectError(error: unknown): boolean
```

Minimalne kategorije:

- transient transport/network,
- manual disconnect,
- quota/billing/auth,
- microphone/permission,
- timeout,
- unknown.

R2 ne mora praviti veliki error framework, ali reconnect odluka mora biti čitljiva i testirana.

## Acceptance criteria

R2 je završen tek kada važi sve:

- Neočekivani transport prekid nakon uspješne konekcije pokreće najviše 3 reconnect pokušaja.
- Manual Stop/Disconnect nikad ne pokreće reconnect.
- Quota/billing/auth/microphone greške nikad ne pokreću reconnect.
- Reconnect pokušaji imaju backoff.
- Reconnect status je vidljiv korisniku.
- Ako reconnect uspije, korisnik može nastaviti razgovor bez restartovanja aplikacije.
- Ako reconnect ne uspije, sistem završava u jasnom error/idle stanju i ne vrti beskonačno.
- Outbound event queue čuva važne evente dok DataChannel nije open.
- Queue ima max size i/ili max age.
- Queue se ne flushuje u stale sesiju.
- `npm.cmd run test:voice` prolazi.
- `npm.cmd run typecheck` prolazi.
- `npm.cmd run build` prolazi ili postojeći warning jasno dokumentovan.
- `git diff --check` prolazi.
- Ako se dira Electron handler: `node --check electron/ipc_handlers/realtime.cjs`.
- Ako se dira Python backend: `python -m pytest -q python_backend/tests/test_realtime.py`.
- GitNexus `detect_changes(scope="all")` ili `scope="staged"` pokrenut prije commita.
- `docs/MIGRATION_PLAN.md` ažuriran.
- `agent_reports/YYYY-MM-DD_voice-realtime-r2.md` dodat.

## Preporučeni redoslijed rada

### Korak 0 — stanje i impact

Pi prvo:

```bash
git status --short
git log -5 --oneline
```

Zatim GitNexus impact prije izmjene centralnih simbola:

```text
RickyRealtimeClient.connect
RickyRealtimeClient.disconnect
RickyRealtimeClient.sendEvent
RickyRealtimeClient.handleServerEvent
```

Ako `disconnect()` ili `sendEvent()` ispadnu HIGH/CRITICAL, nastaviti samo sa minimalnim, testiranim promjenama i zapisati rizik u report.

### Korak 1 — reconnect policy

Dodati minimalne interne state varijable i helper:

- broj pokušaja,
- max pokušaja,
- manual disconnect flag,
- reconnect timer,
- helper koji odlučuje da li reconnect smije krenuti.

Dodati testove prije širenja.

### Korak 2 — transport failure → schedule reconnect

Spojiti postojeće R1 transport failure handlere na `scheduleReconnect()`.

Paziti:

- cleanup ne smije okinuti reconnect ako cleanup dolazi iz manual disconnect-a;
- stale generation se ignoriše;
- reconnect timer se čisti na manual disconnect.

### Korak 3 — reconnect execution

Reconnect treba koristiti postojeći `connect()` put ako je moguće.

Paziti:

- ne praviti paralelni reconnect ako je `connectPromise` već aktivan;
- ne resetovati brojač pokušaja pogrešno;
- uspješan reconnect resetuje attempts.

### Korak 4 — outbound queue

Dodati queue i testove.

Početi minimalno:

- queue event ako DC nije open, ali konekcija nije manualno ugašena;
- flush na DC open;
- max size.

Tek onda dodati max age ako je jednostavno.

### Korak 5 — UI/status

Minimalno status/activity kroz postojeće callback-e.

Ne praviti novi ekran.

### Korak 6 — dokumentacija i report

Ažurirati:

- `docs/MIGRATION_PLAN.md`
- `agent_reports/YYYY-MM-DD_voice-realtime-r2.md`

Report mora sadržati:

- šta je promijenjeno,
- šta nije urađeno,
- GitNexus impact sažetak,
- test komande i rezultate,
- ručni smoke test checklist.

## Test komande

Minimalno:

```bash
npm.cmd run test:voice
npm.cmd run typecheck
npm.cmd run build
git diff --check
```

Ako je diran Electron realtime handler:

```bash
node --check electron/ipc_handlers/realtime.cjs
```

Ako je diran Python backend:

```bash
python -m pytest -q python_backend/tests/test_realtime.py
```

Prije commita:

```text
gitnexus_detect_changes(scope="all")
```

## Ručni smoke test nakon R2

Korisnik ili review agent treba provjeriti:

1. Normalan start voice sesije.
2. Normalan razgovor.
3. Stop tokom povezivanja — nema reconnect-a.
4. Stop tokom aktivne sesije — nema reconnect-a.
5. Simuliran DataChannel close/transport prekid — reconnect krene.
6. Nakon uspješnog reconnect-a razgovor se nastavlja.
7. Quota/billing/auth greška ne pokušava reconnect.
8. UI/status jasno kaže šta se desilo.

## Šta eksplicitno nije R2

Ne raditi:

- lokalni Whisper/Ollama/Piper voice engine,
- provider abstraction,
- automatski fallback na drugi LLM,
- kompleksan diagnostics panel,
- novi settings ekran za reconnect policy,
- veliki UI redesign,
- promjene permission/confirmation sistema,
- migraciju legacy computer-use toolova,
- promjene u `electron/main.cjs`.

Ako Pi vidi da je nešto od ovoga potrebno, neka zapiše kao R3/R4 preporuku, ali ne implementira u R2.

## R3 prijedlog poslije R2

Ako R2 bude stabilan, sljedeći smislen paket je:

- fail-safe tool lifecycle,
- per-tool timeout,
- idempotency za `call_id`,
- bolji diagnostics panel,
- eventualno provider abstraction za jeftiniji/non-OpenAI voice mode.
