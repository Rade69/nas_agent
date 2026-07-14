# Voice Communication Reliability — R1 brief za Pi agenta

**Datum:** 2026-07-14
**Namjena:** praktičan implementacioni brief za Pi agenta
**Status ulaza:** R0 je završen; live hotfix nakon R0 je otkrio stvarne OpenAI greške i učinio ih vidljivim u UI-u. R1 sada smije raditi samo stabilizaciju lifecycle-a konekcije, bez širenja funkcionalnosti.

## Kratki cilj

Implementirati R1 stabilizaciju Realtime voice konekcije:

1. single-flight `connect()`,
2. connect timeout,
3. kontrolisani abort/cancel pokušaja povezivanja,
4. generation/session guard protiv stale async callback-ova,
5. osnovni transport health za PeerConnection/DataChannel,
6. deterministic test coverage.

Ovo nije puni rewrite voice sistema i nije novi provider sistem.

## Važno: kako se Pi mora ponašati tokom implementacije

Pi mora raditi usko, disciplinovano i fazno.

- Ne raditi R2/R3 unaprijed.
- Ne refaktorisati cijeli `src/lib/realtime.ts`.
- Ne mijenjati `electron/main.cjs`.
- Ne dodavati novu business logiku u Electron main.
- Ne uvoditi novi LLM provider.
- Ne mijenjati tool registry, permissions ili confirmation bridge osim ako test direktno pokaže da R1 promjena to lomi.
- Ne mijenjati UI dizajn osim minimalnog statusa koji je potreban za connect timeout/transport error.
- Ne mijenjati OpenAI session payload osim ako postoji konkretna runtime greška.
- Ne pogađati API parametre. Ako API vrati grešku, zapisati tačan error i napraviti minimalnu korekciju.
- Ne čistiti tuđe nekomitovane promjene.
- Prije rada obavezno:
  - `git status --short`
  - `git log -5 --oneline`
  - pročitati `docs/MIGRATION_PLAN.md`
  - pročitati `docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md`
  - pročitati `agent_reports/2026-07-13_voice-realtime-connect-hotfix.md` ako postoji

Ako se stanje koda razlikuje od plana, kod je jači dokaz od plana, ali `docs/MIGRATION_PLAN.md` mora biti ažuriran nakon implementacije.

## Trenutno poznato stanje

R0 je dao test harness i diagnostics osnovu.

Live hotfix nakon R0 je već adresirao:

- `connect()` error se više ne smije odmah prebrisati kroz `disconnect()` → `idle`.
- djelimično kreirani WebRTC resursi se moraju čistiti i kada `connect()` padne prije kraja.
- UI sada treba prikazivati stvarnu Realtime error poruku.
- OpenAI Realtime payload trenutno mora ostati kompatibilan sa stvarnim greškama:
  - koristiti `model: "gpt-realtime"`,
  - koristiti `output_modalities: ["audio"]`,
  - ne slati `session.modalities`,
  - ne slati `reasoning: { effort: "low" }`.

R1 ne smije vratiti stare greške.

## Primarni fajlovi

Očekivani glavni fajlovi:

- `src/lib/realtime.ts`
- `src/lib/__tests__/realtimeClient.test.ts`
- eventualno `src/App.tsx` samo ako je potrebno povezati novi status/error event
- eventualno `src/components/pixel/*` samo ako je potrebno minimalno prikazati novo stanje
- `docs/MIGRATION_PLAN.md`
- novi `agent_reports/YYYY-MM-DD_voice-realtime-r1.md`

Ne dirati:

- `electron/main.cjs`
- auth/billing/env fajlove
- legacy PowerShell computer-use toolove
- storage migracije
- tool permission sistem, osim ako R1 test ne dokaže direktan lom

## R1 funkcionalni zahtjevi

### 1. Single-flight connect

Problem koji treba riješiti:

Korisnik može kliknuti/pokrenuti voice connect više puta, ili UI može poslati više connect zahtjeva dok je prethodni još u toku. To pravi race condition: više PeerConnection-a, više DataChannel-a, više mic streamova i nejasno finalno stanje.

Očekivano ponašanje:

- Ako je `connect()` već u toku, drugi `connect()` ne smije pokrenuti novi WebRTC setup.
- Drugi poziv treba:
  - ili vratiti isti pending promise,
  - ili fail-soft vratiti trenutno stanje bez pravljenja nove konekcije.

Preporuka:

- Dodati privatni `connectPromise?: Promise<void>` ili ekvivalent.
- Na početku `connect()`:
  - ako postoji aktivni `connectPromise`, vratiti ga,
  - ako je već `connected`, ne praviti novu konekciju.
- U `finally` očistiti `connectPromise` samo ako pripada trenutnoj generaciji.

Testovi:

- dva paralelna `connect()` poziva pozivaju `createRealtimeToken` samo jednom;
- ne kreiraju se dva PeerConnection-a;
- finalno stanje nije duplirano/nestabilno.

### 2. Connect timeout

Problem:

WebRTC setup može ostati zaglavljen na token fetch-u, SDP exchange-u, ICE-u ili DataChannel open-u.

Očekivano ponašanje:

- `connect()` mora imati timeout.
- Timeout mora završiti pokušaj povezivanja, očistiti djelimične resurse i emitovati `error`.
- Error poruka mora biti jasna, npr. `Realtime povezivanje je isteklo`.

Preporuka:

- Uvesti konstantu, npr. `DEFAULT_CONNECT_TIMEOUT_MS = 30000`.
- U testovima koristiti dependency injection/fake timer ako već postoji DI seam iz R0.
- Timeout mora biti očišćen u svim uspješnim i neuspješnim granama.

Testovi:

- ako SDP/fetch/DataChannel open nikad ne završi, `connect()` završava timeout greškom;
- nakon timeout-a nema otvorenih mic trackova/PeerConnection-a;
- error ostaje zadnje emitovano stanje, ne prebacuje se odmah na `idle`.

### 3. Abort/cancel aktivnog pokušaja povezivanja

Problem:

Ako korisnik klikne Stop/Disconnect dok je `connect()` još u toku, stari async nastavak može kasnije završiti i vratiti klijenta u pogrešno stanje.

Očekivano ponašanje:

- `disconnect()` tokom connecting stanja mora poništiti aktivni pokušaj povezivanja.
- Stari `connect()` ne smije nakon toga emitovati `connected`.
- Resursi iz starog pokušaja moraju biti zatvoreni.

Preporuka:

- Uvesti `connectAbortController` gdje je moguće za fetch/token/SDP dio.
- Ako postoje operacije koje se ne mogu abortovati, koristiti generation/session guard.

Testovi:

- `connect()` krene, zatim `disconnect()` prije završetka;
- zakašnjeli promise iz starog connect-a ne smije prebaciti stanje u `connected`;
- state sequence završava očekivano, bez duplih idle/error oscilacija.

### 4. Generation/session guard

Problem:

Async callback-ovi iz stare konekcije mogu stići nakon nove konekcije ili nakon disconnect-a.

Očekivano ponašanje:

- Svaki connect pokušaj dobija monotonu generaciju/session id.
- Event listeneri i async nastavci provjeravaju da li još pripadaju aktivnoj generaciji prije emitovanja state/activity/transcript događaja.

Preporuka:

- Dodati privatni `connectionGeneration` counter.
- `connect()` inkrementira generaciju.
- `disconnect()` takođe invalidira trenutnu generaciju.
- Event handleri dobijaju lokalni `generation` i provjeravaju `if (generation !== this.connectionGeneration) return`.

Testovi:

- stari DataChannel event nakon disconnect-a se ignoriše;
- stari PeerConnection event nakon novog connect-a ne mijenja novo stanje;
- stale transcript/activity ne ulazi u novu sesiju.

### 5. Transport health

Problem:

Konekcija može biti uspostavljena, ali kasnije pukne: ICE failed/disconnected, DataChannel close/error, mic track ended.

Očekivano ponašanje:

- Klijent mora emitovati smisleno stanje kad transport pukne.
- Ne smije ostati vizuelno `connected/listening` ako je DataChannel zatvoren ili PeerConnection failed.

Minimalni R1 opseg:

- slušati `pc.connectionState` / `iceConnectionState` gdje je dostupno;
- slušati `dc.close` i `dc.error`;
- na fatalan transport prekid emitovati `error` ili `idle` sa jasnom activity porukom;
- očistiti resurse.

Ne raditi još:

- automatski reconnect/backoff kao puni sistem;
- kompleksni network quality UI;
- provider failover.

Testovi:

- DataChannel `close` poslije `connected` mijenja stanje iz connected/listening u error/idle;
- PeerConnection `failed` zatvara resurse;
- stale event iz stare generacije se ignoriše.

### 6. Error klasifikacija

R1 ne mora praviti veliki error framework, ali treba dodati nekoliko prepoznatljivih poruka:

- quota/billing:
  - ako error sadrži `insufficient_quota`, prikazati korisniku da je OpenAI quota/billing problem;
- timeout:
  - jasna poruka da je povezivanje isteklo;
- permission/microphone:
  - jasna poruka ako browser/Electron odbije mikrofon;
- generic:
  - fallback sa originalnom porukom, sanitizovan ako sadrži osjetljive podatke.

Ne logovati API ključeve, bearer tokene, SDP blobove ili cijele auth headere.

## Minimalni acceptance criteria

R1 je završen tek kada važi sve ispod:

- paralelni `connect()` pozivi ne prave više konekcija;
- connect timeout postoji i testiran je;
- `disconnect()` tokom connecting stanja ne dozvoljava stale `connected`;
- stale DataChannel/PeerConnection callback-ovi se ignorišu;
- fatalan transport prekid ne ostavlja UI u lažnom connected stanju;
- OpenAI `insufficient_quota` poruka se pretvara u korisniku razumljiv error;
- `test:voice` prolazi;
- `typecheck` prolazi;
- `build` prolazi ili je jasno dokumentovan postojeći nevezani warning;
- `git diff --check` prolazi;
- GitNexus `detect_changes` je pokrenut prije commita;
- `docs/MIGRATION_PLAN.md` je ažuriran;
- `agent_reports/YYYY-MM-DD_voice-realtime-r1.md` je dodat.

## Preporučeni redoslijed rada

### Korak 0 — provjera stanja

Pi prvo radi:

```bash
git status --short
git log -5 --oneline
```

Zatim čita:

```text
docs/MIGRATION_PLAN.md
docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md
agent_reports/2026-07-13_voice-realtime-connect-hotfix.md
```

Ako neki fajl ne postoji, nastaviti bez panike, ali zabilježiti u agent reportu.

### Korak 1 — impact analysis

Prije izmjene `RickyRealtimeClient.connect` i `disconnect`, pokrenuti GitNexus impact:

```text
target: RickyRealtimeClient.connect
direction: upstream

target: RickyRealtimeClient.disconnect
direction: upstream
```

Ako `disconnect` opet bude HIGH, ne zaustavlja se automatski, ali Pi mora nastaviti minimalno i zapisati rizik u reportu.

### Korak 2 — single-flight i timeout

Prvo implementirati samo:

- `connectPromise`,
- timeout,
- cleanup u `finally`.

Odmah dodati testove.

### Korak 3 — abort i generation guard

Zatim dodati:

- `connectionGeneration`,
- invalidaciju na disconnect,
- guard u async nastavcima i event handlerima.

Odmah dodati testove.

### Korak 4 — transport health

Dodati minimalne listenere:

- DataChannel close/error,
- PeerConnection failed/disconnected/closed.

Odmah dodati testove.

### Korak 5 — error mapping

Dodati minimalnu klasifikaciju poruka, posebno za:

```text
insufficient_quota
quota
billing
microphone
permission
timeout
```

Ne praviti veliki error sistem ako nije potreban.

### Korak 6 — dokumentacija i report

Ažurirati:

- `docs/MIGRATION_PLAN.md`
- `agent_reports/YYYY-MM-DD_voice-realtime-r1.md`

Report mora sadržati:

- šta je promijenjeno,
- zašto,
- GitNexus impact sažetak,
- test komande i rezultat,
- šta nije urađeno u R1,
- preporuku za R2.

## Test komande

Minimalno:

```bash
npm.cmd run test:voice
npm.cmd run typecheck
npm.cmd run build
git diff --check
```

Ako se dira Python backend ili realtime endpoint:

```bash
python -m pytest -q tests/test_realtime.py
```

Ako se dira Electron handler:

```bash
node --check electron/ipc_handlers/realtime.cjs
```

Prije commita:

```text
gitnexus_detect_changes(scope="all")
```

## Šta eksplicitno nije R1

Ove stvari ne raditi u ovom zadatku:

- automatski reconnect/backoff,
- fallback na drugi LLM provider,
- lokalni Whisper/Ollama/Piper voice engine,
- novi settings ekran za providere,
- veći UI redesign,
- promjene confirmation sistema,
- migracija legacy computer-use toolova,
- promjene u `electron/main.cjs`.

Ako Pi primijeti da je neka od ovih stvari potrebna, treba to zapisati kao R2/R3 preporuku, a ne implementirati u R1.

## R2 preporuka nakon R1

Nakon R1 logičan sljedeći paket je:

- kontrolisani reconnect/backoff,
- voice transport health indicator,
- user-facing diagnostics panel,
- provider abstraction za budući jeftiniji/non-OpenAI voice mode,
- detaljnije mjerenje latencije i failure rate-a.

Ali R2 ne počinjati dok R1 nije stabilan i pregledan.
