# Arhitektura — RileyJarvis Windows Hybrid Voice-First

> **Zamijenjeno.** Ovaj dokument je zamijenjen sa [ARCHITECTURE_VOICE_FIRST_REVISED.md](./ARCHITECTURE_VOICE_FIRST_REVISED.md) — prethodna verzija je pogrešno predlagala da Python preuzme cijeli audio pipeline (mikrofon/VAD/STT/TTS), što je ispravljeno u revidiranoj verziji. Zadržano samo kao istorijski zapis.

## Osnovna odluka

RileyJarvis više ne treba posmatrati kao chat aplikaciju sa mikrofonom.

Nova osnovna odluka:

```text
RileyJarvis = glasovni desktop companion
              + vizuelni kontrolni centar
              + sigurni lokalni tool runtime
```

Chat ostaje važan, ali je sekundaran. Tekstualni unos služi kao fallback, korekcija, ručni unos i pregled istorije. Primarni način rada je glas.

Polazna arhitektura ostaje ista u osnovnom lancu: React UI, Electron preload/IPC, Electron main kao tanak shell/bridge, Python backend kao mozak, Python tools i SQLite storage. Mijenja se prioritet: između UI-ja i agent runtime-a uvodi se **Voice Runtime** kao primarni sloj interakcije.

---

## Ciljna arhitektura

```text
Voice-first React UI + Companion Orb
  -> Electron preload / IPC
  -> Electron main process kao tanak shell/bridge
  -> Python backend kao mozak aplikacije
  -> Python Voice Runtime: audio input, VAD, STT, TTS, interruption, confirmations
  -> Python Agent Runtime + Tool Registry + Tool Executor
  -> Python Tools: Windows automation, screenshot, UI inspect, storage, artifacts
  -> SQLite lokalna baza, voice sessions, activity, plans, artifacts, settings
```

Cilj nije full rewrite. Cilj je postepeno izvlačenje logike iz `electron/main.cjs` u modularan Python backend, ali uz promjenu prioriteta: **glas je primarni tok interakcije**.

---

# Primarni tok interakcije

```text
Korisnik aktivira push-to-talk / klikne orb / koristi hotkey
  -> Ricky odmah vizuelno pokaže da sluša
  -> audio ide u Voice Runtime
  -> STT pravi transkript
  -> Agent Runtime razumije namjeru
  -> ako je sigurno: odgovara ili izvršava
  -> ako je rizično: traži glasovnu + vizuelnu potvrdu
  -> rezultat ide glasom + u Output/Activity panel
```

Sekundarni tok:

```text
Korisnik kuca poruku u tekstualni input
  -> agent obradi kao tekstualni zahtjev
  -> rezultat može biti tekstualni, glasovni ili oba
```

---

# Podjela odgovornosti

## React renderer = voice-first UI + vizuelni kontrolni centar

React UI je zadužen za:

- glavni voice-first prozor,
- Companion orb UI,
- push-to-talk dugme,
- mikrofon status,
- prikaz voice stanja,
- tekstualni fallback input,
- Output panel,
- Activity timeline,
- Plans/Proposals panel,
- Approval dialog,
- Memory/Screens/Artifacts prikaz,
- IPC komunikaciju sa Electron main procesom.

React UI ne smije sadržati agent logiku, storage logiku, AI-service logiku ili Windows automation logiku.

## Electron main process = app shell + IPC bridge + Python process manager

Electron main process je zadužen za:

- `createWindow` za glavni prozor,
- `createWindow` za Companion orb,
- app lifecycle,
- IPC setup,
- global hotkey za push-to-talk,
- pokretanje/gašenje Python backend procesa,
- prosljeđivanje eventa iz Python backend-a prema React UI-ju,
- native tray/context menu po potrebi.

`electron/main.cjs` ne smije postati mozak aplikacije. Ne smije dobijati novu agent logiku, voice processing logiku, computer-use logiku, storage logiku, AI-service logiku ili poslovnu logiku.

## Python backend = Voice Runtime + Agent Runtime + Tools + Storage

Python backend je srce aplikacije.

Zadužen je za:

- voice runtime,
- speech-to-text integraciju,
- text-to-speech integraciju,
- interruption/cancel mehanizme,
- conversation turn management,
- agent runtime,
- tool registry,
- tool execution,
- Windows automation,
- screenshot,
- UI inspect,
- memoriju,
- action log,
- SQLite storage,
- AI model/API pozive,
- permission/risk/confirmation sloj,
- artifact generation.

---

# Voice Runtime

Dodati novi Python modul:

```text
python_backend/
  app/
    voice/
      audio_input.py
      audio_output.py
      device_manager.py
      voice_activity.py
      transcription.py
      speech_synthesis.py
      conversation_turns.py
      interruption.py
      confirmation_listener.py
      voice_state.py
      latency_monitor.py
```

Voice Runtime upravlja:

```text
- izborom mikrofona
- testom mikrofona
- nivoom ulaznog zvuka
- detekcijom govora / tišine
- snimanjem audio turn-a
- transkripcijom govora
- slanjem transkripta agent runtime-u
- reprodukcijom odgovora
- prekidanjem govora
- glasovnim potvrdama
- voice state eventima prema UI-ju
```

---

# Voice states

Uvesti centralni state model:

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
- TopBar
- AssistantAvatar
- CompanionOrb
- BottomVoiceBar
- ActivityTimeline
- ApprovalDialog
```

Nije dovoljno da samo ikonica mikrofona promijeni boju.

## Mapiranje state-a na UI

```text
idle:
- Ricky je spreman
- miran plavi orb

listening:
- plavi puls
- indikator jačine mikrofona
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
- mikrofon nije stalno uključen
- korisnik aktivira slušanje dugmetom, hotkey-em ili Companion orb-om
```

Preporučene opcije:

```text
- Ctrl + Space
- Alt + R
- dugme "Hold to talk"
- Companion orb interakcija
```

Always-listening može postojati kasnije kao opcija, ali mora biti:

```text
OFF by default
```

Razlog:

- privatnost,
- manje grešaka,
- lakše povjerenje korisnika,
- manje slučajnog izvršavanja akcija.

---

# Companion Orb kao voice entry point

Companion Mode dobija veći značaj u voice-first arhitekturi.

Companion orb nije samo mini ikonica. On je primarni brzi ulaz za glas.

Mogući model ponašanja:

```text
single click:
- push-to-talk ili start listening

double click:
- otvori glavni prozor

right click:
- companion menu
```

Alternativni model, ako je single-click za listening problematičan:

```text
single click:
- otvori glavni prozor

hold click:
- push-to-talk

right click:
- companion menu
```

Ovo treba testirati u praksi. Ne zaključavati prerano.

Companion orb mora prikazati voice state:

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

# Chat kao sekundarni, ali kvalitetan fallback

Tekstualni chat/input ostaje, ali nije centar aplikacije.

Služi za:

```text
- kada korisnik ne želi govoriti
- korekciju pogrešno prepoznatog govora
- ručni unos dužih instrukcija
- pregled istorije razgovora
- copy/paste sadržaj
- tihe situacije gdje glas nije poželjan
```

UI pravilo:

```text
Voice controls su vizuelno primarni.
Text input je uvijek dostupan, ali sekundaran.
```

Primjer donjeg bara:

```text
[ Hold to talk ]  Ricky is ready           [Type instead...           ] [Send]
```

---

# Latencija

Latencija zavisi od više faktora:

```text
- brzina interneta
- stabilnost konekcije
- udaljenost API servera
- izabrani model
- STT brzina
- TTS brzina
- lokalni hardver
```

Ne možemo garantovati istu brzinu kod svakog korisnika.

Ali ne smijemo samo reći: "to zavisi od interneta, korisnik mora prihvatiti". Arhitektura mora smanjiti osjećaj čekanja.

## Pravila za dobar UX kod latencije

```text
1. Vizuelni feedback mora biti trenutan.
2. Orb/status mora odmah pokazati Listening.
3. Nakon govora odmah pokazati Transcribing/Thinking.
4. Koristiti streaming odgovora gdje je moguće.
5. TTS treba početi čim ima dovoljno sigurnog teksta.
6. Korisnik uvijek mora imati Stop/Cancel.
7. Kod sporog odgovora prikazati da sistem još radi.
8. Ako mreža padne, jasno prikazati problem.
```

Korisnik može prihvatiti da odgovor ponekad kasni, ali ne može prihvatiti da ne zna da li ga je Ricky čuo ili da li se aplikacija zaledila.

## Latency monitor

Dodati mjerenje:

```text
- audio capture start
- speech detected
- transcription started
- transcription completed
- model request started
- first token/first audio
- full response completed
- TTS started
- TTS completed
```

Ovo se čuva u Activity/Diagnostics logu.

---

# Interruption / Stop

Prekidanje asistenta je obavezno.

Korisnik mora moći prekinuti Ricky-ja kroz:

```text
- Stop dugme
- voice command: "stani"
- voice command: "prekini"
- voice command: "stop"
- ESC
```

Python backend mora imati:

```text
interrupt_speech()
cancel_current_response()
cancel_pending_confirmation()
cancel_safe_before_tool_execution()
```

Za akcije koje su već izvršene ne obećavati rollback ako ga nema.

Ako je alat rizičan, prekid mora zaustaviti izvršavanje prije konkretne akcije kad god je moguće.

---

# Voice confirmations

Rizične akcije zahtijevaju vizuelnu i glasovnu potvrdu.

Primjer:

```text
Ricky kaže:
"Predlažem da otvorim aplikaciju i unesem tekst u aktivni prozor. Da li da nastavim?"

UI prikazuje:
- naziv akcije
- korake
- rizik
- ciljnu aplikaciju/prozor ako postoji
- dugmad: Otkaži / Pokreni
```

Korisnik može potvrditi:

```text
- "da"
- "pokreni"
- "nastavi"
- klik na Pokreni
```

Korisnik može odbiti:

```text
- "ne"
- "otkaži"
- "prekini"
- klik na Otkaži
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

Tehnički naziv može biti:

```text
Plan
Proposal
TaskPreview
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

Dodati tabele/entitete za voice-first rad:

```text
voice_sessions
voice_turns
transcripts
tts_events
latency_metrics
plans
plan_steps
plan_runs
confirmations
activity_events
artifacts
screenshots
settings
```

## Planovi se ne čuvaju kao gomila fajlova

Planovi su interni zapisi u bazi.

Fajlovi se prave samo za:

```text
- export
- screenshot
- generated image
- document artifact
- user-requested markdown/txt
```

Organizacija fajlova:

```text
RickyData/
  database/
    ricky.sqlite

  artifacts/
    2026/
      07/

  screenshots/
    2026/
      07/

  exports/
    plans/
    artifacts/

  logs/
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

## Output

Glavni rezultat razgovora ili zadatka.

## Activity

Timeline glasovnih i tool događaja:

```text
12:44 Listening started
12:44 Transcript: "Ricky, pogledaj šta je na ekranu"
12:44 screen_snapshot OK
12:45 UI inspect OK
12:45 Output created
```

## Plans

Interni prijedlozi i izvršeni zadaci:

```text
Draft
Approved
Running
Completed
Failed
Archived
```

## Memory

Bilješke, records, korisni zapisi.

## Screens

Screenshotovi koje je korisnik eksplicitno napravio ili koje je Ricky napravio tokom odobrenog zadatka.

---

# Out of scope

Ricky nije coding agent.

Ne planirati funkcije koje već dobro rade u VSCode, Cursor, Codex ili Claude Code alatima.

Izostaviti:

```text
- coding profile
- git status
- run tests
- edit source code
- project refactor
- codebase indexing kao osnovna funkcija
- IDE replacement
```

Ricky može otvoriti aplikaciju ili pomoći korisniku oko opšteg rada, ali ne treba postati zamjena za developerske alate.

---

# API / Event komunikacija

## REST endpointi

```text
GET  /health
GET  /voice/devices
POST /voice/start
POST /voice/stop
POST /voice/interrupt
POST /agent/message
POST /confirmations/{id}/approve
POST /confirmations/{id}/reject
GET  /activity
GET  /plans
GET  /artifacts
```

## WebSocket event types

```text
voice.state_changed
voice.partial_transcript
voice.final_transcript
voice.tts_started
voice.tts_finished
voice.interrupted

agent.thinking_started
agent.thinking_finished

confirmation.required
confirmation.approved
confirmation.rejected

tool.started
tool.progress
tool.completed
tool.failed
tool.blocked

artifact.created
artifact.updated

activity.created

backend.connected
backend.disconnected
backend.error
```

---

# Minimalne faze za voice-first implementaciju

## Phase VF-1 — Voice-first UI state

Cilj:

```text
UI prikazuje voice-first prirodu aplikacije i sva osnovna voice stanja.
```

Zadaci:

```text
1. Dodati VoiceState tip.
2. Dodati TopBar voice status.
3. Dodati BottomVoiceBar.
4. CompanionOrb povezati sa voice state-om.
5. Text input pomjeriti u sekundarnu ulogu.
6. Mock stanja: idle, listening, thinking, speaking, waiting_confirmation, error.
```

Acceptance criteria:

```text
- korisnik odmah vidi da je glas primarni način rada
- text input postoji, ali nije dominantan
- voice state je vidljiv u glavnom prozoru i companion modu
```

## Phase VF-2 — Push-to-talk foundation

Cilj:

```text
Omogućiti osnovni push-to-talk tok bez full agent logike.
```

Zadaci:

```text
1. Dodati Hold to talk dugme.
2. Dodati hotkey placeholder.
3. Dodati start/stop voice IPC kanale.
4. Dodati indikator nivoa mikrofona ako je moguće.
5. Dodati stanje "listening" dok korisnik drži dugme.
```

Acceptance criteria:

```text
- korisnik može pokrenuti i zaustaviti listening state
- UI odmah reaguje
- nema always-listening po defaultu
```

## Phase VF-3 — STT integration

Cilj:

```text
Pretvaranje govora u tekst i prikaz transkripta.
```

Zadaci:

```text
1. Audio ide u Python backend.
2. Python backend radi transkripciju.
3. UI prikazuje partial/final transcript.
4. Korisnik može ponoviti ili ispraviti transkript prije slanja kod nesigurnih slučajeva.
```

Acceptance criteria:

```text
- izgovorena komanda se pojavi kao tekst
- Ricky ne izvršava rizične akcije na osnovu nesigurne transkripcije
```

## Phase VF-4 — TTS / Speaking

Cilj:

```text
Ricky odgovara glasom.
```

Zadaci:

```text
1. Dodati TTS odgovor.
2. Dodati speaking state.
3. Dodati Stop dugme.
4. Dodati mute opciju.
5. Dodati osnovne voice settings: glas, brzina, volume.
```

Acceptance criteria:

```text
- Ricky može odgovoriti glasom
- korisnik može zaustaviti odgovor
- mute je uvijek vidljiv
```

## Phase VF-5 — Voice confirmations

Cilj:

```text
Rizične akcije se potvrđuju glasom i vizuelno.
```

Zadaci:

```text
1. Dodati confirmation context ID.
2. Dodati Approval dialog.
3. Dodati voice commands: da, ne, pokreni, otkaži, stani.
4. Povezati confirmation state sa Activity timeline.
```

Acceptance criteria:

```text
- "da" ne radi ništa ako nema aktivne potvrde
- high-risk action ne ide bez potvrde
- potvrda je vidljiva i čujna
```

## Phase VF-6 — Voice Activity Timeline

Cilj:

```text
Korisnik vidi šta je Ricky čuo, mislio, rekao i uradio.
```

Zadaci:

```text
1. Dodati voice evente u Activity.
2. Dodati tool evente u Activity.
3. Dodati transcript history.
4. Dodati latency metrics u diagnostics/log.
```

Acceptance criteria:

```text
- korisnik može provjeriti šta je Ricky čuo
- može se vidjeti kada je akcija pokrenuta
- greške su razumljive
```

---

# Pravila za agente koji implementiraju

```text
1. Voice-first je osnovni princip.
2. Chat/text input je fallback, ne primarni tok.
3. Ne dodavati coding-agent funkcije.
4. Ne širiti electron/main.cjs poslovnom logikom.
5. Python backend je vlasnik voice runtime-a, agent runtime-a, storage-a i toolova.
6. Companion orb mora prikazivati voice state.
7. Always-listening je OFF by default.
8. Rizične akcije traže vizuelnu i glasovnu potvrdu.
9. Planovi se čuvaju u SQLite, ne kao gomila .txt/.md fajlova.
10. Export fajlova se radi samo na zahtjev korisnika.
11. Svaka bitna voice/tool akcija ide u Activity timeline.
12. Latencija se ne može potpuno kontrolisati, ali UI mora odmah davati feedback.
```
