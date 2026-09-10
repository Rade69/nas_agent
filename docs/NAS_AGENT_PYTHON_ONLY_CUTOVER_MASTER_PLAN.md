---
title: "Naš Agent — Python-Only Cutover Master Plan"
description: "Detaljan, code-aligned plan za što brži prelazak Rade69/nas_agent sa aktivnog Electron/React + Python hibridnog runtime-a na svakodnevni Python/PySide6 runtime, uz očuvanje postojećeg Python backend-a, ToolExecutor/PermissionEngine sigurnosnog puta, OpenAI Realtime WebSocket voice sloja i rollback mogućnosti."
project: "nas_agent"
repository: "Rade69/nas_agent"
target_branch: "qt-desktop-migration"
baseline_date: "2026-09-10"
baseline_head_observed: "a1733b9827d46590b586acb051498c7847d5573c"
status: "master-implementation-plan"
priority: "critical"
strategy: "cutover-first, parity-after"
supersedes_for_qt_cutover:
  - "zastarjele Electron/WebRTC pretpostavke iz docs/MIGRATION_PLAN.md"
consolidates:
  - "MIGRATION_PLAN.md"
  - "NAS_AGENT_OMARCHY_LESSONS_IMPLEMENTATION_PLAN.md"
  - "docs/QT_MIGRATION_PLAN_2026-07-20.md"
focus:
  - "Python-only daily-driver runtime"
  - "PySide6 main shell"
  - "OpenAI Realtime WebSocket voice"
  - "microphone reliability"
  - "voice observability and diagnostics"
  - "ToolExecutor / PermissionEngine parity"
  - "in-app Realtime model selector"
  - "feature parity"
  - "Windows cutover"
  - "Electron/React retirement"
---

# Naš Agent — Python-Only Cutover Master Plan

## 0. Svrha dokumenta

Ovaj dokument je novi operativni plan za završetak migracije projekta `Rade69/nas_agent` na Python/PySide6 desktop aplikaciju.

Ne pokušava da ponovo ispriča istoriju projekta. Njegova svrha je da odgovori na praktično pitanje:

> Kako da iz trenutnog stanja koda što prije dobijemo Rickyja koji se svakodnevno pokreće i radi bez Electron/React runtime-a, a da ne izgubimo već izgrađenu sigurnost, toolove, voice funkcionalnost i mogućnost rollback-a?

Plan je zasnovan na tri izvora:

1. istorijskom `MIGRATION_PLAN.md`;
2. `NAS_AGENT_OMARCHY_LESSONS_IMPLEMENTATION_PLAN.md`;
3. stvarnom stanju grane `qt-desktop-migration` provjerenom 2026-09-10.

Kod ima prednost nad dokumentom. Ako se nakon datuma ovog plana stanje repozitorija promijeni, agent mora prvo ponovo provjeriti HEAD, tracker, testove i relevantne call-siteove.

---

# 1. Strateška odluka

## 1.1 Novi prioritet

Raniji plan je bio organizovan kao klasična migracija:

```text
port komponenti
→ feature parity
→ security
→ packaging
→ finalni cutover
```

Za trenutno stanje projekta to više nije najbolji redoslijed.

Korisnik već ima praktičan problem sa glasom: agent ga povremeno ne čuje. Aktivni runtime i dalje uključuje Electron/renderer voice putanju, dok Python već posjeduje backend, agent runtime, tool execution, permission sistem i novu WebSocket voice implementaciju.

Zato se usvaja:

```text
CUTOVER-FIRST
```

Novi redoslijed:

```text
1. dokazati Python voice end-to-end na stvarnoj mašini
2. zatvoriti microphone reliability i osnovnu voice dijagnostiku
3. napraviti minimalni PySide6 main shell
4. prebaciti svakodnevno pokretanje na Python-only desktop runtime
5. koristiti Python runtime kao daily driver
6. tek zatim završavati puni UI/feature parity
7. packaging
8. Windows cutover
9. obrisati Electron/React nakon soak perioda i rollback gate-a
10. Linux/macOS poslije Windows stabilizacije
```

Ovo ne znači veliki rewrite.

Naprotiv: cilj je što ranije presjeći aktivnu zavisnost od Electron-a, ali zadržati stare fajlove kao pasivni rollback dok Python verzija ne bude dovoljno dokazana.

---

# 2. Šta podrazumijevamo pod „potpuno preći na Python“

Važno je precizno definisati cilj.

## 2.1 Python-only NE znači jedan proces

Postojeća odluka iz Qt migration plana ostaje dobra:

```text
PySide6 desktop proces
+
poseban Python FastAPI backend proces
```

Oba procesa su Python.

Dakle:

```text
Python-only ≠ single-process
```

Nema potrebe sada spajati Qt event loop i FastAPI/asyncio backend u jedan proces preko `qasync` samo da bismo mogli reći da je aplikacija „potpuno Python“.

To bi povećalo rizik bez stvarne potrebe.

Za v1 ostaje:

```text
PySide6 shell
    ↓ localhost HTTP + session bearer
Python backend
```

Single-process optimizacija može biti kasniji posao samo ako mjerenje pokaže jasnu korist.

## 2.2 Python-only znači

Daily-driver aplikacija:

- ne zahtijeva Electron;
- ne zahtijeva React renderer;
- ne zahtijeva Vite;
- ne zahtijeva Node/npm za runtime;
- ne koristi `src/lib/realtime.ts` za glas;
- mikrofon i playback vode se iz Python voice runtime-a;
- OpenAI Realtime WebSocket vodi se iz `desktop/voice/`;
- UI je PySide6;
- backend je postojeći Python backend;
- svi model-facing toolovi idu kroz Python `ToolExecutor`;
- permissions i confirmations ostaju backend-controlled;
- API ključevi ostaju backend-only;
- normalni start aplikacije ide kroz `python -m desktop` ili packaged Python executable.

---

# 3. Potvrđeno trenutno stanje koda

Baseline koji je provjeren pri izradi ovog plana:

```text
repository: Rade69/nas_agent
branch:     qt-desktop-migration
HEAD:       a1733b9827d46590b586acb051498c7847d5573c
```

Napomena: agent prije svakog paketa mora ponovo provjeriti HEAD. Ovaj SHA nije naredba da se repo vraća na staro stanje.

## 3.1 Backend / agent — već Python

Prethodna migracija je već prenijela ključne slojeve u `python_backend/`:

- agent runtime;
- `ToolRegistry`;
- `ToolExecutor`;
- `PermissionEngine`;
- cancellation/execution state;
- SQLite storage;
- notes/records/artifacts;
- computer-use;
- UI Automation element targeting;
- web search;
- image generation;
- confirmations/plans;
- browser bridge;
- thumbnail domen najvećim dijelom;
- OpenAI credential minting.

Ovo se NE prepisuje.

Novi desktop mora koristiti postojeći backend.

## 3.2 Qt process bridge — urađen

Postoji:

```text
desktop/core/process_bridge.py
```

On:

- bira slobodan localhost port;
- generiše session bearer token;
- prosljeđuje token kroz env, ne komandnu liniju;
- spawn-uje Python backend;
- čeka `/health`;
- ima fail-closed startup;
- na Windowsu koristi Job Object lifecycle;
- ima frozen-safe komandu za packaged mode.

Ovo je temelj Python-only desktop aplikacije.

Ne uvoditi paralelni proces manager bez stvarnog razloga.

## 3.3 Companion orb — Python/PySide6 postoji

Postoje Qt moduli:

```text
desktop/ui/orb.py
desktop/ui/orb_window.py
desktop/ui/voice_state.py
desktop/ui/voice_bus.py
```

Orb je već portovan i povezan sa lokalnim voice signalima.

Ne vraćati HTTP polling kao primarni live signal za orb.

## 3.4 Python Realtime voice — već ozbiljno implementiran

Postoji pravi paket:

```text
desktop/voice/
    __init__.py
    audio.py
    events.py
    guards.py
    session.py
    state.py
    worker.py
```

`desktop/voice/session.py` već ima:

- OpenAI Realtime WebSocket;
- ephemeral credential sa backend-a;
- backend-authoritative model;
- `session.created` čekanje;
- `session.update`;
- PCM16 audio;
- 24 kHz mono;
- semantic VAD;
- interrupt response;
- Whisper transkripciju na srpskom;
- input/output audio queue;
- tool schemas sa backend-a;
- tool execution kroz `ToolBridge`;
- confirmation bridge;
- reconnect policy;
- duplicate call guard;
- stale generation guard;
- tool-loop guard;
- audio-level tracking;
- user/assistant transcript callbacks;
- fail-closed credential/model handling.

Ovo je novi kanonski voice engine za Python-only Ricky.

## 3.5 Voice test infrastruktura već postoji

U `desktop/tests/` postoje zasebni testovi za:

```text
process bridge
confirmation dialog
orb
realtime model
tool bridge
voice audio
voice events
voice guards
voice state
voice state machine
```

Zato plan NE smije tretirati QM-3 kao da počinje od nule.

## 3.6 Glavni PySide6 prozor još NIJE aplikacija

`desktop/main.py` trenutno pravi samo osnovni:

```text
QMainWindow
title = Ricky
size = 400x300
```

i sam komentar u kodu ga opisuje kao skelet prije QM-4/QM-5.

Ovo je trenutno najveća blokada za daily-driver Python cutover.

## 3.7 Aktivni normalni runtime još je Electron

Postojeći Node paket i dalje koristi:

```text
electron/main.cjs
Vite
React
electron-builder
```

Drugim riječima:

```text
Python backend = već dominantan
Python Qt voice = već napravljen
Python Qt UI = još nedovršen
normalni desktop start = još Electron
```

To je tačno stanje koje ovaj plan treba da promijeni.

---

# 4. Šta iz starih planova više NIJE autoritativno

`MIGRATION_PLAN.md` je istorijski važan, ali sadrži raniju voice-first hibridnu odluku:

```text
React/Electron ostaje shell
src/lib/realtime.ts ostaje glavni WebRTC audio pipeline
Python ne preuzima microphone/VAD/STT/TTS
```

Ta odluka više ne važi za `qt-desktop-migration`.

Isti projekat je kasnije eksplicitno usvojio:

```text
Electron/Chromium potpuno ukloniti
React → PySide6
WebRTC → Python WebSocket
```

Novi plan zato tretira staru zabranu Python audio pipeline-a kao:

```text
SUPERSEDED za qt-desktop-migration
```

Ne brisati istorijski dokument samo zbog toga. Dovoljno je označiti ga kao istorijski/superseded u odnosu na aktivni Qt cutover.

---

# 5. Šta iz Omarchy plana zadržavamo

Omarchy addendum ne postaje nova arhitektura projekta.

Zadržavaju se lekcije koje odgovaraju našem kodu:

- robustan Realtime lifecycle;
- reconnect;
- stale-generation zaštita;
- duplicate tool-call zaštita;
- bounded tool loop;
- direktni VoiceState signal;
- audio-reactive orb;
- jasna confirmation semantika;
- Desktop Context;
- Capability Manifest;
- deterministički compound tools tek kada mjerenje pokaže potrebu;
- observability;
- doctor/diagnostics;
- echo/duplex hardening;
- text/voice parity.

Ne kopiraju se:

- veliki monolitni `tools.py`;
- Linux-specifični Omarchy mehanizmi;
- slabiji permission sistem;
- drugi memory sistem;
- generalni shell tool;
- paralelni voice executor.

---

# 6. Status Omarchy OA faza prema trenutnom trackeru

Već završeno / uglavnom završeno:

```text
OA-0  Baseline + contract freeze                  ✅
OA-1  Production Realtime runtime                 ✅
OA-2  Centralni VoiceSignals contract             ✅
OA-3  Audio-reactive orb                          ✅ kod
OA-4  Confirmation Bridge v2                      🟡 djelimično
```

Još otvoreno:

```text
OA-5   Desktop Context Snapshot                   ⬜
OA-6   Capability Manifest                        ⬜
OA-7   Tool Surface Optimization                  ⬜
OA-8   Deterministic compound tools               ⬜
OA-9   Realtime observability                     ⬜
OA-10  Ricky Doctor / Diagnostics                 ⬜
OA-11  Echo / duplex hardening                    ⬜
OA-12  Text / Voice parity test suite             ⬜
```

Novi plan mijenja samo PRIORITET dijela ovih faza.

Zbog konkretnog problema „agent me povremeno ne čuje“, minimalni dio OA-9/OA-10 ulazi mnogo ranije nego što je ranije planirano.

---

# 7. Ciljna arhitektura

```text
┌───────────────────────────────────────────────────────────┐
│                       PySide6 Desktop                     │
│                                                           │
│ MainWindow                                                │
│ ├─ Voice controls                                        │
│ ├─ Transcript / Activity                                 │
│ ├─ Settings                                              │
│ ├─ ConfirmationDialog                                    │
│ └─ Panels                                                │
│                                                           │
│ OrbWindow                                                │
└───────────────────┬───────────────────────────────────────┘
                    │ Qt signals / slots
                    │
          ┌─────────▼──────────┐
          │ Python Voice       │
          │ desktop/voice/     │
          │                    │
          │ RealtimeWorker     │
          │ asyncio loop       │
          │ OpenAI WS          │
          │ mic/playback       │
          │ VAD/events         │
          │ reconnect/guards   │
          └─────────┬──────────┘
                    │
                    │ localhost HTTP + bearer
                    │
┌───────────────────▼───────────────────────────────────────┐
│                     Python Backend                        │
│                                                           │
│ /realtime/session                                        │
│ /tools                                                   │
│ /tools/execute                                           │
│ /confirmations                                           │
│ /plans                                                   │
│ /events                                                  │
│ /agent                                                   │
│ /thumbnails                                              │
│ browser bridge                                           │
│                                                           │
│ ToolRegistry → ToolExecutor → PermissionEngine → Handler │
│                         ↓                                 │
│               SQLite / Events / Artifacts                 │
└───────────────────────────────────────────────────────────┘
```

Electron i React u ovom modelu nisu runtime komponente.

---

# 8. Neoborive invarijante

## INV-1 — Jedan execution/security put

```text
VOICE
  ↓
ToolBridge
  ↓
POST /tools/execute
  ↓
ToolExecutor
  ↓
PermissionEngine
  ↓
handler
```

Tekstualni agent koristi isti `ToolExecutor`.

Nema posebnog „voice fast path“.

## INV-2 — API ključ backend-only

`OPENAI_API_KEY`:

- ne ide u PySide6 widget;
- ne ide u log;
- ne ide u voice worker;
- ne ide u command line;
- ne ide u agent report.

Desktop dobija samo ephemeral credential.

## INV-3 — Backend je source of truth za Realtime model

Korisnik može birati model kroz Settings, ali aktivna session dobija model iz backend odgovora:

```text
saved settings
→ backend resolve
→ mint credential
→ response.model
→ Python WS URL
→ session.update.model
```

Bez `credential + model` sesija ne počinje.

## INV-4 — Confirmation nije modelova odluka

High-risk action:

```text
model requests action
→ backend says CONFIRMATION_REQUIRED
→ UI asks human
→ human approves
→ exact approved action executes
```

Model ne smije sam „potvrditi“ sopstvenu akciju.

## INV-5 — Kill-switch ne zavisi od backend-a

Ako backend visi ili je mrtav, korisnik i dalje mora moći zaustaviti lokalni voice/computer-control runtime.

## INV-6 — Jedan audio capture

Orb audio animacija koristi nivo iz stvarnog voice input streama.

Ne otvarati drugi microphone stream samo radi animacije.

## INV-7 — Electron se prvo deaktivira, pa tek kasnije briše

Ne brisati fallback istog dana kada prvi put proradi Python daily driver.

Redoslijed:

```text
Python runtime postaje default
→ soak
→ parity
→ packaged test
→ explicit cutover
→ tek onda delete Electron/React
```

## INV-8 — Nema velikog refaktora radi estetike

Cutover ima prioritet nad savršenom arhitekturom.

Refaktori koji nisu potrebni za:
- voice stabilnost;
- daily driver;
- security;
- parity;
- packaging

odlažu se.

---

# 9. Novi execution plan

Novi plan koristi oznaku `PC` = **Python Cutover**.

Ove oznake ne zamjenjuju istorijske QM/OA brojeve; one su operativni redoslijed izvršenja preostalog posla.

Mapiranje:

```text
PC-0  → reconciliation + baseline
PC-1  → finish QM-3 live gate + microphone reliability + early OA-9/OA-10
PC-2  → QM-4 main shell
PC-3  → minimum critical subset of QM-5 + Settings/model selector
PC-4  → Python daily-driver cutover
PC-5  → remaining QM-5/QM-6 parity + OA-5/OA-6/OA-12
PC-6  → QM-7 + full OA-9/OA-10/OA-11
PC-7  → QM-8 Windows packaging
PC-8  → QM-9a Windows cutover + Electron retirement
PC-9  → QM-9b/c Linux/macOS
```

---

# 10. PC-0 — Reconciliation i novi baseline

## Cilj

Zaključati stvarno stanje prije nastavka migracije i ukloniti kontradikciju između istorijskog hibridnog plana i aktuelnog Python Qt pravca.

## Obavezni koraci

Agent prvo:

```text
git status
git branch --show-current
git log -1 --oneline
```

Mora biti na:

```text
qt-desktop-migration
```

Zatim pročitati:

```text
AGENTS.md
CLAUDE.md
docs/MIGRATION_PLAN.md
docs/QT_MIGRATION_PLAN_2026-07-20.md
NAS_AGENT_OMARCHY_LESSONS_IMPLEMENTATION_PLAN.md
desktop/main.py
desktop/core/process_bridge.py
desktop/voice/*
desktop/ui/orb*
desktop/ui/voice*
desktop/ui/tool_bridge.py
desktop/ui/confirmation_dialog.py
```

I relevantne backend module:

```text
python_backend/app/api/realtime.py
python_backend/app/core/config.py
ToolRegistry
ToolExecutor
PermissionEngine
ConfirmationService
settings schemas/repository/API
```

## Dokumentaciona korekcija

Aktuelni tracker mora jasno reći:

```text
qt-desktop-migration:
- Electron/React removal is active target
- Python WebSocket voice is active target
- old rule "src/lib/realtime.ts must remain the audio pipeline" is superseded
```

Ne prepisivati istoriju. Označiti stari dio kao superseded.

## Baseline test

Pokrenuti stvarne testove, bez hardkodiranog očekivanog broja:

```text
backend tests
desktop tests
relevant realtime tests
relevant settings tests
```

Zabilježiti stvarne brojeve.

## Gate PC-0

PASS samo ako:

- branch/HEAD poznati;
- dirty state poznat;
- dokumenti više ne daju kontradiktornu instrukciju coding agentima;
- desktop voice testovi zeleni;
- backend testovi zeleni;
- trenutni model selection flow poznat;
- trenutni settings persistence flow poznat.

---

# 11. PC-1 — Python Voice E2E + Microphone Reliability Gate

## Prioritet

**KRITIČAN.**

Ovo je prvi pravi blocker za Python daily-driver.

Python voice kod postoji, ali kod nije isto što i dokaz na korisnikovoj mašini.

## 11.1 Glavni cilj

Dokazati tok:

```text
PySide6/Python
→ microphone
→ PCM frames
→ OpenAI Realtime WebSocket
→ semantic VAD
→ transcript
→ model response
→ audio output
→ tool call
→ ToolExecutor
→ optional confirmation
→ execution result
→ spoken response
```

bez Electron/renderer voice pipeline-a.

## 11.2 Poseban problem: „agent me povremeno ne čuje“

Trenutni Python `RealtimeSession` koristi `sounddevice.RawInputStream` bez eksplicitnog `device=` argumenta.

To znači da se oslanja na sistemski default input uređaj.

Prije daily-driver cutovera mora postojati dokaziva audio-device strategija.

## 11.3 AudioDeviceService

Uvesti mali, izolovan servis/modul u okviru desktop voice sloja.

Predloženo:

```text
desktop/voice/devices.py
```

Odgovornosti:

- enumeracija input uređaja;
- enumeracija output uređaja;
- stabilan device identifier koliko PortAudio/sounddevice dozvoljava;
- human-readable naziv;
- default input/output;
- validacija izabranog uređaja;
- selected device;
- selected sample rate/channel compatibility;
- fallback ponašanje;
- health probe bez slanja audio sadržaja modelu.

Ne praviti paralelni audio engine.

## 11.4 Settings za mikrofon i zvučnik

U PySide6 Voice Settings treba imati:

```text
Microphone
[ System default ▼ ]

Speaker
[ System default ▼ ]
```

Korisnik mora moći eksplicitno izabrati uređaj.

Ako sačuvani uređaj više ne postoji:

```text
ne silent fail
```

nego:

```text
selected device unavailable
→ jasan warning
→ kontrolisani fallback na system default ILI blok starta,
   zavisno od potvrđenog UX pravila
```

Preporuka za v1:

- ako eksplicitno izabrani uređaj nestane: prikaži warning;
- ponudi system default;
- ne glumi da koristiš stari device.

## 11.5 Microphone health signal

Dodati structured runtime činjenice:

```text
voice.input_stream_opened
voice.input_frame_received
voice.input_activity
voice.input_stream_warning
voice.input_stream_error
voice.input_device_changed
```

Ne emitovati event za svaki frame u trajni log.

Agregirati.

Minimalni runtime state:

```text
input_device
input_stream_open
last_input_frame_at
input_frames_5s
input_bytes_5s
input_level_peak_5s
last_vad_speech_started_at
last_user_transcript_at
```

## 11.6 „Čuje li me?“ dijagnostika

Za debugging je potreban jasan lanac:

```text
A. Je li input stream otvoren?
B. Stižu li PCM frameovi?
C. Ima li signal RMS iznad noise floor-a?
D. Šalju li se frameovi na WS?
E. Je li WS connected?
F. OpenAI šalje li speech_started?
G. OpenAI šalje li speech_stopped?
H. Dolazi li transcript?
I. Kreira li se response?
```

Ako agent ne čuje korisnika, ovaj lanac mora omogućiti da se problem smjesti u jednu od zona.

## 11.7 Minimalni observability pomjeren unaprijed iz OA-9

Ne čekati pred-cutover fazu.

Odmah mjeriti:

```text
session_connect_start
session_created
session_connected
mic_stream_open
last_mic_frame
speech_started
speech_stopped
user_transcript
response_created
first_audio
response_done
response_failed
disconnect
reconnect
```

Derived:

```text
speech_to_first_audio_ms
mic_silence_duration
reconnect_count
failed_response_count
```

Ako event par ne postoji, metrika je `None`, ne lažna nula.

## 11.8 Log security

Nikada ne logovati:

- raw PCM;
- API key;
- ephemeral credential;
- Authorization header;
- puni osjetljivi transcript bez jasnog postojećeg privacy pravila.

## 11.9 Pregled trenutnog mic callback ponašanja

Trenutni callback na `sounddevice` status prekida obradu tog callback-a.

Agent treba posebno provjeriti:

- koje `status` vrijednosti se realno mogu javiti;
- da li transient overflow/underflow treba značiti „drop frame + warning“ ili kompletno ignorisanje;
- da li trenutni behavior može ostaviti korisnika u prividno povezanoj sesiji bez audio signala.

Ne mijenjati napamet. Reprodukovati/testirati gdje je moguće.

## 11.10 Sample-rate provjera

Realtime voice koristi:

```text
24000 Hz
mono
int16
block 480
```

Prije starta provjeriti da izabrani PortAudio device može otvoriti traženi format.

Ako ne može:

- jasan error;
- device fallback ili kontrolisana konverzija tek ako je potrebna;
- ne ostaviti sesiju u „listening“ bez input streama.

Ne uvoditi resampling dependency prije nego što je stvarno potreban.

## 11.11 Realtime model

Potvrditi oba:

```text
gpt-realtime
gpt-realtime-2.1-mini
```

Backend mora mintati credential za izabrani model, a Python WS mora koristiti backend-returned model.

## 11.12 Live E2E matrix

Za svaki model minimalno:

### Scenario V1 — običan govor
Korisnik izgovori kratko pitanje.

PASS:
- audio level reaguje;
- speech_started;
- transcript;
- odgovor se čuje.

### Scenario V2 — duži srpski turn
15–30 sekundi prirodnog govora.

PASS:
- nema prekida inputa;
- kompletna namjera razumljiva.

### Scenario V3 — kratka pauza usred rečenice
Provjera VAD-a.

### Scenario V4 — barge-in
Ricky govori, korisnik ga prekine.

### Scenario V5 — read-only tool
Npr. bezbjedan local/read alat.

### Scenario V6 — confirmation-required tool
Mora otvoriti PySide6 confirmation flow.

### Scenario V7 — network drop
Ako je praktično simulirati.

### Scenario V8 — stop/start voice
Više ciklusa u istoj desktop sesiji.

### Scenario V9 — sleep/wake ili audio-device perturbation
Ako je moguće bez destruktivnih testova.

## 11.13 Voice soak

Prije PC-2/PC-3 finalnog daily-driver gate-a:

- najmanje nekoliko dužih stvarnih razgovora;
- ponovljeni start/stop;
- test nakon promjene default Windows input device-a;
- zabilježiti svaki „ne čuje me“ slučaj kroz nove health evente.

## Gate PC-1

PASS samo ako:

```text
Python voice E2E = PASS
mic frames = dokazano
VAD = dokazano
transcript = dokazano
audio output = dokazano
tool call = dokazano
confirmation = dokazano
model selection = dokazano
no Electron voice dependency = dokazano
```

Ako „ne čuje me“ i dalje postoji, ne prelaziti preko toga kozmetikom.

---

# 12. PC-2 — PySide6 MainWindow / Composition Root

## Cilj

Pretvoriti `desktop/main.py` iz praznog 400×300 skeleta u pravi composition root.

Ovo nije full UI parity.

Cilj je minimalan, stabilan prozor koji povezuje već postojeće Python dijelove.

## 12.1 Predložena struktura

Ne mora biti tačno ovako, ali odgovornosti treba razdvojiti:

```text
desktop/
    main.py
    app_controller.py

desktop/ui/
    main_window.py
    top_bar.py
    voice_panel.py
    transcript_panel.py
    activity_panel.py
    settings_panel.py
    confirmation_dialog.py
    orb.py
    orb_window.py
```

`desktop/main.py` treba ostati composition root, ne novi monolit od hiljade linija.

## 12.2 Startup tok

Željeni startup:

```text
main()
→ QApplication
→ BackendProcess.start()
→ backend health PASS
→ security self-test minimalni gate
→ BackendClient
→ VoiceStateBus / signals
→ ToolBridge
→ RealtimeWorker controller
→ MainWindow
→ OrbWindow
→ show
```

Ako backend startup failuje:

- ne prikazivati lažno spremnu aplikaciju;
- ponuditi jasan error/retry/exit;
- ne startovati computer-control mode.

## 12.3 Shutdown tok

```text
user quit
→ voice stop
→ cancel active local voice tasks
→ cancel/stop tool executions where appropriate
→ stop backend
→ close Job Object / child process
→ Qt exit
```

Mora biti idempotentno.

## 12.4 MainWindow minimalni sadržaj

Za PC-2 je dovoljno:

```text
Top/status
Voice start/stop
Voice state
Transcript
Activity/status
Settings entry
Confirmation dialog
Orb toggle
Quit/minimize
```

Ne portovati još sve rijetke panele samo da bi prozor vizuelno ličio 1:1 na React.

## Gate PC-2

Korisnik može pokrenuti:

```text
python -m desktop
```

i dobiti pravi Ricky prozor koji:

- startuje backend;
- može startovati Python voice;
- prikazuje state;
- može stopirati voice;
- otvara confirmation;
- pravilno gasi backend;
- ne koristi Electron.

---

# 13. PC-3 — Daily-Driver Critical UI

## Cilj

Dodati samo funkcije bez kojih korisnik ne može normalno koristiti Rickyja svaki dan.

## 13.1 P0 UI komponente

### Voice controls

Mora imati:

- start;
- stop;
- mute ako postojeći contract to podržava;
- current voice state;
- reconnect/error status.

### Transcript

Minimalno:

- posljednji user transcript;
- posljednji Ricky transcript;
- scroll/history gdje postojeći backend/voice state to podržava.

### Activity

Prikaz:

- tool requested;
- tool running;
- waiting confirmation;
- success/failure;
- relevant voice connectivity status.

### Confirmation

Postojeći PySide6 `ConfirmationDialog` ostaje kanonski.

### Settings

Minimalno mora pokriti voice-critical settings.

---

# 14. PC-3A — Realtime model selector u aplikaciji

Ako do početka ove faze model selector već bude implementiran drugim commitom, agent prvo provjerava stvarni kod i samo integriše postojeće rješenje.

Ako nije, implementirati.

## Dozvoljeni modeli

```text
GPT Realtime
→ gpt-realtime

GPT Realtime 2.1 Mini
→ gpt-realtime-2.1-mini
```

## Pravilo persistence-a

Normalni izbor je user setting.

Precedence:

```text
saved user setting
→ OPENAI_REALTIME_MODEL fallback
→ gpt-realtime default
```

Env nije više normalni UX selector.

## Security

- API key ostaje backend-only;
- desktop ne bira WS model mimo backend-a;
- backend vraća authoritative model;
- voice session fail-closed ako model nedostaje.

## Session semantics

Promjena modela:

```text
save setting
→ primjenjuje se na SLJEDEĆU voice session
```

Nema potrebe za hot-swapom usred istog WebSocket-a.

---

# 15. PC-3B — Audio device Settings

Isti Settings panel treba imati:

```text
Microphone
Speaker
```

i health/status po potrebi.

Ne zatrpavati normalni ekran dijagnostikom.

Detaljni signal ide u Diagnostics.

---

# 16. PC-3C — Minimalni Voice Diagnostics ekran

Zbog trenutnog stvarnog problema ovo postaje P0, ne P4.

Mali ekran:

```text
Voice Diagnostics

Backend              OK
Realtime credential  OK
WebSocket             Connected
Model                 gpt-realtime-2.1-mini
Microphone            <device>
Mic stream            Open
Mic signal            Active / Silent
Last mic frame        0.08 s ago
VAD speech_started    ...
Last transcript       ...
Speaker               <device>
Reconnects            0
Last error             None
```

Ne treba odmah kompletan OA-10 doctor.

Cilj je dijagnostikovati „Ricky me ne čuje“.

## Gate PC-3

Korisnik može kroz PySide6 aplikaciju:

- izabrati voice model;
- izabrati mikrofon;
- izabrati speaker;
- pokrenuti razgovor;
- vidjeti da li mic zaista šalje signal;
- dobiti confirmation;
- vidjeti osnovni activity/transcript;
- stopirati razgovor.

---

# 17. PC-4 — Python Daily-Driver Cutover

## Cilj

Ovo je ključna tačka projekta.

Od ovog trenutka korisnik više ne treba da pokreće Electron za svakodnevni Ricky rad.

## 17.1 Kanonski development start

Kanonski start postaje:

```text
python -m desktop
```

ili jedan repo helper koji isključivo vodi na taj entry point.

Poželjno je dodati jednostavan Windows launcher za korisnika, ali ne uvoditi packaging prerano.

## 17.2 Electron freeze

Od ovog trenutka:

```text
electron/
src/
```

postaju:

```text
LEGACY / FALLBACK
```

Pravila:

- nema novih feature-a u Electron verziji;
- nema paralelnog bugfixa osim ako je nužan za rollback sigurnost;
- svaki novi feature ide prvo/isključivo u Python/PySide6;
- React se koristi samo kao vizuelna/funkcionalna referenca za preostali port.

## 17.3 Ne brisati još

Iako je normalni runtime Python-only, Electron ostaje u repou dok:

- daily-driver soak ne prođe;
- critical feature parity ne prođe;
- packaging ne prođe;
- korisnik eksplicitno odobri finalni Windows cutover.

## 17.4 Soak period

Ne definišemo proizvoljan broj dana kao apsolutni uslov.

Bitnije je pokriti realne scenarije:

- više voice sesija;
- restart aplikacije;
- restart računara;
- sleep/wake;
- network reconnect;
- tool use;
- confirmations;
- browser bridge;
- screenshots;
- image generation;
- notes/records;
- plans;
- thumbnails;
- promjena Realtime modela;
- promjena audio device-a.

Sve što korisnik stvarno radi treba proći kroz Python daily driver.

## Gate PC-4

PASS:

```text
normal daily use ne zahtijeva Electron
```

Od tog trenutka „hibridni runtime“ je praktično prevaziđen, iako legacy fajlovi još fizički postoje u git-u.

---

# 18. PC-5 — Preostali UI i Feature Parity

Tek poslije Python daily-driver cutovera završiti širi parity.

Prioriteti se određuju po stvarnoj upotrebi.

## 18.1 Port UI komponenti

Portovati postojeće React funkcije u male PySide6 pakete.

Svaki paket:

```text
source React component
→ existing backend contract
→ target PySide6 widget
→ focused tests
→ manual smoke
```

Ne mijenjati backend endpoint samo zato što je novi UI Python.

## 18.2 Plans

Portovati:

- list;
- open;
- create gdje postoji;
- update;
- progress/state;
- confirmation veze ako postoje.

## 18.3 Memory / notes / records

UI samo koristi postojeće Python backend API-je.

Ne uvoditi novi lokalni Qt storage.

## 18.4 Artifacts

Portovati artifact pregled.

Posebno odlučiti kako će se prikazivati:
- tekst;
- slike;
- linkovi;
- strukturisani rezultati.

## 18.5 Screenshots

Portovati list/view/clear funkcije prema postojećem API-ju.

## 18.6 Thumbnail board

Backend domen je već najvećim dijelom portovan.

Potrebno je Qt UI prikazati preko postojećih `/thumbnails` API-ja.

Ne vraćati legacy JSON board kao novi source of truth.

## 18.7 Browser Bridge

Portovati Settings/status/pairing UI na Qt.

Ne prepisivati broker/protokol.

## 18.8 Localization

Ne pokušavati odmah duplicirati cijeli i18next sistem 1:1 ako to usporava cutover.

Definisati Qt localization strategy:

- Qt translations;
- JSON/localization adapter;
- drugi jednostavan postojeći pattern.

Ali UI tekst ne smije završiti razbacan bez strategije.

## 18.9 Mermaid

Ovo je posebna stavka jer je Chromium/Puppeteer ranije bio koristan.

Prvo utvrditi stvarnu potrebu.

Moguće opcije:

- prikaz fenced code-a kao fallback;
- eksterni render servis samo ako bezbjednosno prihvatljiv;
- Python/Qt kompatibilan renderer;
- odložiti rich Mermaid preview ako nije daily-driver blocker.

Ne vraćati cijeli Chromium samo zbog Mermaid-a.

---

# 19. PC-5A — OA-5 Desktop Context Snapshot

Tek nakon stabilnog Python voice patha.

## Cilj

Model prije odluke dobija svjež mali desktop kontekst.

Minimalno:

```text
captured_at
computer_mode
active_window
bounded visible windows
monitor summary
browser bridge state
```

Sadržaj prozora/title je untrusted data.

Ne pretvarati ga u sistemsku instrukciju.

Voice i text treba da koriste kompatibilnu semantiku.

---

# 20. PC-5B — OA-6 Capability Manifest

Stabilni session-level opis mogućnosti.

Izvori:

- ToolRegistry;
- OS;
- desktop automation capability;
- browser bridge;
- audio uređaji;
- integracije.

Ne slati secrets.

Manifest nije authorization.

PermissionEngine ostaje autoritet.

---

# 21. PC-5C — OA-12 Voice/Text Security Parity

Formalna matrica.

Za isti intent:

```text
low risk
computer-mode required
confirmation required
blocked app/action
outbound action
```

voice i text moraju dobiti istu backend security odluku.

Razlika smije biti samo u UI prezentaciji/modalitetu.

---

# 22. PC-5D — OA-7/OA-8 samo nakon mjerenja

Ne optimizovati tool surface unaprijed.

Prvo izmjeriti:

- broj enabled toolova;
- schema bytes/tokens;
- selection greške;
- setup latency.

Compound tool se uvodi samo kada postojeći usage pokaže realan race/roundtrip problem.

---

# 23. PC-6 — Safety, Full Diagnostics i Voice Hardening

## 23.1 QM-7 Kill-switch

Mora biti lokalni desktop mehanizam.

Zahtjevi:

- radi kada backend odgovara;
- radi kada backend visi;
- radi tokom voice response-a;
- prekida lokalni voice playback/capture;
- blokira/zaustavlja computer control gdje je moguće;
- ponašanje je dokumentovano i testirano.

## 23.2 Security self-test

Qt shell treba imati svoj startup/security signal koji provjerava relevantne lokalne uslove bez Electron-a.

Ne kopirati Electron-specific checkove koji više nemaju smisla.

## 23.3 OA-9 full observability

Proširiti minimalne voice metrike na:

```text
voice.session_connect_start
voice.session_connected
voice.session_disconnected
voice.session_reconnect
voice.speech_started
voice.speech_stopped
voice.response_created
voice.first_audio
voice.response_done
voice.response_failed
voice.tool_requested
voice.tool_started
voice.tool_finished
voice.tool_failed
voice.confirmation_required
voice.confirmation_approved
voice.confirmation_rejected
voice.confirmation_expired
voice.rate_limit
voice.audio_underrun
voice.echo_suspected
```

Derived:

```text
speech_to_first_audio_ms
tool_duration_ms
confirmation_wait_ms
reconnect_count
failed_response_count
rate_limit_count
duplicate_call_count
```

## 23.4 OA-10 Ricky Doctor

Dodati:

```text
python -m desktop --doctor
```

ili ekvivalent.

Provjere:

```text
Qt
backend spawn/health/auth/shutdown
SQLite
Realtime configuration
input device
output device
mic capture
speaker playback
ToolRegistry
PermissionEngine
UIA
screenshot
browser bridge
capability manifest
```

Machine-readable:

```text
--json
```

Svaki FAIL treba imati fix hint.

## 23.5 OA-11 Echo/duplex

Ne mijenjati full-duplex ako nema dokaza da je problem.

Mjeriti:

- output playback aktivan;
- user VAD start za vrijeme playback-a;
- repeated false interruptions;
- echo suspected.

Half-duplex je fallback, ne default.

Ako se ikada uvede, UI mora jasno pokazati promjenu ponašanja.

## Gate PC-6

Nema tihih voice failure-a bez dijagnostičkog traga.

---

# 24. PC-7 — Windows Packaging

## Cilj

Napraviti Windows build koji ne zavisi od Node/Electron runtime-a.

## 24.1 Package target

Primarni kandidat:

```text
PyInstaller
```

Nuitka ostaje alternativa samo ako mjerenje/build problemi opravdaju promjenu.

Ne održavati dvije produkcijske packaging putanje bez potrebe.

## 24.2 Frozen lifecycle

Obavezno testirati postojeći pattern:

```text
ricky.exe
→ Qt mode

ricky.exe --backend
→ FastAPI backend child
```

`process_bridge.py` je već pisan frozen-safe i treba ga testirati, ne zaobići.

## 24.3 Bundle dependencies

Posebno provjeriti:

- PySide6 platform plugins;
- sounddevice/PortAudio;
- websockets;
- httpx;
- uvicorn/FastAPI;
- SQLite data location;
- images/assets;
- localization files;
- browser bridge assets ako ih app distribuira.

## 24.4 Secrets

`.env.local`:

- ne bundle-ovati;
- ne commitovati;
- ne logovati.

Definisati produkcijski način konfiguracije secrets prije javnog release-a.

## 24.5 Installer

Novi installer ne smije zavisiti od `electron-builder`.

Stari `electron-builder.yml` ostaje legacy dok Windows cutover nije odobren.

## Gate PC-7

Na čistom Windows test scenariju:

```text
install
launch
backend start
voice start
tool call
confirmation
quit
relaunch
uninstall
```

prolaze bez Node/npm/Electron.

---

# 25. PC-8 — Windows Cutover i Electron Retirement

## 25.1 Pre-cutover checklist

Mora biti PASS:

```text
Python daily driver
voice reliability
mic diagnostics
model selector
tool execution
confirmations
kill switch
critical feature parity
browser bridge
thumbnail parity ako je daily usage
packaged build
clean install
restart
shutdown
```

## 25.2 Eksplicitna korisnička odluka

Finalni Windows cutover nije automatski.

Korisnik eksplicitno kaže da Python build postaje jedina podržana Windows desktop verzija.

## 25.3 Electron delete sequence

Tek poslije odluke i sigurnog commita/taga:

1. napraviti tag/commit posljednjeg dual-runtime stanja;
2. potvrditi da Python build može biti vraćen;
3. ukloniti Electron runtime fajlove;
4. ukloniti React renderer;
5. ukloniti Vite;
6. ukloniti Electron dependencies;
7. ukloniti `electron-builder`;
8. ukloniti legacy npm runtime skripte;
9. ukloniti Electron-only testove;
10. očistiti dokumentaciju;
11. update `AGENTS.md`;
12. update `CLAUDE.md`;
13. update `MIGRATION_PLAN.md`;
14. update project overview;
15. novi full test/package smoke.

Kandidati za brisanje nakon provjere:

```text
electron/
src/
vite.config.*
electron-builder.yml
Electron-only assets/scripts/tests
React-only dependencies
```

Ne brisati mehanički cijele foldere bez provjere da neki asset/protocol/schema nije još potreban Python verziji.

## 25.4 Legacy PowerShell

Ako Electron-only PowerShell fallback više nema nikakav runtime poziv i Python ekvivalenti su potvrđeni:

- ukloniti ga u istom cleanup periodu;
- prije brisanja napraviti search/call-site audit.

## Gate PC-8

Repo nakon cutovera:

```text
normal runtime = Python/PySide6
voice = Python WebSocket
backend = Python
UI = PySide6
packaging = Python
Electron runtime = 0
React runtime = 0
Node runtime requirement = 0
```

---

# 26. PC-9 — Linux i macOS

Ne blokiraju Windows cutover.

## Linux

Testirati posebno:

- Wayland/X11 orb;
- always-on-top;
- transparency;
- sounddevice;
- audio device enumeration;
- keyboard/mouse automation ekvivalente;
- packaging.

Windows-specific `ctypes` computer-use dijelovi zahtijevaju platform adapter prije nego što se može tvrditi puna feature parity.

## macOS

Testirati:

- PySide6 app lifecycle;
- orb/window level;
- permissions;
- microphone;
- accessibility permissions;
- computer-use platform layer;
- signing/notarization;
- packaging.

Cross-platform cilj ne znači da Windows-only automation kod magično postaje cross-platform.

---

# 27. Voice reliability — obavezni acceptance kriteriji

Pošto je voice glavni razlog za ubrzanje migracije, definiše se poseban gate.

## VR-1 — Input stream health

Aplikacija zna:

```text
koji mic koristi
da li je stream otvoren
da li stižu frameovi
da li postoji audio signal
```

## VR-2 — Nema lažnog „listening“

Ako input stream ne radi, UI ne smije ostati zelen/idle/listening kao da je sve u redu.

## VR-3 — VAD trace

Za stvarni user govor mora postojati provjerljiv event chain.

## VR-4 — Recoverable reconnect

Mrežni prekid ne smije trajno ubiti voice bez jasnog statusa.

## VR-5 — Start/stop idempotency

Više start/stop ciklusa ne ostavlja:

- orphan mic stream;
- orphan speaker stream;
- drugi WS;
- stale callback;
- stale tool output.

## VR-6 — Device failure

Nestanak/greška audio device-a nije tiha.

## VR-7 — Model switch

Promjena Realtime modela u Settings važi za sljedeću session i jasno je provjerljiva.

## VR-8 — Barge-in

Stari playback se ne nastavlja poslije pravilnog prekida.

## VR-9 — Confirmation

Voice high-risk action ima isti security rezultat kao text.

## VR-10 — Diagnostics

Kada korisnik kaže „ne čuje me“, imamo tehnički trag koji razlikuje:

```text
mic problem
device problem
PCM problem
WS problem
VAD problem
transcription problem
response problem
playback problem
```

---

# 28. Test strategija

## 28.1 Ne hardkodirati brojeve

Plan ne propisuje „mora biti 425“ ili sličan broj.

Broj testova se mijenja.

Svaki report navodi:

```text
komanda
stvarni rezultat
pass/fail
```

## 28.2 Slojevi

### Unit
- audio helpers;
- device resolver;
- event parser;
- guards;
- settings validation;
- model resolver.

### Component
- MainWindow state;
- Settings;
- ConfirmationDialog;
- Orb;
- Diagnostics.

### Integration
- process bridge;
- backend auth;
- settings roundtrip;
- realtime session credential;
- tool bridge.

### Manual hardware
- microphone;
- speaker;
- VAD;
- echo;
- barge-in;
- device switching;
- multi-monitor;
- packaged build.

## 28.3 Voice failure injection

Gdje je moguće testirati:

```text
credential failure
missing authoritative model
WebSocket disconnect
failed response
rate limit
duplicate call_id
stale generation
tool timeout
confirmation reject
backend down
mic open failure
speaker open failure
```

---

# 29. Branch i commit disciplina

Nastaviti na:

```text
qt-desktop-migration
```

Ne praviti novi repo.

Za velike/rizične pakete preporučene task grane ili worktree.

Primjer slicing-a:

```text
feat(qt-voice): add audio device management
feat(qt-voice): add microphone health diagnostics
feat(qt-shell): wire backend and voice composition root
feat(qt-ui): add daily-driver voice shell
feat(settings): add realtime model and audio selectors
chore(runtime): make python desktop the daily-driver path
feat(qt-ui): port plans and activity
feat(qt-ui): port artifacts and screenshots
feat(qt-ui): port thumbnail board
feat(qt-ui): port browser bridge settings
feat(diagnostics): add ricky doctor
feat(security): add qt kill switch
build(qt): add windows packaging
chore(cutover): retire electron react runtime
```

Svaki commit:

- uzak scope;
- test;
- agent report gdje pravila repoa to traže;
- tracker update kada mijenja fazni status.

---

# 30. Preporučena podjela rada agenata

Ovo nije apsolutno pravilo, ali prati dosadašnji način rada.

## Claude / arhitektonski reviewer

Najrizičnije:

- PC-0 reconciliation;
- PC-1 voice lifecycle/device reliability;
- confirmation/security izmjene;
- kill-switch;
- finalni cutover review;
- Electron deletion review.

## Coding agenti

Dobri paketi:

- pojedinačni PySide6 widget portovi;
- Settings kontrole;
- diagnostics UI;
- Plans/Artifacts/Screens UI;
- thumbnail UI;
- localization wiring;
- packaging prema unaprijed definisanom specu.

## Reviewer

Svaki značajan paket mora pregledati stvarni diff, ne samo agent report.

---

# 31. STOP uslovi

Agent mora stati i prijaviti, umjesto da improvizuje, ako:

## STOP-P1

Python voice bi morao direktno izvršiti tool handler mimo backend `ToolExecutor`.

## STOP-P2

Da bi voice radio, permanentni OpenAI API key morao bi preći u desktop UI/voice proces.

## STOP-P3

Confirmation flow zahtijeva slabiju sigurnost nego postojeći backend.

## STOP-P4

MainWindow port zahtijeva veliki backend rewrite koji nije opravdan postojećim API ugovorima.

## STOP-P5

Audio reliability „rješenje“ zahtijeva drugi paralelni microphone capture.

## STOP-P6

Agent planira ukloniti Electron prije nego što postoji provjeren Python daily-driver rollback point.

## STOP-P7

Packaged Python build zahtijeva Node/Electron runtime da bi normalno radio.

## STOP-P8

Realtime model selector dozvoljava desktopu da zaobiđe backend-authoritative model.

## STOP-P9

Intermittent mic failure ostane nereprodukovan, ali agent ga proglasi riješenim bez health/observability dokaza.

## STOP-P10

Current repo state više ne odgovara ovom planu.

Tada se plan prvo revidira prema kodu.

---

# 32. Šta NE raditi tokom ubrzanog cutovera

Ne raditi:

- single-process Qt+FastAPI rewrite sada;
- QML migraciju;
- novu bazu;
- novi permission sistem;
- drugi tool registry;
- drugi memory sistem;
- MiniMax voice kao paralelni projekat prije Python cutovera;
- potpuni redizajn interfejsa;
- rewrite computer-use sistema;
- arbitrary shell tool;
- novi audio engine pored `desktop/voice`;
- generički provider framework ako nije potreban;
- port svakog vizuelnog detalja prije daily-driver gate-a;
- brisanje legacy koda prije rollback tačke.

---

# 33. Najkraći put do cilja

Ako sve ostalo zanemarimo, kritični put je:

```text
PC-0
reconcile docs/code
        ↓
PC-1
Python voice live + mic reliability + diagnostics
        ↓
PC-2
real PySide6 MainWindow / composition root
        ↓
PC-3
voice controls + transcript + confirmation + settings
        ↓
PC-4
Python becomes daily driver
        ↓
PC-5
remaining parity
        ↓
PC-6
kill switch + full diagnostics/hardening
        ↓
PC-7
Windows package
        ↓
PC-8
Windows final cutover
        ↓
delete Electron/React
```

Najvažniji milestone nije brisanje `electron/`.

Najvažniji milestone je:

> Korisnik nekoliko realnih sesija zaredom pokreće Ricky kroz `python -m desktop`, razgovara preko Python WebSocket voice runtime-a, koristi toolove i confirmations, i više nema operativnu potrebu da pokrene Electron verziju.

Od tog trenutka migracija je praktično prelomljena.

---

# 34. Definition of Done — Python-only Windows Ricky

Windows migracija je završena kada su svi sljedeći uslovi ispunjeni:

## Runtime

- PySide6 je jedini desktop UI runtime.
- Python voice je jedini voice runtime.
- FastAPI backend je Python child process.
- Electron nije potreban.
- React/Vite nisu potrebni.
- Node nije runtime dependency.

## Voice

- mikrofon eksplicitno poznat;
- speaker eksplicitno poznat;
- input frames provjerljivi;
- VAD provjerljiv;
- Realtime WS stabilan;
- reconnect bounded;
- tool guards aktivni;
- barge-in radi;
- nema tihog mic failure-a;
- diagnostics mogu locirati problem.

## Models

- korisnik bira podržani Realtime model u Settings;
- model se persistira;
- backend je autoritativan;
- nema drugog OpenAI key-a.

## Security

- ToolExecutor je jedini execution path;
- PermissionEngine važi za voice/text;
- high-risk traži confirmation;
- payload binding ostaje;
- kill-switch radi bez backend-a;
- secrets se ne izlažu.

## UI

- main window;
- orb;
- voice controls;
- transcript/activity;
- confirmations;
- settings;
- svi critical daily-use paneli.

## Features

- plans;
- memory/records gdje su dio daily use-a;
- artifacts;
- screenshots;
- thumbnails;
- browser bridge;
- image/search integrations.

## Packaging

- Python-only Windows build;
- clean install smoke;
- restart smoke;
- uninstall;
- no Electron runtime.

## Cleanup

- Electron runtime uklonjen;
- React renderer uklonjen;
- Electron packaging uklonjen;
- legacy docs jasno arhivirani/superseded;
- tracker pokazuje finalni status.

---

# 35. Prvi zadatak nakon usvajanja ovog plana

Ne počinjati sa Plans panelom, thumbnail kozmetikom ili cross-platform packagingom.

Prvi coding paket treba biti:

```text
PC-1 — PYTHON VOICE LIVE + MICROPHONE RELIABILITY
```

Obavezni rezultati:

1. Python voice session pokrenuta iz PySide6/Python test entry point-a na stvarnoj mašini.
2. Dokazan `session.created`.
3. Dokazani mic PCM frameovi.
4. Dokazan VAD.
5. Dokazan user transcript.
6. Dokazan assistant audio.
7. Dokazan read-only tool.
8. Dokazana confirmation-required akcija.
9. Dodan audio device resolver/selector ili dokumentovan konkretan razlog zašto trenutni default-device pristup ostaje.
10. Dodana minimalna mic health dijagnostika.
11. Ponovljen test sa `gpt-realtime`.
12. Ponovljen test sa `gpt-realtime-2.1-mini`.
13. Nema Electron voice procesa u tom testu.
14. Agent report sa stvarnim dokazima, ne samo unit testovima.

Tek poslije toga:

```text
PC-2 — pravi PySide6 MainWindow
```

---

# 36. Konačna odluka

Naš Agent više nije projekat u kojem treba odlučivati da li Python preuzima agent runtime.

To je već urađeno.

Preostali problem je:

```text
aktivni desktop shell i svakodnevni voice UX
```

Zato završna strategija glasi:

```text
POSTOJEĆI PYTHON BACKEND
+
POSTOJEĆI PYTHON REALTIME VOICE
+
MINIMALNI PYSIDE6 DAILY-DRIVER UI
=
RANI PYTHON CUTOVER
```

nakon čega:

```text
PARITY
+
HARDENING
+
PACKAGING
=
FINALNI ELECTRON RETIREMENT
```

Ne čekamo savršen PySide6 klon React interfejsa da bismo prestali svakodnevno koristiti hibridni runtime.

Prvo prelazimo na Python tamo gdje je najvažnije: glas, agent, toolovi, confirmations i osnovni desktop shell.

Zatim završavamo ostatak bez pritiska da održavamo dvije aktivne aplikacije.
