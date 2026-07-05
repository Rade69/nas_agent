# Arhitektura — RileyJarvis Windows Hybrid Voice-First REVISED

> **Zamijenjeno — sadržaj razdvojen u dva kanonska fajla.** Voice-first arhitektura (prvi dio ovog dokumenta) je identična [ARCHITECTURE_VOICE_FIRST_REVISED.md](./ARCHITECTURE_VOICE_FIRST_REVISED.md) — koristiti taj fajl. Document/Paperwork Engine sekcija (drugi dio ovog dokumenta) je prepravljena i premještena u [DOCUMENT_ENGINE_FUTURE_EPIC.md](./DOCUMENT_ENGINE_FUTURE_EPIC.md) — brojevi faza (FAZA 11-17) koje je ovaj fajl predlagao za Document Engine su uklonjeni jer su se sudarali sa `MIGRATION_PLAN.md` numeracijom; future epic tamo sada koristi dependency-based korake bez brojeva faza, plus eksplicitan privacy model za osjetljive dokumente. Ovaj fajl je zadržan samo kao istorijski zapis.

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
- audit trail,
- Document/Paperwork Engine,
- Review Packets,
- citations,
- Action Receipts,
- human approval gate.
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


---

# Document / Paperwork Engine — Review Packet sloj

Ovaj sloj je dodat na osnovu principa iz transcript analize:

```text
Agent ne treba prvenstveno da klikće finalno dugme.
Agent treba da pretvori neuredan skup dokumenata, mejlova, PDF-ova,
slika i bilješki u strukturisan, provjerljiv paket za ljudsku odluku.
```

To je posebno važno za high-trust rad:

```text
- dokumenti,
- osiguranje,
- porezi,
- ugovori,
- računi,
- carinska dokumentacija,
- medicinski ili administrativni obrasci,
- poslovna evidencija.
```

Ricky ne smije biti sistem koji samostalno šalje, potpisuje, plaća ili predaje dokumente.
Ricky treba da pripremi pregledan paket, citira izvore i zaustavi se na ljudskoj provjeri.

---

## Agent skeleton za dokumente

Za rad sa dokumentima koristiti isti skeleton kroz različite domene:

```text
Context Pack
Ingest
Chunk
Normalize
Store
Retrieve
Cite
Export
Gate
```

Ovo je generički skeleton i ne zavisi od toga da li korisnik radi sa emailom, osiguranjem, porezima, fakturama, carinom ili nekim drugim folderom.

---

## Context Pack

`Context Pack` definiše šta Ricky smije da čita i koji je cilj zadatka.

Primjer:

```text
Context Pack:
- folder koji je korisnik izabrao,
- dozvoljeni fajlovi,
- relevantni email thread ili attachment,
- screenshot ako je korisnik odobrio,
- cilj: "napravi pregled", "pripremi paket", "izvuci rokove",
- zabrane: ne šalji, ne potpisuj, ne briši, ne predaji.
```

Pravila:

```text
- Ricky ne smije sam proširiti scope bez korisnikove dozvole.
- Context Pack mora biti vidljiv korisniku.
- Svaki dokument u paketu mora imati izvor.
```

---

## Ingest

`Ingest` znači učitavanje izvora u sistem.

Izvori mogu biti:

```text
- PDF,
- DOCX,
- TXT/MD,
- slike,
- screenshotovi,
- email attachmenti,
- CSV/Excel,
- skenirani dokumenti,
- lokalni folder.
```

MVP ne mora podržati sve formate odmah.

Prvi korisni MVP:

```text
- PDF text extraction,
- TXT/MD,
- slike kao fajl reference,
- ručno dodani folder,
- screenshot koji korisnik eksplicitno odobri.
```

---

## Chunk

`Chunk` znači razbijanje dokumenata na adresabilne dijelove.

Primjer:

```text
Document:
- page 1,
- section "Rok za žalbu",
- paragraph 4,
- table row 8,
- attachment "faktura_001.pdf".
```

Cilj nije samo "Ricky je pročitao fajl", nego:

```text
Ricky zna iz kog dijela dokumenta dolazi svaka tvrdnja.
```

---

## Normalize

`Normalize` pretvara neuredan tekst u strukturisane entitete.

Primjeri:

```text
datumi        -> ISO date
iznosi        -> amount + currency
osobe         -> person
firme         -> company
rokovi        -> deadline
dokumenti     -> document_type
brojevi       -> claim_number / invoice_number / document_number
stavke        -> line_items
nedostaje     -> missing_document
```

Ovo je važnije od samog "AI odgovora", jer čist i normalizovan podatak smanjuje potrebu za skupim modelom i smanjuje greške.

---

## Store

Sve se čuva lokalno.

MVP storage za Document/Paperwork Engine:

```text
context_packs
source_documents
document_chunks
normalized_entities
citations
review_packets
packet_items
packet_exports
gate_decisions
action_receipts
missing_items
```

Ovo se nadovezuje na postojeći SQLite sloj:

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

Ne praviti gomilu `.txt` / `.md` fajlova po defaultu.

Fajlovi se prave samo kada korisnik traži export.

---

## Retrieve

`Retrieve` vraća relevantne dijelove iz lokalno spremljenih izvora.

Ricky ne treba uvijek raditi samo "vector search".
Za mnoge dokumente važnije je strukturalno vraćanje:

```text
- tačan rok,
- tačan broj dokumenta,
- citirani paragraf,
- navedeni iznos,
- konkretan dokaz,
- lista nedostajućih dokumenata.
```

Princip:

```text
Ako dokument već sadrži adresu ili referencu, koristi strukturu.
Ako struktura nije dovoljna, koristi semantičku pretragu kao pomoć.
```

---

## Cite

Svaka tvrdnja u ozbiljnom paketu mora imati izvor.

Ricky mora moći pokazati:

```text
- naziv fajla,
- stranicu,
- sekciju,
- paragraf,
- red tabele,
- screenshot ID,
- email/thread ID ako postoji,
- vrijeme kada je izvor učitan.
```

Bez citata, rezultat je samo "AI tekst".
Sa citatima, rezultat je reviewable packet.

---

## Export

Export pravi paket koji čovjek može pregledati.

Mogući export formati:

```text
- Markdown,
- PDF,
- DOCX,
- CSV/Excel za tabele,
- ZIP folder sa izvorima i izvještajem.
```

Export nije automatski.

Pravila:

```text
- Ricky priprema paket u UI-ju.
- Korisnik ga pregleda.
- Korisnik eksplicitno bira Export.
- Export dobija Action Receipt.
```

---

## Gate

`Gate` je sigurnosna granica.

Ricky smije:

```text
- čitati dozvoljene fajlove,
- organizovati,
- izdvojiti podatke,
- normalizovati,
- napraviti checklistu,
- napraviti nacrt,
- citirati izvore,
- napraviti review packet,
- predložiti sljedeće korake.
```

Ricky ne smije bez eksplicitnog human approval-a:

```text
- poslati email,
- predati obrazac,
- potpisati dokument,
- platiti,
- obrisati važne fajlove,
- poslati dokument trećoj strani,
- napraviti nepovratnu akciju.
```

Za neke akcije default treba biti potpuno blokiran:

```text
- plaćanje,
- digitalni potpis,
- poreska predaja,
- slanje medicinskih/osjetljivih dokumenata,
- masovno brisanje fajlova.
```

---

# Review Packet

Glavni proizvod Document/Paperwork Engine-a nije "odgovor u chatu".

Glavni proizvod je:

```text
Review Packet
```

Review Packet je pregledan paket za ljudsku provjeru.

Sadrži:

```text
- sažetak,
- ključne datume,
- ključne iznose,
- osobe/firme,
- dokumente koji su korišteni,
- citate i izvore,
- listu nedostajućih dokumenata,
- rizike/nejasnoće,
- pitanja za korisnika ili stručnjaka,
- predložene korake,
- nacrt dokumenta ako je potreban,
- Action Receipt.
```

Ricky ne garantuje da je korisnik "završio slučaj".
Ricky pomaže da korisnik prestane raditi sa haotičnom gomilom podataka.

---

# Action Receipt

Svaki ozbiljan zadatak mora završiti sa `Action Receipt`.

Action Receipt odgovara na pitanja:

```text
Šta je Ricky uradio?
Koje izvore je koristio?
Koje fajlove je pročitao?
Šta je promijenio?
Šta je samo pripremio?
Šta nije siguran?
Koji dokazi nedostaju?
Šta korisnik mora provjeriti?
Koja akcija je blokirana ili čeka potvrdu?
```

Receipt je ključ za povjerenje.

Razlika:

```text
Loše:
"AI je to završio."

Dobro:
"Znam šta je Ricky uradio, odakle mu podaci, šta nije uradio i šta ja moram potvrditi."
```

---

# Runbooks / reusable workflows

Ne praviti jednokratne agente za svaki domen.

Koristiti reusable runbooks.

Primjeri:

```text
Runbook: Sredi folder
1. Napravi Context Pack.
2. Učitaj dozvoljene dokumente.
3. Klasifikuj dokumente.
4. Izvuci datume, iznose, osobe/firme.
5. Pronađi nedostajuće stavke.
6. Napravi Review Packet.
7. Napravi Action Receipt.
8. Zaustavi se na Gate-u.

Runbook: Pripremi dokumente za knjigovođu
1. Učitaj folder.
2. Razdvoji račune, izvode, ugovore i nepoznate dokumente.
3. Normalizuj datume, iznose, dobavljače i kategorije.
4. Napravi tabelu.
5. Označi stavke bez dokaza.
6. Exportuj samo ako korisnik traži.

Runbook: Pregled carinskog paketa
1. Učitaj fakturu, CMR, XML i prateće dokumente.
2. Izvuci pošiljaoca, primaoca, robu, vrijednost, valutu, masu i zemlju porijekla.
3. Poveži stavke sa izvorom.
4. Označi nedostajuće ili konfliktne podatke.
5. Napravi Review Packet za ljudsku provjeru.
6. Ne predaj deklaraciju automatski.
```

Svaki runbook koristi isti skeleton:

```text
context pack -> ingest -> chunk -> normalize -> store -> retrieve -> cite -> export -> gate
```

---

# Document Engine UI

Postojeći workspace tabovi ostaju:

```text
Output
Activity
Plans
Memory
Screens
```

Dodati konceptualni prikaz Review Packet-a u `Output`.

Moguće kasnije dodati novi tab:

```text
Packets
```

Ali ne uvoditi novi tab ako komplikuje MVP.

Minimalno:

```text
Output:
- prikazuje trenutni Review Packet.

Activity:
- prikazuje šta je učitano, normalizovano, citirano i exportovano.

Plans:
- prikazuje prijedlog koraka prije obrade foldera.

Memory:
- čuva korisne zapise i prethodne pakete.

Screens:
- screenshot izvori i vizuelni dokazi.
```

---

# Document Engine API / storage MVP

Dodati kasnije, poslije voice/session/activity osnove.

Predloženi endpointi:

```text
POST /context-packs
GET  /context-packs
GET  /context-packs/{id}

POST /documents/ingest
GET  /documents
GET  /documents/{id}

POST /review-packets
GET  /review-packets
GET  /review-packets/{id}

POST /review-packets/{id}/export

GET  /citations
GET  /citations/{id}

POST /gate-decisions
GET  /gate-decisions
```

Ne dodavati ove endpoint-e prije nego što postoje:

```text
- Python backend skeleton,
- Realtime session security,
- Activity timeline,
- Plans/Confirmations.
```

---

# Dodatne faze za Document/Paperwork Engine

Ove faze dolaze poslije postojećih FAZA 4-10.

Ne gurati ih prije stabilnog voice/control sloja.

```text
FAZA 11:
Context Pack MVP
- korisnik bira folder/fajlove,
- definisati dozvoljeni scope,
- cilj zadatka,
- zabranjene akcije.

FAZA 12:
Document Ingest MVP
- učitavanje PDF/TXT/MD,
- osnovni metadata,
- source_documents tabela.

FAZA 13:
Chunk + Normalize MVP
- document_chunks,
- datumi,
- iznosi,
- osobe/firme,
- dokument type,
- missing_items.

FAZA 14:
Citation Map
- svaka tvrdnja u paketu ima izvor,
- citation table,
- link iz Output-a do source dijela.

FAZA 15:
Review Packet Builder
- sažetak,
- timeline,
- checklist,
- missing docs,
- questions,
- risks,
- draft section ako treba.

FAZA 16:
Action Receipt + Gate
- šta je urađeno,
- koji izvori,
- šta čeka korisnika,
- koje akcije su blokirane,
- export samo na zahtjev.

FAZA 17:
Runbooks
- "Sredi folder",
- "Pripremi dokumente za knjigovođu",
- "Pregled carinskog paketa",
- drugi reusable workflow-i.
```

---

# Prioritet

Ovaj sloj je vrlo relevantan, ali nije prije voice/control osnove.

Redoslijed:

```text
Prvo:
FAZA 4-10
- Python backend skeleton,
- Realtime session security,
- Voice-first UI,
- Activity timeline,
- Confirmations/Plans,
- safe local tools,
- Companion voice integration.

Zatim:
FAZA 11-17
- Document/Paperwork Engine,
- Review Packets,
- Citations,
- Action Receipts,
- Runbooks.
```

Razlog:

```text
Ako se Document Engine doda prije stabilnog voice/control sloja,
projekat će postati preširok i teže održiv.
```


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
