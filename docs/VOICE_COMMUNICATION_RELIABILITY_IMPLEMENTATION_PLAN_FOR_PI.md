# Plan implementacije pouzdane glasovne komunikacije za pi agenta

**Projekat:** RileyJarvis Windows Hybrid (Naš-agent)
**Namjena:** operativni plan koji pi agent realizuje u kodu
**Datum:** 13. jul 2026.
**Status:** R0 završen i verifikovan 2026-07-13; R1 nije odobren niti započet
**Osnovna analiza:** [VOICE_COMMUNICATION_RELIABILITY_ANALYSIS_2026-07-13.md](./VOICE_COMMUNICATION_RELIABILITY_ANALYSIS_2026-07-13.md)

## 0. Trenutno odobreni opseg — samo R0

**Pi agent je trenutno ovlašten da realizuje isključivo paket R0: test harness i redigovanu observability osnovu.** Ostatak dokumenta opisuje buduće pakete radi arhitektonskog kontinuiteta, ali njihovo postojanje u planu nije dozvola za implementaciju.

Pi mora eksplicitno raditi ovim redoslijedom:

1. pročitati sve obavezne projektne dokumente;
2. provjeriti `git status`, `git log` i postojeći diff;
3. prijaviti kolizije i vlasništvo nekomitovanih izmjena;
4. pokrenuti GitNexus impact prije izmjene svakog postojećeg simbola;
5. realizovati samo R0;
6. pokrenuti R0 testove, typecheck, build i relevantne Python testove;
7. pokrenuti `gitnexus_detect_changes`;
8. napisati agent report i prikazati korisniku diff/stat i rezultate testova;
9. **zaustaviti rad i čekati pregled i novu eksplicitnu dozvolu korisnika.**

Pi ne smije protumačiti izraze poput „nastavi po planu“, sopstvenu procjenu da je R0 uspješan ili preostali token/vremenski budžet kao dozvolu za R1. Dozvola za R1 mora doći kao nova, jasna korisnička instrukcija, na primjer: **„Pregledao sam R0. Odobravam implementaciju R1.“**

### Obavezna stop-pravila tokom R0

Pi mora odmah stati i prijaviti korisniku stanje ako:

- Git working tree sadrži izmjene u R0 fajlovima čije vlasništvo nije potvrđeno;
- GitNexus vrati HIGH ili CRITICAL rizik;
- realizacija zahtijeva izmjenu `disconnect`, `sendEvent`, `executeFunctionCalls`, Python audio toka ili `electron/main.cjs`;
- test harness zahtijeva proizvodnu behavioral promjenu umjesto test seam-a;
- mora se dodati nova dependency koja nije Vitest ili minimalno opravdana alternativa;
- bilo koji postojeći test, typecheck ili build padne;
- primijeti sigurnosnu regresiju, curenje osjetljivog sadržaja ili mogućnost logovanja transkripta;
- opseg R0 više nije moguće zadržati bez ulaska u R1.

U tim slučajevima pi ne smije „usput“ popraviti susjedni problem. Treba navesti dokaz, pogođene fajlove, GitNexus blast radius i najmanju preporučenu odluku, pa čekati odgovor.

### Šta je dozvoljeno u R0

- dodavanje minimalnog TypeScript test runnera i `test:voice` skripte;
- fake/mock WebRTC, DataChannel, MediaStream i timer objekti za testove;
- dependency-injection seam koji ne mijenja podrazumijevano produkcijsko ponašanje;
- čisti, redigovani diagnostics ring-buffer modul;
- unit testovi za test seam i diagnostics;
- potrebni tipovi i kratki file-header komentari;
- dokumentovanje i izvještavanje.

### Šta nije dozvoljeno u R0

- nova connection state mašina;
- single-flight behavioral promjena `connect()` metode;
- reconnect, backoff ili network recovery;
- izmjena VAD/model/transcription konfiguracije;
- izmjena tool-call ponašanja;
- izmjena confirmation/cancellation toka;
- novi korisnički UI ili i18n poruke osim ako su nužne samo za neaktivni test seam, što treba posebno opravdati;
- promjena Python realtime endpoint ponašanja;
- refactor nepovezanih voice/UI modula;
- automatski commit ili prelazak na R1.

Ako je za testabilnost potrebna mala izmjena konstruktora `RickyRealtimeClient`, ona mora biti unazad kompatibilna: postojeći `new RickyRealtimeClient(callbacks)` poziv mora nastaviti raditi bez izmjene ponašanja.

## 0.1. R0 review — obavezne popravke prije R1

**Ova sekcija je izvršena kao R0 review korekcija. R0 je završen, ali završetak R0 nije dozvola za R1.** Sljedeći agent ovu sekciju treba koristiti kao audit kriterij: ne smije ponavljati iste greške, ne smije širiti opseg i ne smije započeti R1 bez nove eksplicitne korisničke instrukcije.

### Blokirajući nalaz: diagnostics mora biti fail-closed

Trenutni `createDiagnosticsRing().push(event)` direktno čuva događaj, dok je `redactDiagnosticEvent(event)` samo opcioni helper. To znači da budući pozivalac može zaobići redakciju i sačuvati transkript, tool argument/rezultat, API ključ, URL sa tokenom ili osjetljivu putanju.

Pi mora:

1. učiniti sanitizaciju obaveznom unutar `push()` puta; pozivalac ne smije moći preskočiti redakciju;
2. primijeniti validaciju na **sve kategorije**, ne samo `event` i `tool`;
3. validirati/sanitizovati sva tekstualna polja, uključujući `name` i `code`;
4. dozvoliti samo kratke stabilne tehničke identifikatore iz ograničenog skupa znakova i dužine;
5. nikada ne čuvati raw dinamički tekst kao zamjenu kada validacija padne — koristiti fiksne vrijednosti poput `redacted` i `UNSAFE_FIELD`;
6. osigurati da snapshot ne omogućava naknadnu mutaciju sačuvanih događaja; zamrznut niz nije dovoljan ako su objekti u njemu i dalje mutabilni;
7. ispraviti file-header i komentare koji trenutno tvrde da je diagnostics već integrisan u `RickyRealtimeClient`: u R0 modul još nije integrisan u produkcijski tok.

### Obavezni negativni sigurnosni testovi

Postojeći test koji samo provjerava da hardkodirani bezbjedni naziv ne sadrži riječ `hello` nije dokaz zaštite. Pi ga mora zamijeniti stvarnim pokušajima unosa osjetljivog sadržaja kroz javni `push()` API.

Testovi moraju najmanje pokušati ubaciti:

- običan transkript i tekst sa razmacima;
- JSON payload i tool argumente/rezultate;
- Windows apsolutnu putanju, UNC putanju i `file://` vrijednost;
- URL sa query tokenom ili authorization vrijednošću;
- sadržaj nalik API ključu/Bearer tokenu;
- osjetljivi sadržaj u `code`, ne samo u `name`;
- svaki od prethodnih primjera kroz svaku diagnostics kategoriju;
- objekat koji se mutira nakon `push()` i objekat dobijen kroz `snapshot()`.

Acceptance: nijedan osjetljivi literal iz ulaza ne smije postojati u rezultatu `snapshot()`.

### Minimalan dependency i DI cleanup

Pi mora:

- ukloniti `@vitest/ui` iz `package.json` i lockfile-a jer se UI runner ne koristi u `test:voice`;
- zadržati `jsdom` samo ako testovi stvarno zavise od DOM okruženja i to navesti u reportu;
- povezati `now` i `randomUUID` kroz DI na stvarna mjesta upotrebe ako je to moguće bez behavioral promjene, ili ih ukloniti iz R0 DI ugovora dok ne postanu potrebni;
- ne širiti DI seam, ne refaktorisati voice lifecycle i ne mijenjati ponašanje `connect()`, `disconnect()`, alata, confirmationa ili cancellationa.

### Tracker, izvještaj i izolacija promjena

- `docs/MIGRATION_PLAN.md` ne smije tvrditi da je R0 konačno odobren prije ponovnog review-a. Dok korekcije nisu prihvaćene, status treba biti „R0 korekcije nakon review-a“ ili ekvivalentno.
- Ažurirati `agent_reports/2026-07-13_voice-reliability-r0-test-harness.md` stvarnim brojem R0 fajlova/simbola i jasno odvojiti R0 diff od ostalih izmjena u shared tree-u.
- Ne uključivati tuđe izmjene iz `AGENTS.md`, `CLAUDE.md`, Python modula, drugih dokumenata ili drugih epica u R0 commit.
- Ne commitovati bez eksplicitne korisničke dozvole.

### Ponovna verifikacija R0

Pi mora pokrenuti i prijaviti:

```powershell
npm.cmd run test:voice
npm.cmd run typecheck
npm.cmd run build
cd python_backend
python -m pytest -q tests/test_realtime.py
```

Zatim:

```powershell
git diff --check
git status --short
git diff --stat
```

Na kraju pokrenuti `gitnexus_detect_changes(scope="all")`, ali u izvještaju posebno navesti koji nalazi pripadaju R0, a koji postojećem shared dirty tree-u.

### Obavezno zaustavljanje

Nakon korekcija pi mora prikazati:

- tačan R0 diff/stat;
- rezultate svih navedenih testova;
- dokaz da se svaki osjetljivi testni literal uklanja prije čuvanja;
- ažurirani agent report i tracker status;
- GitNexus nalaz i razdvajanje tuđih izmjena.

Potom mora **zaustaviti rad i čekati novi Codex/korisnički review**. Završetak ovih korekcija nije dozvola za R1.

## 1. Cilj i arhitektonska odluka

Stabilizovati glasovnu komunikaciju bez zamjene postojeće arhitekture:

- React/Electron renderer ostaje vlasnik mikrofona, WebRTC-a, VAD/STT/TTS sesije i audio reprodukcije.
- `src/lib/realtime.ts` ostaje primarni voice engine.
- Python ostaje vlasnik ephemeral credentiala, lokalnih alata, dozvola, potvrda, cancellationa, storagea i agent runtimea.
- `electron/main.cjs` ostaje shell/IPC sloj i ne dobija novu poslovnu logiku.
- OpenAI Realtime WebRTC se ne zamjenjuje custom Python audio pipelineom.

Krajnji rezultat mora ukloniti silent failure scenarije, spriječiti duple sesije, detektovati prekid transporta, oporaviti se od privremenih mrežnih problema i garantovati da svaki tool call završi kontrolisanim rezultatom.

## 2. Stroge granice

Pi agent ne smije:

- raditi veliki rewrite `realtime.ts` u jednom potezu;
- prebacivati audio u Python;
- dodavati business/voice logic u `electron/main.cjs`;
- mijenjati model i lifecycle u istom commitu;
- uvoditi beskonačni reconnect;
- automatski ponavljati ne-idempotentne tool pozive;
- logovati audio, transkript, tool argumente/rezultate, ključeve ili osjetljive putanje;
- uklanjati confirmation, permission, cancellation ili prompt-injection zaštite;
- koristiti find-and-replace za simbole;
- početi na shared dirty tree-u bez razrješenja vlasništva izmjena;
- proglasiti fazu završenom samo zato što typecheck prolazi;
- commitovati bez eksplicitne korisničke dozvole.

## 3. Obavezni protokol prije prvog editovanja

### 3.1. Shared tree

Izvršiti:

```powershell
git status --short
git log -5 --oneline
git diff -- src/lib/realtime.ts src/App.tsx electron/ipc_handlers/realtime.cjs electron/main.cjs
```

U vrijeme pisanja plana postoje nekomitovane izmjene u collision fajlovima:

- `src/lib/realtime.ts`;
- `src/App.tsx`;
- `electron/ipc_handlers/realtime.cjs`;
- `electron/main.cjs`;
- `electron/core/realtimeToolSpecs.cjs`;
- `src/vite-env.d.ts`.

Pi mora dobiti čist commit/branch, eksplicitno preuzeti postojeći tree ili koristiti zaseban worktree. Zabranjeni su `git reset --hard`, `git checkout --` i brisanje tuđih izmjena.

### 3.2. Izvori istine

Potpuno pročitati:

- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/MIGRATION_PLAN.md`;
- `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md`;
- osnovnu analizu ovog plana;
- `docs/SECURITY_AND_VOICE_HARDENING_BACKLOG.md`;
- voice/confirmation/cancellation/dictation agent reports.

### 3.3. GitNexus

Prije izmjene svakog postojećeg simbola pokrenuti upstream impact:

```text
connect
disconnect
handleServerEvent
executeFunctionCalls
sendEvent
routeRealtimeEvent
App
```

Već potvrđen blast radius:

| Simbol | Rizik | Direktno pogođeno |
|---|---:|---|
| `disconnect` | HIGH | `App`, `bumpIdleTimer`, `connect`, posredno `sendText` |
| `sendEvent` | HIGH | `sendText`, `setDictationMode`, `executeFunctionCalls`, `returnToolOutput` |
| `handleServerEvent` | LOW u grafu | centralni connect/event tok |
| `executeFunctionCalls` | LOW u grafu | `handleServerEvent`, connect procesi |
| `routeRealtimeEvent` | LOW | `handleServerEvent` |

Za HIGH/CRITICAL pi mora stati, prijaviti blast radius i dobiti potvrdu. Prije commita obavezan je `gitnexus_detect_changes(scope="all")`.

## 4. Paketi realizacije

| Paket | Sadržaj | Rizik |
|---|---|---:|
| R0 | test harness i redigovana observability osnova | nizak/srednji |
| R1 | single-flight connect, cleanup, timeout i state model | visok |
| R2 | transport health i stale-session zaštita | visok |
| R3 | pouzdan outbound transport i serijski event queue | visok |
| R4 | fail-safe tool lifecycle | visok |
| R5 | kontrolisan reconnect i audio health | visok |
| R6 | VAD profili, push-to-talk i model/transcription spike | eksperimentalan |

Svaki paket se implementira i pregleda zasebno. Ne spajati R1–R5.

## 5. Ciljna struktura

`RickyRealtimeClient` ostaje javni facade radi manjeg blast radiusa. Čistu logiku izdvojiti samo kada time postaje testabilna:

```text
src/lib/
  realtime.ts
  realtimeTypes.ts
  realtimeEventRouter.ts
  realtimeEventHelpers.ts
  realtimeSessionState.ts
  realtimeReconnectPolicy.ts
  realtimeDiagnostics.ts
  __tests__/
    realtimeSessionState.test.ts
    realtimeReconnectPolicy.test.ts
    realtimeEventRouter.test.ts
    realtimeClient.test.ts
```

Novi i značajno mijenjani kod fajlovi moraju imati kratak header komentar prema `CLAUDE.md`.

## 6. R0 — test harness i instrumentacija

### Cilj

Omogućiti determinističko testiranje bez pravog mikrofona i mreže, prije behavioral izmjena.

### Test runner

Preferirati Vitest jer projekat već koristi Vite/TypeScript. Nova dependency mora biti obrazložena. Ne uvoditi težak browser automation framework.

### Dependency injection

Zadržati postojeći konstruktor kompatibilnim, uz opcione dependencies:

```ts
type RealtimeClientDeps = {
  createPeerConnection: () => RTCPeerConnection;
  getUserMedia: (...) => Promise<MediaStream>;
  fetch: typeof fetch;
  createAudioElement: () => HTMLAudioElement;
  now: () => number;
  setTimeout: ...;
  clearTimeout: ...;
  random: () => number;
};
```

Produkcija koristi browser default vrijednosti, testovi fake objekte.

### Redigovani diagnostics

Ring buffer, najviše oko 300 tehničkih događaja:

```ts
type RealtimeDiagnosticEvent = {
  at: number;
  generation: number;
  category: "connection" | "ice" | "data_channel" | "audio_input" | "audio_output" | "event" | "tool";
  name: string;
  durationMs?: number;
  code?: string;
};
```

Zabranjeni su raw payload, transcript, delta, tool sadržaj, token i putanje.

### R0 testovi

- ring buffer odbacuje najstariji zapis;
- diagnostics tip ne prihvata sadržaj razgovora;
- fake peer/data channel/media stream pokreću osnovni connect test;
- callback ugovor ostaje kompatibilan;
- produkcijske default dependencies i typecheck rade.

### R0 acceptance

- postoji `test:voice` skripta;
- testovi ne traže mikrofon ni mrežu;
- typecheck/build/Python realtime testovi prolaze;
- produkcijsko ponašanje nije namjerno promijenjeno.

## 7. R1 — lifecycle, single-flight i cleanup

### State mašina

Interna stanja:

```text
idle
requesting_permission
minting_token
negotiating
connected
reconnecting
disconnecting
failed
```

Ako se proširuje javni `RickyConnectionState`, impact analizirati UI i i18n pozivaoce. Tranzicije centralizovati u čistu funkciju.

### Single-flight connect

Dodati konceptualno:

```ts
private connectPromise: Promise<void> | null = null;
private generation = 0;
private desiredActive = false;
```

Pravila:

- prvi connect postavlja željeno aktivno stanje i kreira Promise;
- sljedeći connect tokom povezivanja vraća isti Promise;
- connect dok je connected je no-op;
- disconnect invalidira generation i abortuje connect;
- connectPromise se čisti u `finally`.

### Session scope

Resursi postaju dostupni cleanupu odmah:

```ts
type ActiveRealtimeSession = {
  generation: number;
  pc: RTCPeerConnection;
  dc: RTCDataChannel | null;
  micStream: MediaStream | null;
  audioElement: HTMLAudioElement;
  abortController: AbortController;
  manualStop: boolean;
};
```

### Idempotentan cleanup

Redoslijed:

1. odvojiti handlere;
2. abortovati fetch;
3. zatvoriti DataChannel;
4. zatvoriti peer;
5. zaustaviti mic trackove;
6. pause audio, ukloniti `srcObject`;
7. stopirati meter/AudioContext;
8. očistiti timere;
9. ukloniti reference samo ako generation odgovara.

Odvojiti `cleanupResources`, `disconnect(reason)` i `fail(error)`. Greška se ne smije odmah pretvoriti u idle.

### Timeout i error codeovi

Ukupni connect deadline: početno 20 sekundi. Tipovi:

```text
MIC_PERMISSION_DENIED
MIC_NOT_FOUND
TOKEN_REQUEST_FAILED
SDP_TIMEOUT
SDP_REJECTED
WEBRTC_NEGOTIATION_FAILED
MANUAL_ABORT
UNKNOWN_CONNECT_ERROR
```

### R1 testovi

- dva connecta → jedan peer/mic/session;
- Stop tokom tokena ili SDP-a abortuje sve;
- timeout → failed, ne idle;
- permission denied nema reconnect;
- cleanup je idempotentan;
- stari cleanup ne briše novu sesiju;
- svaki mic track se zaustavlja.

## 8. R2 — transport health i stale-session zaštita

Dodati handlere za:

- `connectionstatechange`;
- `iceconnectionstatechange`;
- DataChannel `open/close/error`;
- mic track `mute/unmute/ended`;
- `devicechange`;
- renderer `online/offline`.

Pravila:

- connected tek kada je DataChannel otvoren i peer zdrav;
- kratko disconnected dobija grace period;
- failed pokreće cleanup i retry odluku;
- manual close nije greška;
- mic ended bez Stop-a je input greška;
- offline odlaže retry.

Svaki handler zatvara generation i prije mutacije provjerava da li je još aktivan.

Testovi:

- stale event poslije reconnecta se ignoriše;
- DataChannel close i ICE failed se detektuju;
- kratko disconnected→connected ne duplira sesiju;
- mic ended daje jasan problem;
- manual close nema reconnect;
- cleanup uklanja listenere.

## 9. R3 — pouzdan event transport

### `sendEvent`

Ovo je HIGH-risk simbol; ponoviti impact i tražiti potvrdu.

Novi ugovor vraća eksplicitan rezultat:

```text
sent
queued
rejected_not_connected
rejected_stale_session
send_failed
```

Važni događaji dobijaju `event_id`. Ne redati sve naslijepo:

- `session.update` može čekati open samo u istoj generaciji;
- `function_call_output` ne ide u novu sesiju;
- `response.create` se ne ponavlja automatski;
- stale poruke se odbijaju.

### Serijski event queue

State-changing događaji idu kroz Promise queue koji se oporavlja nakon exceptiona. Vizuelni audio meter može ostati izvan samo ako ne mijenja conversation state.

Proširiti interne tipove potrebnim poljima:

- `event_id`;
- `response.id/status`;
- `item_id`;
- `content_index`;
- `call_id`.

Testovi:

- zatvoren kanal ne gubi poruku tiho;
- dictation update prije opena ima definisan ishod;
- response.done eventi se obrađuju redom;
- jedan event exception ne ubija queue;
- server error se korelira preko event_id;
- transkripti se slažu po item_id.

## 10. R4 — fail-safe tool lifecycle

### Aktivni pozivi

Ciljno zamijeniti globalni boolean:

```ts
private activeToolCalls = new Set<string>();
```

Ako je prevelik scope, prvo zaštititi batch `try/finally`, ali Set ostaje cilj.

### Per-call wrapper

```ts
executeOneFunctionCall(item, generation): Promise<ToolCallOutcome>
```

Mora:

1. validirati call ID, naziv i argumente;
2. provjeriti katalog;
3. označiti call aktivnim;
4. izvršiti postojeći Electron/Python bridge;
5. obraditi confirmation bez prekida batcha;
6. poslati tačno jedan sanitizovan output;
7. u finally očistiti aktivno stanje;
8. vratiti da li treba response.create.

Kontrolisana greška modelu ne sadrži stack/path/raw body.

### Timeout/cancellation/idempotency

- Python executor ostaje autoritativan;
- renderer/IPC dobija malo duži watchdog;
- timeout pokušava postojeći cancellation;
- kill-switch otkazuje voice i backend;
- običan voice interruption ne otkazuje automatski alat;
- reconnect ne ponavlja acting tool;
- završeni call_id se ne izvršava dvaput.

Testovi:

- executeTool rejection/timeout vraća završni output;
- malformed args i unknown tool ne ruše queue;
- confirmation ne preskače ostatak batcha;
- više callova svaki dobija tačno jedan output;
- dupli call_id se ne izvršava;
- stale generation ne šalje output u novu sesiju;
- active state se uvijek čisti.

## 11. R5 — reconnect i audio health

### Retry klasifikacija

Čista funkcija vraća:

```text
retry_now
retry_when_online
do_not_retry
```

Retry: ICE failed, neočekivan DC close, privremeni network problem.
Bez retrya: mic permission/not found, invalid key/config, Stop, kill-switch, idle timeout, app quit.

### Backoff

Početno:

```text
500 ms → 1500 ms → 4000 ms
```

Mali jitter, najviše tri pokušaja. Svaki pokušaj ima novu generation i novi ephemeral token. Ne prenosi outbound queue i ne ponavlja tool.

### Mic health

Lokalni RMS meter bez snimanja audio podataka. Pratiti track muted/unmuted/ended i devicechange. UI razlikuje track problem od tišine; sama tišina nije dokaz kvara.

### Output health

Audio element je eksplicitno vlasništvo sessiona. Pratiti `play()` Promise, `playing/error/stalled` i output track ended. Ako transkript/audio event stigne, a playback ne počne, prikazati output problem.

Testovi:

- retry najviše tri puta;
- Stop prekida backoff;
- offline čeka online;
- fatalna greška nema retry;
- svaki pokušaj minta novi token;
- tool se ne ponavlja;
- autoplay rejection i track ended su vidljivi.

## 12. R6 — VAD, push-to-talk i modeli

Radi se tek nakon stabilnih R1–R5.

### VAD profili

Samo nakon evala:

```text
natural       → semantic_vad medium
patient       → semantic_vad low
fast_commands → semantic_vad high
noisy         → izmjeren server_vad profil
```

Default ostaje sadašnji medium dok mjerenje ne pokaže bolje.

### Push-to-talk

Opcionalni fallback. Prije implementacije ponovo provjeriti aktuelne OpenAI evente. Ne improvizovati API iz memorije. PTT mora očistiti odgovarajuće buffere, kontrolisati prekid odgovora i završiti turn bez kvara hands-free režima.

### Model A/B

Odvojeno testirati trenutni `gpt-realtime-2` i aktuelni 2.1 model, ako je dostupan. Isti prompt/alati/VAD; najmanje 30–50 srpskih turnova; mjeriti latenciju, tool accuracy, interruption, prazne odgovore i trošak.

### Transcription spike

Procijeniti `gpt-realtime-whisper` protiv `whisper-1` uz provjeru kompatibilnosti sa conversational sessionom i VAD-om. Testirati latinicu, ćirilicu, imena, brojeve i code-switching. Produkcija se ne mijenja bez mjerljivog poboljšanja.

## 13. UI zahtjevi

Minimalno prikazati:

- mic permission;
- token/povezivanje;
- connected;
- reconnect pokušaj N/3;
- mic/device problem;
- transport problem;
- tool traje;
- čeka potvrdu;
- output playback problem;
- failed sa „Pokušaj ponovo“.

Ne zatrpavati osnovni UI tehničkim detaljima. Companion orb koristi postojeći voice-state bridge, bez paralelne state mašine.

Sve nove poruke imaju i18n za `sr-Latn/en/de/es/fr`. Srpska latinica je autoritativna; ostali prevodi mogu biti best-effort uz napomenu u reportu.

## 14. Python scope

Dozvoljeno ako je potrebno:

- precizniji strukturirani error code iz `/realtime/session`;
- redigovane timeout/upstream greške;
- korelacijski request ID bez sadržaja;
- testovi da tajne ne izlaze;
- provjera tool timeout/cancellation ugovora.

Zabranjeno:

- audio ingest/VAD/STT/TTS u Pythonu;
- novi put mimo permission/tool executora;
- standardni OpenAI ključ u rendereru ili Electronu.

## 15. Sigurnost koju treba sačuvati

- standardni ključ samo u Pythonu;
- renderer samo ephemeral credential;
- backend local auth obavezan;
- svaki tool prolazi permission/cancellation;
- confirmation IDs ostaju single-use i vezani za payload;
- `external_content_seen` voice kontekst ostaje;
- kill-switch prekida mic i backend izvršavanja;
- diagnostics nema sadržaj;
- reconnect ne zaobilazi potvrdu niti ponavlja radnju.

## 16. Verifikacija

Poslije svakog paketa:

```powershell
npm.cmd run test:voice
npm.cmd run typecheck
npm.cmd run check
npm.cmd run build
cd python_backend
python -m pytest -q tests/test_realtime.py
```

Ako se diraju tool/cancellation moduli, cijeli Python suite. Na kraju R1–R5 `npm.cmd run quality`.

Prije commita:

```powershell
git diff --check
git status --short
git diff --stat
```

Zatim `gitnexus_detect_changes(scope="all")`.

## 17. Ručni smoke matrix

Korisnik mora potvrditi:

1. normalan connect i razgovorni turn;
2. brzi dvostruki klik ne duplira odgovor;
3. Stop odmah gasi mic;
4. companion i glavni prozor kontrolišu istu sesiju;
5. prekid interneta se detektuje;
6. povrat mreže oporavlja ili jasno završava failed;
7. odbijena mic dozvola je jasna;
8. uklanjanje USB/Bluetooth mikrofona se detektuje;
9. govor prekida Rickyja bez kvara sljedećeg turna;
10. tool greška daje objašnjenje umjesto tišine;
11. confirmation approve/reject radi;
12. dictation entry/exit ne gubi session.update;
13. kill-switch prekida glas i backend;
14. 30-minutna sesija ne gomila peerove/timere/AudioContext.

## 18. Rollback

- R0 je behavior-neutral.
- R1 zadržava javni facade.
- R2 handleri su izolovani.
- R3 koristi adapter prema starim pozivaocima.
- R4 ne dira Python permission engine.
- R5 reconnect počinje iza feature flaga/default off do smoke testa.
- R6 VAD/model/PTT su konfigurabilni i odvojeni.

Ne skrivati osnovni cleanup/error correctness iza trajnog feature flaga.

## 19. Tracker, report i commit

`MIGRATION_PLAN.md` trenutno nema aktivnu numerisanu fazu za ovaj epic. Pi ne izmišlja broj. U prvom implementacionom commitu dodaje/ažurira Backlog/Future Epic red „Voice Communication Reliability“, označavajući samo stvarni paket. Epic nije gotov dok R1–R5 i smoke nisu završeni.

Za svaki paket:

```text
agent_reports/YYYY-MM-DD_voice-reliability-rN-slug.md
```

Sekcije prema `CLAUDE.md`: Datum, Scope, GitNexus impact, Šta/Zašto/Kako, Šta nije dirano, Verifikacija, Rizici, Follow-up, Korisnička potvrda.

Predloženi commit naslovi:

```text
test(voice): add deterministic realtime client harness
fix(voice): make realtime connect lifecycle single-flight
fix(voice): detect transport failure and ignore stale sessions
fix(voice): serialize realtime events and surface send failures
fix(voice): guarantee terminal output for every tool call
fix(voice): add bounded reconnect and audio health signals
feat(voice): add evaluated VAD and push-to-talk options
```

Bez commita dok korisnik eksplicitno ne odobri.

## 20. Definition of Done

Epic je gotov kada:

- dupli connect ne može otvoriti dvije sesije;
- connect ima deadline/abort;
- svaki djelimični resurs se čisti;
- WebRTC/ICE/DC/mic prekid se detektuje;
- stale eventi ne mijenjaju novu sesiju;
- outbound poruke ne nestaju tiho;
- state-changing eventi su deterministički;
- svaki tool call dobija tačno jedan terminalni output;
- exception/timeout ne zaglavljuje razgovor;
- reconnect je ograničen i ne ponavlja acting tool;
- Stop/kill-switch gase mic i backend;
- playback kvar se razlikuje od modelskog;
- TS voice testovi pokrivaju failure scenarije;
- `npm run quality` prolazi;
- GitNexus nema neočekivan scope;
- tracker/report su usklađeni;
- korisnik potvrdi ručni smoke matrix.

## 21. Ready-to-paste početni prompt za pi

```text
Radiš na RileyJarvis Windows Hybrid repo-u. Realizuješ
docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md.

Prvo potpuno pročitaj AGENTS.md, CLAUDE.md, docs/MIGRATION_PLAN.md,
docs/ARCHITECTURE_VOICE_FIRST_REVISED.md,
docs/VOICE_COMMUNICATION_RELIABILITY_ANALYSIS_2026-07-13.md i ovaj plan.

Ne edituj prije git status/log/diff provjere i prijave svih nekomitovanih
izmjena. Shared tree koriste drugi agenti. Ne briši i ne prepisuj tuđe promjene.

Arhitektonska granica: src/lib/realtime.ts ostaje WebRTC voice engine.
Ne prebacuj audio/VAD/STT/TTS u Python. Ne dodaj business logic u
electron/main.cjs.

Radi samo jedan paket, počevši od R0. Prije izmjene svakog postojećeg simbola
pokreni GitNexus upstream impact. Za HIGH/CRITICAL stani, prijavi blast radius
i čekaj korisničku potvrdu. Nakon paketa pokreni testove,
gitnexus_detect_changes, napiši agent report i uskladi MIGRATION_PLAN tracker
u istom commitu kada commit bude odobren.

Ne pravi veliki rewrite. Ne mijenjaj model/VAD dok R1-R5 nije završeno.
Ne commituj bez eksplicitne korisničke dozvole.

Sada uradi samo R0: test harness i redigovani diagnostics temelj. Na kraju
prijavi fajlove, testove, blast radius, ograničenja i ručni test. Ne prelazi
na R1 bez nove potvrde.
```

## 22. Preporuka za rad sa pi agentom

Pi je racionalan izbor ako dobija samo jedan paket odjednom. Ušteda cijene nestaje ako dobije svih sedam paketa i napravi veliki rewrite centralnog voice toka.

Preporučeni ritam:

```text
pi implementira R0
→ Codex/korisnik pregledaju diff i testove
→ pi ispravi nalaze
→ odobri se R1
```

Za HIGH-risk R1–R5 preporučuje se review drugog agenta prije commita, iako pi može sam napisati kod.
