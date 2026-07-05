# Arhitektura — RileyJarvis Windows Hybrid Voice-First REVISED

## Status ove verzije

Ovaj dokument ispravlja prethodnu verziju `ARCHITECTURE_VOICE_FIRST.md`.

Prethodna verzija je pogrešno sugerisala da Python backend treba da preuzme cijeli audio pipeline: audio input, VAD, STT, TTS i interruption. To više nije važeća odluka.

Nova ključna odluka:

```text
Postojeći src/lib/realtime.ts ostaje primarni voice/audio pipeline.

Python backend NE preuzima mikrofon, VAD, STT i TTS u MVP-u.

Python backend je sloj za:
- Realtime session security,
- orchestration,
- confirmations,
- plans/proposals,
- activity timeline,
- transcript persistence,
- local tools,
- permissions/risk policy,
- SQLite storage.
```

Razlog: projekat već ima funkcionalan niskolatentni WebRTC/OpenAI Realtime pipeline u rendereru. Zamjena tog puta custom Python audio pipeline-om bi povećala kompleksnost, rizik i latenciju.

---

# Osnovna odluka

RileyJarvis nije chat aplikacija sa mikrofonom.

RileyJarvis je:

```text
glasovni desktop companion
+ vizuelni kontrolni centar
+ sigurni lokalni tool runtime
```

Chat ostaje važan, ali je sekundaran. Tekstualni unos služi kao fallback, korekcija, ručni unos, copy/paste i pregled istorije. Primarni način rada je glas.

---

# Šta ostaje, a šta se mijenja

## Ostaje

```text
React UI
  -> Electron preload / IPC
  -> Electron main kao tanak shell/bridge
  -> Python backend kao lokalni control/storage/tools sloj
  -> SQLite lokalna baza
```

## Mijenja se

Ne uvodi se Python kao audio engine.

Umjesto toga:

```text
Renderer/WebRTC = audio engine
Python backend = voice control + safety + storage + tools
```

---

# Ciljna arhitektura

```text
Voice-first React UI + Companion Orb
  -> src/lib/realtime.ts kao Realtime WebRTC voice client
  -> WebRTC direktno prema OpenAI Realtime API
  -> OpenAI Realtime: VAD, STT events, audio response streaming, interruption
  -> Renderer Realtime Event Router
  -> Electron preload / IPC
  -> Electron main process kao tanak shell/bridge
  -> Python backend kao Voice Control + Agent/Tool Orchestration sloj
  -> Python tools: Windows automation, screenshot, UI inspect, storage, artifacts
  -> SQLite lokalna baza: sessions, activity, transcripts, confirmations, plans, tool_runs, artifacts, settings
```

Cilj nije full rewrite. Cilj je očuvati postojeći radni Realtime voice pipeline i oko njega izgraditi:

```text
- bolji voice-first UI,
- Companion orb,
- API key/session sigurnost,
- Activity timeline,
- Plans/Proposals,
- confirmations,
- local tool runtime,
- SQLite memoriju,
- audit trail.
```

---

# Primarni voice pipeline

Primarni audio put ostaje:

```text
Renderer / src/lib/realtime.ts
  -> WebRTC
  -> OpenAI Realtime API
  -> audio stream nazad u renderer
```

Ovaj dio pokriva:

```text
- mikrofon,
- WebRTC konekciju,
- server-side VAD,
- STT transcript evente,
- streaming audio odgovor,
- interruption,
- audio playback kroz renderer.
```

Ako `src/lib/realtime.ts` već radi ove stvari, ne smije se prepisivati bez jasnog razloga.

---

# Renderer odgovornosti

Renderer je zadužen za:

```text
- voice-first UI,
- Companion orb UI,
- push-to-talk UI,
- text fallback input,
- mikrofon kroz browser/Electron renderer APIs,
- WebRTC Realtime konekciju,
- raw OpenAI Realtime evente,
- audio playback,
- interruption poziv u postojeći Realtime client,
- mapiranje raw eventa u interni VoiceState,
- Realtime Event Router,
- slanje relevantnih activity/transcript eventa Python backendu,
- prikaz Output/Activity/Plans/Memory/Screens panela.
```

Renderer ne smije imati:

```text
- standardni OpenAI API key,
- local tool executor,
- Windows automation,
- SQLite storage,
- permission/risk decision engine,
- plans/proposals storage logiku.
```

---

# Electron main process odgovornosti

Electron main process je samo app shell + bridge.

Zadužen je za:

```text
- createWindow za glavni prozor,
- createWindow za Companion orb,
- app lifecycle,
- IPC setup,
- global hotkey za push-to-talk,
- pokretanje/gašenje Python backend procesa,
- event forwarding između renderera i Python backend-a,
- native tray/context menu po potrebi.
```

`electron/main.cjs` ne smije postati mozak aplikacije.

Dozvoljeno:

```text
- window creation,
- IPC registration,
- Python process startup/shutdown,
- companion window lifecycle,
- event forwarding.
```

Nije dozvoljeno:

```text
- agent reasoning,
- STT/TTS audio pipeline,
- tool execution,
- storage,
- plans/proposals decision logic,
- confirmation decision logic,
- Windows automation business logic.
```

---

# Python backend odgovornosti

Python backend nije audio engine u MVP-u.

Python backend je:

```text
Voice Control Layer
+ Session Security Layer
+ Safety Layer
+ Storage Layer
+ Local Tool Orchestration Layer
```

Python backend radi:

```text
- Realtime session endpoint,
- OpenAI standard API key zaštitu,
- izdavanje ephemeral/session credentiala rendereru,
- session registry,
- session metadata,
- activity timeline persistence,
- transcript persistence,
- confirmation context,
- plans/proposals storage,
- tool registry,
- tool execution,
- local Windows tools,
- permission/risk policy,
- SQLite storage,
- artifacts/screenshots/logs.
```

Python backend ne radi u MVP-u:

```text
- direktno čitanje mikrofona,
- custom VAD,
- custom STT,
- custom TTS,
- audio playback,
- zamjenu za src/lib/realtime.ts.
```

Custom Python STT/TTS može biti budući fallback/offline mode, ali nije aktivni MVP plan.

---

# API key / session security

Renderer ne smije držati standardni OpenAI API key.

Ispravan tok:

```text
Renderer traži novu Realtime sesiju
  -> Python backend koristi standardni OpenAI API key iz .env
  -> Python backend kreira ephemeral/session credential
  -> Renderer koristi kratkoživući credential za WebRTC
  -> audio ide direktno renderer <-> OpenAI Realtime
```

Time se dobija:

```text
- niska latencija Realtime WebRTC puta,
- API key ostaje van renderera,
- Python backend kontroliše konfiguraciju sesije,
- Python backend može logovati session metadata.
```

---

# Realtime Event Router

Dodati/izdvojiti renderer sloj:

```text
src/lib/realtime.ts
src/lib/realtimeEventRouter.ts
src/lib/voiceStateMapper.ts
```

Realtime Event Router radi:

```text
- prima raw OpenAI Realtime evente,
- ne mijenja raw event format,
- mapira raw evente u interne app evente,
- šalje UI state update,
- šalje transcript/activity evente Python backendu,
- ne izvršava local risky tools direktno.
```

Primjer mapiranja:

```text
raw OpenAI:
conversation.item.input_audio_transcription.completed

internal app event:
voice.final_transcript
activity.created
```

Raw OpenAI evente čuvati pod originalnim nazivima gdje god je potrebno za debugging.

---

# Primarni tok interakcije

```text
Korisnik aktivira push-to-talk / klikne orb / koristi hotkey
  -> src/lib/realtime.ts koristi postojeći Realtime pipeline
  -> UI odmah pokazuje Listening
  -> OpenAI Realtime radi VAD/STT/audio response
  -> raw OpenAI event ide u Realtime Event Router
  -> router mapira event u app event
  -> UI ažurira VoiceState
  -> transcript/activity šalje se Python backendu za persistence
  -> ako je potrebna lokalna akcija:
       Python radi risk/permission/confirmation/tool execution
  -> rezultat ide u Output/Activity panel i po potrebi nazad u voice odgovor
```

Sekundarni tok:

```text
Korisnik kuca poruku u tekstualni input
  -> renderer šalje tekst u postojeći Realtime/API/Agent tok
  -> Python backend po potrebi čuva activity i izvršava lokalne tools
  -> rezultat može biti tekstualni, glasovni ili oba
```

---

# VoiceState

Centralni state model:

```ts
type VoiceState =
  | "idle"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "waiting_confirmation"
  | "interrupted"
  | "muted"
  | "error";
```

Ovaj state mora biti vidljiv u:

```text
- TopBar,
- AssistantAvatar,
- CompanionOrb,
- BottomVoiceBar,
- ActivityTimeline,
- ApprovalDialog.
```

Ako aplikacija već ima mood/state mapping, koristiti ga kao osnovu i uskladiti sa ovim enumom.

## Mapiranje state-a na UI

```text
idle:
- Ricky je spreman
- miran plavi orb

listening:
- plavi puls
- tekst: "Slušam..."

transcribing:
- kratki processing state
- tekst: "Prepoznajem govor..."

thinking:
- ljubičasto/plavi shimmer
- tekst: "Razmišljam..."

speaking:
- animacija govora
- tekst: "Ricky odgovara..."
- vidljivo Stop dugme

waiting_confirmation:
- narandžasti status
- modal/panel sa prijedlogom radnje
- voice commands: "da", "ne", "pokreni", "otkaži"

interrupted:
- kratki status "Prekinuto"
- vraća se u idle

muted:
- mikrofon isključen
- jasno vidljivo

error:
- crveni status
- jasna poruka šta nije uspjelo
```

---

# Push-to-talk kao default

Default način rada mora biti push-to-talk.

```text
Default:
- mikrofon nije stalno aktivan kao namjerni product mode
- korisnik aktivira slušanje dugmetom, hotkey-em ili Companion orb-om
```

Preporučene opcije:

```text
- Ctrl + Space,
- Alt + R,
- Hold to talk dugme,
- Companion orb interakcija.
```

Always-listening može postojati kasnije kao opcija, ali mora biti:

```text
OFF by default
```

---

# Companion Orb kao voice entry point

Companion orb je primarni brzi ulaz za glas.

Mogući model ponašanja:

```text
single click:
- push-to-talk ili start listening

double click:
- otvori glavni prozor

right click:
- companion menu
```

Alternativni model:

```text
single click:
- otvori glavni prozor

hold click:
- push-to-talk

right click:
- companion menu
```

Ovo treba testirati u praksi. Ne zaključavati prerano.

Companion orb mora prikazati VoiceState:

```text
Ready
Listening
Transcribing
Thinking
Speaking
Waiting confirmation
Error
Muted
Backend disconnected
```

---

# Chat kao sekundarni fallback

Tekstualni chat/input ostaje, ali nije centar aplikacije.

Služi za:

```text
- kada korisnik ne želi govoriti,
- korekciju pogrešno prepoznatog govora,
- ručni unos dužih instrukcija,
- pregled istorije razgovora,
- copy/paste sadržaj,
- tihe situacije gdje glas nije poželjan.
```

UI pravilo:

```text
Voice controls su vizuelno primarni.
Text input je uvijek dostupan, ali sekundaran.
```

---

# Latencija

Latencija zavisi od:

```text
- brzine interneta,
- stabilnosti konekcije,
- udaljenosti API servera,
- izabranog modela,
- OpenAI Realtime sesije,
- lokalnog hardvera,
- audio uređaja.
```

Ne možemo garantovati istu brzinu kod svakog korisnika.

Ali UI mora smanjiti osjećaj čekanja:

```text
1. Vizuelni feedback mora biti trenutan.
2. Orb/status mora odmah pokazati Listening.
3. Nakon govora odmah pokazati Transcribing/Thinking.
4. Koristiti postojeći streaming audio odgovor.
5. Korisnik uvijek mora imati Stop/Cancel.
6. Kod sporog odgovora prikazati da sistem još radi.
7. Ako mreža padne, jasno prikazati problem.
```

Korisnik može prihvatiti da odgovor kasni, ali ne može prihvatiti da ne zna da li ga je Ricky čuo ili da li se aplikacija zaledila.

## Latency monitor

Ne praviti odmah posebnu kompleksnu šemu ako nije potrebna.

MVP: latency evente upisivati u `activity_events`.

Mjeriti:

```text
- realtime session requested,
- WebRTC connected,
- listening started,
- first transcript delta,
- final transcript,
- response started,
- first audio,
- response completed,
- interruption.
```

Kasnije se može izdvojiti `latency_metrics` tabela.

---

# Interruption / Stop

Prekidanje asistenta je obavezno.

Pošto postojeći Realtime pipeline već podržava interruption, ne zamjenjivati ga custom Python mehanizmom.

Potrebno je:

```text
- UI Stop dugme,
- voice command: "stani",
- voice command: "prekini",
- voice command: "stop",
- ESC,
- poziv postojećeg interrupt mehanizma u src/lib/realtime.ts,
- activity event za interruption.
```

Python backend može evidentirati i sinhronizovati stanje:

```text
- cancel_pending_confirmation(),
- cancel_safe_before_tool_execution(),
- mark_activity_interrupted().
```

Za akcije koje su već izvršene ne obećavati rollback ako ga nema.

**Napomena (2026-07-05):** Voice interruption i tool cancellation su dva odvojena sloja — prekid glasovnog odgovora ne prekida automatski tool koji je u toku. Puna `execution_id`/`cancellation_token` state mašina (planned → preflight → running → commit_started → completed/cancelled_before_commit/cannot_cancel_commit_started) i pravila za event throttling/backpressure ka Python backend-u su definisana u `SECURITY_HARDENING_PLAN.md` sekcija 25 "Realtime Event Flow and Cancellation Safety" — gornje tri stub funkcije se implementiraju prema toj specifikaciji, ne proizvoljno.

---

# Voice confirmations

Rizične akcije zahtijevaju vizuelnu i glasovnu potvrdu.

Potvrda nije dio audio pipeline-a. Potvrda je safety/orchestration dio i pripada Python backendu + UI-ju.

Primjer:

```text
Ricky kaže:
"Predlažem da otvorim aplikaciju i unesem tekst u aktivni prozor. Da li da nastavim?"

UI prikazuje:
- naziv akcije,
- korake,
- rizik,
- ciljnu aplikaciju/prozor ako postoji,
- dugmad: Otkaži / Pokreni.
```

Korisnik može potvrditi:

```text
- "da",
- "pokreni",
- "nastavi",
- klik na Pokreni.
```

Korisnik može odbiti:

```text
- "ne",
- "otkaži",
- "prekini",
- klik na Otkaži.
```

## Confirmation context

Svaka potvrda mora imati ID.

```text
pending_confirmation_id = "confirm_20260705_001"
```

Komanda "da" ne smije ništa uraditi ako nema aktivne potvrde.

Ako ima više pending stvari, Ricky mora pitati na koju se odnosi ili prikazati listu.

---

# Plans / Proposals

Ne koristiti Notepad za planiranje.

Ricky treba prikazati plan u dijaloškom prozoru ili panelu.

Naziv u UI-ju:

```text
Ricky predlaže ove korake
```

Tok:

```text
korisnik glasom zada zadatak
  -> Ricky napravi prijedlog koraka
  -> prijedlog se prikaže u dijalogu/panelu
  -> Ricky ga može i izgovoriti ukratko
  -> korisnik kaže "pokreni" ili klikne Pokreni
  -> plan se čuva u SQLite kao interni zapis
  -> ne pravi se .txt/.md fajl automatski
```

Export u `.md` ili `.txt` samo ako korisnik traži.

---

# Storage

SQLite ostaje lokalno perzistentno skladište.

## MVP tabele

Ne počinjati sa prevelikom šemom.

MVP:

```text
settings
realtime_sessions
voice_turns
transcripts
activity_events
confirmations
plans
plan_steps
tool_runs
artifacts
```

## Kasnije

```text
tts_events
latency_metrics
screenshots
plan_runs
memory_items
```

## Planovi se ne čuvaju kao gomila fajlova

Planovi su interni zapisi u bazi.

Fajlovi se prave samo za:

```text
- export,
- screenshot,
- generated image,
- document artifact,
- user-requested markdown/txt.
```

---

# Workspace tabs

Predloženi glavni tabovi:

```text
Output
Activity
Plans
Memory
Screens
```

`Tools` ne mora biti glavni tab za obične korisnike. Može biti u Settings/Advanced.

---

# Event naming convention

Koristiti tri odvojene konvencije.

## 1. Electron IPC kanali: dvotačka

```text
app:quit
app:enter-companion-mode
voice:start
voice:stop
voice:interrupt
confirmation:approve
confirmation:reject
backend:get-status
```

## 2. Interni app/backend eventi: tačka

```text
backend.connected
voice.state_changed
voice.final_transcript
tool.started
activity.created
confirmation.required
```

## 3. OpenAI raw eventi: originalni naziv

Ne preimenovati raw evente prije event-router sloja.

Primjeri:

```text
conversation.item.input_audio_transcription.delta
conversation.item.input_audio_transcription.completed
response.audio.delta
response.done
input_audio_buffer.speech_started
```

---

# API / Event komunikacija

## REST endpointi MVP

```text
GET  /health

POST /realtime/session
GET  /realtime/sessions

POST /activity
GET  /activity

POST /transcripts
GET  /transcripts

POST /confirmations
POST /confirmations/{id}/approve
POST /confirmations/{id}/reject

GET  /plans
POST /plans
PATCH /plans/{id}

GET  /artifacts
```

Ne uvoditi `/voice/start`, `/voice/stop`, `/voice/devices` kao Python audio endpoint-e u MVP-u ako renderer već posjeduje Realtime audio path.

Renderer voice start/stop može ostati local/IPC oko `src/lib/realtime.ts`.

## WebSocket/internal event types

```text
backend.connected
backend.disconnected
backend.error

voice.state_changed
voice.partial_transcript
voice.final_transcript
voice.interrupted

agent.thinking_started
agent.thinking_finished

confirmation.required
confirmation.approved
confirmation.rejected
confirmation.expired

plan.created
plan.updated
plan.approved
plan.started
plan.completed
plan.failed
plan.cancelled

tool.started
tool.progress
tool.completed
tool.failed
tool.blocked

artifact.created
artifact.updated

activity.created
```

---

# Faze — uskladiti sa MIGRATION_PLAN.md

Ne uvoditi zasebnu VF-1/VF-6 numeraciju koja lebdi pored postojećeg plana.

Voice-first rad treba spojiti u jedan `MIGRATION_PLAN.md` tracker.

Predloženi redoslijed:

```text
FAZA 0-3:
Postojeći Windows/Electron baseline.

FAZA 4:
Python backend skeleton.

FAZA 5:
Realtime session security:
- Python endpoint za Realtime session/client secret,
- standard OpenAI API key ostaje backend-side,
- renderer koristi ephemeral/session credential.

FAZA 6:
Voice-first UI refactor oko postojećeg src/lib/realtime.ts:
- TopBar voice state,
- BottomVoiceBar,
- text fallback sekundaran,
- Realtime Event Router,
- VoiceState mapping.

FAZA 7:
Activity timeline + transcript persistence:
- activity_events,
- transcripts,
- voice_turns,
- renderer šalje relevantne evente Python backendu.

FAZA 8:
Confirmations + Plans/Proposals:
- confirmation_id,
- Approval dialog,
- plan storage u SQLite,
- nema Notepad plana,
- nema automatskog exporta .txt/.md.

FAZA 9:
Tool registry + safe local tools:
- risk policy,
- allowed apps,
- tool_runs,
- local Windows tools.

FAZA 10:
Companion orb voice integration:
- orb prikazuje VoiceState,
- push-to-talk/restore ponašanje,
- context menu.
```

---

# Out of scope

Ricky nije coding agent.

Izostaviti:

```text
- coding profile,
- git status,
- run tests,
- edit source code,
- project refactor,
- codebase indexing kao osnovna funkcija,
- IDE replacement.
```

---

# GitNexus / agent_reports procedura

Ako repo koristi `CLAUDE.md`, `AGENTS.md`, GitNexus ili `agent_reports`, ta procedura i dalje važi.

Pravila:

```text
- prije izmjene bitnog simbola uraditi impact/context analizu ako je GitNexus dostupan,
- ako index nije svjež, pokrenuti reindex po postojećim pravilima projekta,
- prije commita provjeriti affected scope,
- svaki agent mora ostaviti kratak report šta je mijenjao,
- ne raditi veliki refaktor bez blast-radius provjere.
```

Ovaj dokument ne zamjenjuje `CLAUDE.md`/`AGENTS.md`; samo definiše arhitekturu.

---

# Pravila za agente koji implementiraju

```text
1. OpenAI Realtime WebRTC ostaje primarni audio pipeline.
2. Ne zamjenjivati src/lib/realtime.ts Python audio pipeline-om.
3. Python ne preuzima mikrofon, VAD, STT i TTS u MVP-u.
4. Python backend je vlasnik session security, storage, confirmations, plans, tools i permissions sloja.
5. Voice-first je osnovni princip.
6. Chat/text input je fallback, ne primarni tok.
7. Ne dodavati coding-agent funkcije.
8. Ne širiti electron/main.cjs poslovnom logikom.
9. Companion orb mora prikazivati VoiceState.
10. Always-listening je OFF by default.
11. Rizične akcije traže vizuelnu i glasovnu potvrdu.
12. Planovi se čuvaju u SQLite, ne kao gomila .txt/.md fajlova.
13. Export fajlova se radi samo na zahtjev korisnika.
14. Svaka bitna voice/tool akcija ide u Activity timeline.
15. Latencija se ne može potpuno kontrolisati, ali UI mora odmah davati feedback.
