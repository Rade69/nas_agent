---
title: "Naš Agent — Kanonski React + PySide6 + Python Voice Cutover Master Plan"
description: "Novi kanonski implementacioni plan za Rade69/nas_agent: zadržati postojeći React/CSS/i18n GUI kao presentation layer, koristiti PySide6 kao native desktop shell sa QWebEngineView + QWebChannel mostom, zadržati postojeći Python FastAPI backend i Python OpenAI Realtime voice runtime, te ugraditi najbolje lessons-learned iz Omarchy Voice bez paralelnih execution puteva i bez ponovnog crtanja cijelog GUI-ja."
project: "nas_agent"
repository: "Rade69/nas_agent"
target_branch: "qt-desktop-migration"
baseline_date: "2026-09-10"
status: "CANONICAL_MASTER_PLAN"
authority: "highest-active-migration-plan"
strategy: "reuse-react-ui + python-owned-runtime + qt-native-shell + python-voice"
supersedes:
  - "NAS_AGENT_PYTHON_ONLY_CUTOVER_MASTER_PLAN.md u dijelovima koji zahtijevaju PySide6 redraw kompletnog React GUI-ja"
  - "docs/QT_MIGRATION_PLAN_2026-07-20.md tamo gdje pretpostavlja React -> PySide6 widget-by-widget port"
  - "stare Electron/WebRTC runtime pretpostavke iz docs/MIGRATION_PLAN.md"
preserves:
  - "postojeći Python backend"
  - "ToolRegistry / ToolExecutor / PermissionEngine"
  - "Python OpenAI Realtime WebSocket voice"
  - "BackendProcess / BackendClient"
  - "Omarchy Realtime resilience lessons"
  - "Omarchy Desktop Context i Capability Manifest ideje"
  - "Omarchy confirmation, diagnostics, observability i parity principe"
  - "postojeći React/CSS/i18n dizajn i komponente"
primary_ui_host: "PySide6 QWebEngineView"
primary_js_python_bridge: "QWebChannel"
fallback_ui_host: "pywebview + WebView2 samo ako mjerenje diskvalifikuje Qt WebEngine"
runtime_goal: "Electron-free i Node-free produkcijski runtime; React ostaje kao prebuildovan presentation bundle"
---

# Naš Agent — Kanonski React + PySide6 + Python Voice Cutover Master Plan

## 0. STATUS OVOG DOKUMENTA

Ovaj dokument je novi **kanonski plan** za nastavak migracije projekta `Rade69/nas_agent`.

Ako postoji konflikt između ovog dokumenta i ranijih planova, agent prvo provjerava stvarno stanje koda, a zatim koristi ovaj dokument kao aktivnu arhitektonsku namjeru.

Važno:

```text
KOD > OVAJ PLAN > STARI PLANOVI
```

Ako se kod značajno promijenio nakon datuma plana:

```text
STOP
→ ponovo uraditi baseline
→ revidirati pogođeni dio plana
→ tek onda implementirati
```

Ovaj dokument NE briše istorijske planove. Oni ostaju kao evidencija razvoja odluka.

---

# 1. ZAŠTO JE NAPRAVLJEN NOVI KANONSKI PLAN

Postojeća dva velika plana dala su vrijedne, ali sada djelimično konfliktne smjernice.

Prvi plan je ispravno ubrzao:

```text
Electron/WebRTC voice
→ Python WebSocket voice
→ Python-owned runtime
```

ali je pretpostavio da finalni desktop UI mora biti:

```text
React
→ potpuno ponovo nacrtan PySide6 Widgets UI
```

Današnji pregled koda pokazuje da to nije potrebno.

Drugi plan, zasnovan na lessons-learned iz `omarchy-voice`, ispravno je definisao:

```text
Realtime resilience
VoiceState + AudioLevel
Confirmation Bridge
Desktop Context
Capability Manifest
Deterministic compound tools
Observability
Diagnostics
Voice/Text parity
```

Te lekcije ostaju izuzetno vrijedne.

Novi plan zato spaja najbolje iz tri stvarna izvora:

```text
1. postojeći React GUI koji već radi
2. postojeći Python/Qt migration kod koji je već napravljen
3. Omarchy lessons-learned za ozbiljan voice desktop runtime
```

Rezultat nije full React/Electron povratak.

Rezultat nije full PySide6 redraw.

Rezultat je:

```text
PySide6 native shell
+
postojeći React presentation layer
+
QWebEngineView
+
QWebChannel
+
Python Realtime voice
+
Python FastAPI backend
```

---

# 2. NOVA CENTRALNA ARHITEKTONSKA ODLUKA

## ADR-CANON-01 — React ostaje, Electron odlazi

Kanonska odluka:

```text
NE:
React -> PySide6 redraw

DA:
React -> embedded React presentation u PySide6 shell-u
```

Drugim riječima:

```text
React nije problem.
Electron nije potreban.
Browser microphone/WebRTC voice više nije potreban.
```

React se zadržava kao:

```text
presentation layer
```

PySide6 postaje:

```text
native desktop host / lifecycle / window / OS integration layer
```

Python voice ostaje:

```text
jedini kanonski audio + Realtime runtime
```

Python backend ostaje:

```text
jedini kanonski business/security/tool runtime
```

---

# 3. ZAŠTO JE PRIMARNI HOST QWEBENGINEVIEW, A NE PYWEBVIEW

Tokom današnjeg audita prvo je razmatran:

```text
React + pywebview + Python
```

To je tehnički izvodljiva opcija i ostaje rezervni plan.

Međutim, kada se uključi stvarno stanje `qt-desktop-migration` grane i Omarchy plan, bolji primarni izbor je:

```text
PySide6 + QWebEngineView + QWebChannel
```

## 3.1 Razlog 1 — već postoji PySide6 desktop infrastruktura

Već imamo:

```text
desktop/main.py
desktop/core/process_bridge.py
desktop/voice/worker.py
desktop/voice/session.py
desktop/voice/devices.py
desktop/ui/orb*
desktop/ui/voice*
desktop/ui/tool_bridge.py
desktop/ui/confirmation_dialog.py
```

Potpuni prelazak na pywebview bi značio da dio već napravljenog Qt integration rada ponovo adaptiramo na drugi desktop host.

QWebEngineView dozvoljava da sve to ostane unutar istog Qt event loop-a.

## 3.2 Razlog 2 — RealtimeWorker je već QThread

Postojeći voice wrapper:

```text
RealtimeWorker(QThread)
```

već šalje:

```text
state_changed
audio_input_level
audio_output_level
user_transcript
assistant_transcript
confirmation_required
connected_changed
error_occurred
reconnecting
input_stream_opened
input_warning
```

To se prirodno spaja sa:

```text
QWebChannel QObject signals
```

bez nove paralelne thread/event arhitekture.

## 3.3 Razlog 3 — native companion i prozori

Već postoji PySide6 companion/orb rad.

Qt shell je prirodniji vlasnik:

```text
main window
mini computer-mode window
orb window
tray
native dialogs
global shortcuts
kill-switch
window positioning
multi-monitor behavior
```

React treba da crta sadržaj, ne da upravlja OS lifecycle-om.

## 3.4 Razlog 4 — QWebChannel je direktno namijenjen ovom problemu

QWebChannel daje:

```text
Python QObject
<-> JavaScript object
```

sa metodama, signalima i serijalizacijom.

To je bolji fit od ručnog:

```text
evaluate_js(...)
custom event string injection
thread synchronization
```

ako je Qt već naš shell.

## 3.5 Razlog 5 — manje novog koda

Pywebview bi zahtijevao:

```text
novi window host
novi bridge lifecycle
novi Python voice controller ili QThread izbjegavanje
novi native companion pristup
novi native dialog/window adapter
```

QWebEngineView uglavnom zahtijeva:

```text
WebView widget
QWebChannel bridge
React compatibility adapter
```

## 3.6 Mana QWebEngineView-a

Ne krijemo tradeoff.

Qt WebEngine znači:

```text
veći package
Chromium-based renderer
dodatni QtWebEngine procesi
```

Zadržavanje React-a svakako zahtijeva web renderer.

Cilj ovog projekta više nije:

```text
zero browser engine
```

nego:

```text
zero Electron
zero Node runtime
zero browser microphone/WebRTC voice
zero renderer-held OpenAI credential
```

## 3.7 Fallback

Ako mjerenje pokaže da:

```text
Qt WebEngine package size
ili
idle RAM
ili
startup latency
```

nije prihvatljiv, tek tada se aktivira:

```text
Fallback B:
pywebview + WebView2
```

Ne donositi tu odluku po osjećaju.

Mjeriti.

---

# 4. OPCIJE KOJE SMO RAZMOTRILI

| Opcija | React reuse | postojeći Qt reuse | Voice reuse | Rewrite rizik | Runtime težina | Odluka |
|---|---:|---:|---:|---:|---:|---|
| PySide6 Widgets full redraw | nizak | visok | visok | vrlo visok | srednja | ODBAČENO |
| pywebview + WebView2 | vrlo visok | nizak/srednji | visok | srednji | niska | FALLBACK |
| PySide6 + QWebEngineView + QWebChannel | vrlo visok | vrlo visok | vrlo visok | najniži | srednja/viša | PRIMARNI |
| Electron + React | maksimalan | nizak | stari browser voice | nizak kratkoročno | visoka | LEGACY |

Kanonski pravac:

```text
PySide6 + embedded React
```

---

# 5. PRECIZNA DEFINICIJA CILJNOG RUNTIME-A

Stari izraz:

```text
Python-only
```

više nije dovoljno precizan jer React ostaje.

Novi termin:

```text
PYTHON-OWNED DESKTOP RUNTIME
```

To znači:

## Produkcijski runtime sadrži

```text
Python executable
PySide6
Qt WebEngine
prebuildovani React bundle
Python voice
Python FastAPI backend child
SQLite
existing tool/security services
```

## Produkcijski runtime NE zahtijeva

```text
Electron
Node.js
npm
Vite dev server
electron-builder
src/lib/realtime.ts
browser getUserMedia
browser RTCPeerConnection
renderer -> OpenAI direct network
```

Node/Vite ostaju samo:

```text
development/build dependency
```

---

# 6. CILJNA ARHITEKTURA

```text
┌──────────────────────────────────────────────────────────────┐
│                     PySide6 Desktop Shell                    │
│                                                              │
│  MainWindow                                                  │
│  ├─ QWebEngineView ───────────────────────────────────────┐  │
│  │   React 19 + TypeScript + CSS + i18next               │  │
│  │                                                        │  │
│  │   App.tsx                                              │  │
│  │   PixelMockupBoard                                     │  │
│  │   Settings                                             │  │
│  │   Plans                                                │  │
│  │   Activity                                             │  │
│  │   Dictation                                            │  │
│  │   Artifacts                                            │  │
│  │   Screenshots                                          │  │
│  │   Confirmation UI                                      │  │
│  │                                                        │  │
│  │   window.ricky compatibility adapter                   │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │ QWebChannel                    │
│                             ▼                                │
│                    RickyWebBridge(QObject)                   │
│                                                              │
│  OrbWindow / native dialogs / tray / global shortcut         │
└───────────────┬──────────────────────┬───────────────────────┘
                │ Qt signals           │ BackendClient
                │                      │ localhost + bearer
                ▼                      ▼
┌──────────────────────────┐  ┌────────────────────────────────┐
│ Python Voice Runtime     │  │ Python FastAPI Backend         │
│ desktop/voice/           │  │                                │
│                          │  │ ToolRegistry                   │
│ RealtimeWorker QThread   │  │ ToolExecutor                   │
│ RealtimeSession          │  │ PermissionEngine               │
│ sounddevice              │  │ Confirmations                  │
│ OpenAI Realtime WS       │  │ Plans                          │
│ VAD                      │  │ Events                         │
│ transcript               │  │ Settings                       │
│ playback                 │  │ Browser Bridge                 │
│ reconnect / guards       │  │ Desktop automation             │
└────────────┬─────────────┘  └────────────────────────────────┘
             │
             ▼
       OpenAI Realtime
       ephemeral only
```

---

# 7. ŠTA TAČNO ZADRŽAVAMO

## 7.1 React UI

Zadržati kao kanonski presentation layer:

```text
src/App.tsx
src/components/*
src/components/pixel/*
src/styles/*
src/i18n/*
src/shared/*
assets/*
```

Ne precrtavati ove komponente u PySide6 widgete bez posebnog razloga.

## 7.2 React/CSS dizajn

Zadržati:

```text
PixelMockupBoard
IdleScreen
DictationScreen
SettingsPanel
PlansPanel
ActivityTimeline
ArtifactPanel
ScreenshotsGallery
Sidebar
TopBar
RickyOrb
ConfirmationDialog
MiniComputerWindow
```

Zadržati postojeće:

```text
CSS variables
gradients
animations
responsive layout
SVG icon system
i18next
Mermaid renderer
```

## 7.3 Python backend

Ne prepisivati:

```text
ToolRegistry
ToolExecutor
PermissionEngine
settings persistence
confirmations
plans
events
SQLite
computer-use
browser bridge
image/search
thumbnail backend
```

## 7.4 Python process bridge

Zadržati:

```text
desktop/core/process_bridge.py
BackendProcess
BackendClient
session bearer
random localhost port
health gate
Windows Job Object
frozen-safe backend spawn
```

## 7.5 Python voice

Zadržati:

```text
desktop/voice/session.py
desktop/voice/worker.py
desktop/voice/audio.py
desktop/voice/events.py
desktop/voice/guards.py
desktop/voice/state.py
desktop/voice/devices.py
```

## 7.6 ToolBridge

Zadržati postojeći backend-only execution put.

Ne uvoditi drugi React/native tool executor.

---

# 8. ŠTA MIJENJAMO

## 8.1 Electron preload

Trenutni:

```text
electron/preload.cjs
```

zamjenjuje:

```text
RickyWebBridge(QObject)
+
QWebChannel
+
React window.ricky adapter
```

## 8.2 Electron IPC

Trenutni:

```text
ipcRenderer.invoke(...)
ipcMain.handle(...)
```

postepeno odlazi.

Umjesto toga:

```text
React
→ QWebChannel
→ Python RickyWebBridge
→ BackendClient / native shell / voice worker
```

## 8.3 Electron BrowserWindow

Zamjena:

```text
QMainWindow
+
QWebEngineView
```

## 8.4 Browser voice

Penzionisati:

```text
src/lib/realtime.ts
```

kao runtime voice engine.

Može privremeno ostati u repou za rollback/test referencu.

Na kraju više ne smije biti importovan u produkcijski React bundle.

---

# 9. ŠTA NE BRIŠEMO

React se NE briše.

Poslije finalnog cutovera brišemo:

```text
electron/
Electron runtime dependencies
electron-builder
Electron-only preload/IPC
Electron-only tests
old WebRTC voice implementation
```

ali zadržavamo:

```text
src/
React
TypeScript
Vite build tooling
CSS
assets
i18next
Mermaid
```

Node ostaje developer dependency, ne end-user runtime dependency.

---

# 10. WINDOW.RICKY KOMPATIBILNOST KAO MIGRACIONA GRANICA

Najvažniji frontend contract već postoji:

```text
window.ricky
```

Ne želimo mijenjati svaku React komponentu odjednom.

Novi frontend adapter treba zadržati isti API oblik koliko god je razumno.

Primjer:

```text
React component
→ window.ricky.getSettings()
→ QWebChannel adapter
→ RickyWebBridge.getSettings()
→ BackendClient
→ GET /settings
```

Isto za:

```text
updateSettings
executeTool
listPlans
createPlan
updatePlan
updatePlanStep
listEvents
confirmations
rewriteText
screenshots
browser bridge
window controls
voice controls
```

Cilj:

```text
React components ne moraju znati da je Electron nestao.
```

---

# 11. NOVI PYTHON WEB BRIDGE

Predložena struktura:

```text
desktop/web/
    __init__.py
    main_view.py
    bridge.py
    bridge_types.py
    asset_server.py       # samo ako bude potrebno
```

Tačni nazivi nisu dogma.

## RickyWebBridge

Mora biti:

```text
QObject
```

sa uskim allowlisted slotovima.

Ne izlagati generički:

```text
request(url, ...)
execute(command)
run_shell(...)
read_file(any_path)
```

## Metode

Minimalni families:

```text
settings
plans
confirmations
events
tools
screenshots
text rewrite
browser bridge
native file dialog
window lifecycle
voice lifecycle
```

## Signali Python -> React

Predloženo:

```text
voiceStateChanged
voiceInputLevelChanged
voiceOutputLevelChanged
voiceConnectedChanged
voiceUserTranscript
voiceAssistantTranscript
voiceError
voiceReconnecting
voiceInputStreamOpened
voiceInputWarning
confirmationRequired
killSwitchTriggered
companionVoiceToggle
```

QWebChannel šalje signale direktno JS klijentu.

---

# 12. REACT BRIDGE ADAPTER

Dodati jedan centralni modul, npr.:

```text
src/lib/rickyBridge.ts
```

Odgovornosti:

```text
čekati WebChannel initialization
kreirati window.ricky compatibility API
normalizovati Promise/error behavior
pretplatiti se na Python signale
emitovati React-facing typed događaje
```

Ne dozvoliti da svaka React komponenta direktno koristi:

```text
QWebChannel internals
```

## Dev adapter

U Vite standalone dev modu mora postojati kontrolisan način:

```text
mock bridge
ili
dev backend bridge
```

ali ne silent production fallback.

Produkcija mora failovati jasno ako native bridge nije dostupan.

---

# 13. APP.TSX REFAKTOR

`App.tsx` se ne precrtava, ali se razdvaja.

Trenutno sadrži i:

```text
UI state
voice transport
tool callbacks
polling
dictation state machine
confirmation orchestration
```

Cilj:

```text
App.tsx = composition + application state
```

Voice se izdvoji u:

```text
useRickyVoice()
```

ili ekvivalent.

Backend/polling u:

```text
useBackendEvents()
useConfirmations()
```

Ne raditi veliki aesthetic refactor.

Samo dovoljno da:

```text
RickyRealtimeClient
```

više nije vezan direktno za React root.

---

# 14. PYTHON VOICE JE JEDINI KANONSKI VOICE ENGINE

Kanonski put:

```text
microphone
→ sounddevice
→ PCM16
→ Python RealtimeSession
→ OpenAI Realtime WebSocket
→ Python playback
```

Nema:

```text
navigator.mediaDevices.getUserMedia
RTCPeerConnection
RTCDataChannel
HTMLAudioElement
browser AudioContext
browser microphone permission
```

za produkcijski voice.

---

# 15. POSTOJEĆI REALTIMESESSION — ZADRŽATI I DOVRŠITI PARITY

Ne praviti novi voice engine.

Potrebno je samo provjeriti parity funkcije koje stari React `RickyRealtimeClient` danas pruža.

Posebno:

```text
start
stop
text message into active Realtime session
dictation mode toggle
confirmation resolution result
barge-in
reconnect
audio levels
transcripts
```

Ako Python RealtimeSession nema neku od tih komandi:

```text
dodati thread-safe inbox command
```

umjesto da se dio funkcije zadrži u browseru.

Primjer:

```text
send_text
set_dictation_mode
stop
approve_confirmation
reject_confirmation
```

Sve ide u isti session command queue.

---

# 16. OMARCHY LEKCIJE — OSTAJU KANONSKE

Ovaj plan ne umanjuje Omarchy addendum.

Naprotiv, prenosi ga u novu React+Qt arhitekturu.

## OA-1 — Realtime resilience

Zadržati/provjeriti:

```text
bounded reconnect
backoff
manual disconnect distinction
failed response handling
rate limit handling
duplicate call_id guard
stale generation guard
bounded tool loop
barge-in correctness
```

## OA-2 — Centralni Voice Event Bus

Raniji plan je bio Qt-centric.

Nova verzija:

```text
RealtimeWorker signals
→ central VoiceState/VoiceEvent owner
→ native Orb
→ QWebChannel
→ React
```

Jedan source of truth.

## OA-3 — Audio reactive orb

Audio level iz:

```text
istog Python PCM streama
```

Nikada drugi microphone capture.

React main orb i native companion mogu koristiti isti level.

## OA-4 — Confirmation Bridge v2

Kanonski princip ostaje:

```text
model requests tool
→ ToolExecutor
→ PermissionEngine
→ CONFIRMATION_REQUIRED
→ human approval
→ exact original pending action
→ structured execution result
→ model
```

Ne:

```text
"korisnik je odobrio, pokušaj ponovo"
```

kao nova obična user poruka.

## OA-5 — Desktop Context Snapshot

Ostaje.

## OA-6 — Capability Manifest

Ostaje.

## OA-7 — Tool Surface Optimization

Samo nakon mjerenja.

## OA-8 — Deterministic Compound Tools

Samo kada usage dokaže potrebu.

## OA-9 — Observability

Minimalni dio rano, puni dio kasnije.

## OA-10 — Ricky Doctor

Ostaje.

## OA-11 — Echo/Duplex Hardening

Ostaje nakon mjerenja.

## OA-12 — Voice/Text Security Parity

Obavezni formalni gate.

---

# 17. SIGURNOSNE INVARIJANTE

## INV-1 — Jedan execution path

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

React UI nikad ne izvršava model-facing handler direktno.

## INV-2 — Backend-only permanent secrets

`OPENAI_API_KEY`:

```text
ne ide u React
ne ide u QWebChannel
ne ide u WebEngine JS
ne ide u RealtimeWorker
ne ide u log
```

Desktop voice dobija samo ephemeral credential.

## INV-3 — Backend-authoritative Realtime model

```text
saved user setting
→ backend resolve
→ credential mint
→ response.model
→ Python WS URL
→ session.update.model
```

Bez credential + authoritative model:

```text
FAIL CLOSED
```

## INV-4 — Confirmation je ljudska odluka

Model ne može sam potvrditi svoju akciju.

## INV-5 — Approval je payload-bound

Minimalno:

```text
confirmation_id
tool_name
payload binding/hash
expiry
execution context
```

## INV-6 — Kill-switch je lokalni

Mora raditi i ako backend:

```text
hang
offline
dead
```

## INV-7 — Jedan microphone capture

Nema drugog streama za:

```text
orb
meter
diagnostics
```

## INV-8 — React bridge je allowlisted

Ne izlagati generalni Python object graph JS-u.

## INV-9 — Renderer nema direktni OpenAI network access

Nakon Python voice cutovera production CSP treba ukloniti potrebu za:

```text
api.openai.com
wss://*.openai.com
```

u React rendereru.

## INV-10 — Rollback prije delete-a

Electron se prvo deaktivira.

Tek kasnije briše.

---

# 18. AUDIO RELIABILITY OSTAJE KRITIČNI PRIORITET

Prethodni Python Cutover plan je bio ispravan što je ovaj problem stavio rano.

Ne odgađati.

Python voice već ima:

```text
AudioDeviceService
input_device
output_device
input stream opened signal
input warning
audio input level
audio output level
```

Agent prije izmjena mora provjeriti šta je već završeno.

Ne implementirati drugi put samo zato što stari plan kaže da nedostaje.

---

# 19. VOICE HEALTH CONTRACT

Aplikacija mora znati:

```text
selected input device
selected output device
input stream open
last input frame
input frames / short window
input bytes / short window
input level
last VAD speech_started
last VAD speech_stopped
last user transcript
WS connected
current effective Realtime model
reconnect count
last voice error
```

Ne zapisivati svaki PCM frame.

Agregirati.

---

# 20. "RIKI ME NE ČUJE" DIJAGNOSTIKA

Mora biti moguće dokazati gdje se lanac prekida:

```text
A. Audio device postoji?
B. Input stream se otvorio?
C. PCM frameovi stižu?
D. RMS pokazuje signal?
E. Frameovi idu na WebSocket?
F. WebSocket je connected?
G. speech_started stiže?
H. speech_stopped stiže?
I. transcript stiže?
J. response se kreira?
K. first audio stiže?
L. speaker playback radi?
```

Ako je odgovor na jednu tačku NE:

```text
problem je lokalizovan
```

Nema više:

```text
"ne čuje me, ne znamo zašto"
```

kao prihvatljivog stanja.

---

# 21. REALTIME MODEL SELECTOR — ZADRŽATI POSTOJEĆI REACT UI

Postojeći Settings React UI već ima model selector.

Ne precrtavati ga.

Backend ostaje autoritet.

Agent mora koristiti aktuelni backend allowlist iz koda.

Ne hardkodirati stari plan ako se model IDs promijene.

Aktuelno provjereni kod koristi:

```text
gpt-realtime-2.1
gpt-realtime-2.1-mini
```

i frontend treba prikazati user-friendly labele.

Promjena modela:

```text
save
→ next voice session
```

Ne hot-swap usred aktivnog WS-a.

---

# 22. SETTINGS ZA AUDIO DEVICE

Zadržati postojeći React Settings panel i dodati:

```text
Microphone
[ device ▼ ]

Speaker
[ device ▼ ]
```

Podaci dolaze iz Python `AudioDeviceService`.

React ne poziva PortAudio.

Flow:

```text
SettingsPanel
→ window.ricky.listAudioDevices()
→ QWebChannel
→ AudioDeviceService
```

Save:

```text
SettingsPanel
→ backend/native settings
→ persisted selected device identity/index
```

Tačna persistence lokacija se prvo provjerava u kodu.

Ne uvoditi paralelni settings DB.

---

# 23. SCREENSHOT I FILE ASSET STRATEGIJA

Trenutni React koristi lokalne `file://` putanje na nekim mjestima.

To ne prenositi slijepo.

Kanonski pristup:

```text
app-owned local resource URL
ili
QWebEngine custom scheme
ili
controlled data URL za male resurse
```

Cilj:

```text
React ne dobija arbitrary filesystem browsing capability.
```

Screenshot gallery ostaje React komponenta.

Mijenja se samo source transport.

---

# 24. NATIVE OPEN/SAVE DIALOG

Trenutni Electron native dialog kod se portuje u PySide6:

```text
QFileDialog
```

React API ostaje konceptualno isti:

```text
addThumbnailReference()
saveThumbnailAs()
saveDictationAs()
```

Security sandbox pravila ostaju Python/backend-controlled.

---

# 25. WINDOW CONTROLS

Postojeći React buttons:

```text
minimize
maximize/restore
close
```

zadržati.

QWebChannel metode:

```text
minimizeApp
toggleMaximizeApp
quitApp
```

izvršava PySide6 shell.

Drag region:

```text
Electron -webkit-app-region
```

zamijeniti Qt-aware drag ponašanjem.

Ne mijenjati kompletan TopBar.

---

# 26. MAIN WINDOW

Novi pravi `desktop/main.py` više ne pravi prazni 400x300 shell.

Treba:

```text
QApplication
BackendProcess.start()
backend health
security gate
ToolBridge
RealtimeWorker
Voice event owner
QMainWindow
QWebEngineView
QWebChannel
load React bundle
OrbWindow
show
```

Shutdown:

```text
stop voice
cancel local session
cancel relevant executions
stop backend
close child/job object
close windows
QApplication exit
```

Idempotentno.

---

# 27. REACT BUNDLE

Vite ostaje.

Production:

```text
npm run build
→ web_dist/
```

Preporuka:

```text
ne koristiti ./dist kao Vite output
```

ako PyInstaller takođe koristi `dist/`.

Predloženo:

```text
web_dist/
```

ili:

```text
frontend_dist/
```

Tačno ime izabrati jednom i centralizovati.

---

# 28. DEVELOPMENT WORKFLOW

## Normalni React development

Može ostati:

```text
Vite dev server
```

ali se koristi samo u dev modu.

PySide6 shell u dev modu može:

```text
load localhost Vite URL
```

Production:

```text
load packaged web_dist/index.html
```

Bridge mora imati isti contract u oba moda.

## Bez native hosta

React standalone dev treba imati:

```text
explicit mock/dev adapter
```

Ne smije slučajno izgledati kao production-ready ako bridge ne postoji.

---

# 29. CSP NAKON CUTOVERA

Pošto React više ne razgovara direktno sa OpenAI-jem:

production CSP treba pooštriti.

Izbaciti renderer potrebu za:

```text
https://api.openai.com
wss://*.openai.com
mediastream:
```

gdje više nije potrebna.

Dozvoliti samo ono što stvarni React bundle treba.

Ne raditi CSP relax da bi se "brzo riješio" bridge problem.

---

# 30. COMPANION ORB — NAJBOLJI SPOJ SA OMARCHY PLANOM

Kanonski primarni izbor:

```text
zadržati postojeći PySide6 OrbWindow
```

Razlog:

```text
već postoji
native always-on-top ponašanje
direktni Qt voice signals
audio reactive signal
nema drugog WebEngine prozora
nema transparent webview input problema
```

React `RickyOrb` ostaje za glavni React GUI.

Native orb i React orb moraju koristiti:

```text
isti VoiceState
isti audio level source
```

Ne moraju biti isti rendering engine.

---

# 31. MINI COMPUTER MODE WINDOW

Ovdje je cilj zadržati postojeći React `MiniComputerWindow`.

Predloženo:

```text
PySide6 frameless always-on-top mini window
└─ QWebEngineView
   └─ isti React bundle ?window=mini&mode=computer
```

To je spike.

Ako dodatni QWebEngineView pravi previsok trošak ili transparent/window behavior problem:

```text
fallback = mali native PySide6 mini controller
```

Ali ne precrtavati prije nego što spike pokaže potrebu.

---

# 32. CONFIRMATION UI

Primarni main-window confirmation može ostati postojeći React `ConfirmationDialog`.

Approval put:

```text
React dialog
→ QWebChannel
→ backend ConfirmationService
→ exact pending action
```

Za Computer Mode kada main window nije praktično dostupan:

```text
existing PySide6 ConfirmationDialog
```

može ostati kao native fallback.

Važno:

```text
dva prikaza smiju postojati
ali samo jedan ConfirmationService/source of truth
```

Nema duplicate execution.

---

# 33. CENTRALNI VOICE STATE

Kanonski state owner mora biti jedan.

Primjer:

```text
RealtimeWorker
→ VoiceStateBus / VoiceSignals
```

Consumers:

```text
React via QWebChannel
PySide6 OrbWindow
native confirmation status
diagnostics
```

Ne imati:

```text
React voice state
Qt voice state
backend voice state
```

koji nezavisno nagađaju.

---

# 34. AUDIO LEVEL SIGNAL

Input i output level već dolaze iz Python voice engine-a.

UI throttling:

```text
10-30 updates/sec
```

Početni cilj:

```text
20 Hz
```

ali izmjeriti.

Ne slati audio-level update kroz persistent backend event log.

To je live UI signal.

---

# 35. CONFIRMATION BRIDGE V2 — OBAVEZAN PRIJE DAILY DRIVER GATE-A

Provjeriti trenutni Python `RealtimeSession` i `ToolBridge`.

PASS samo ako:

```text
high-risk tool
→ backend returns confirmation required
→ pending exact tool call se čuva
→ human approve
→ isti original tool/payload se izvršava
→ single-use confirmation
→ structured result ide modelu
```

Testirati:

```text
payload mismatch
expiry
double approve
reject
cancel
same-turn self confirmation
stale call_id
```

---

# 36. DESKTOP CONTEXT SNAPSHOT — OMARCHY OA-5

Implementirati poslije stabilnog voice/React host cutovera.

Minimalno:

```text
captured_at
computer_mode
active_window
bounded visible_windows
monitor summary
browser bridge status
```

Window titles i UI content su:

```text
UNTRUSTED DATA
```

Ne model instructions.

Voice i text dobijaju kompatibilnu semantiku.

---

# 37. CAPABILITY MANIFEST — OMARCHY OA-6

Session-level relativno stabilan context:

```text
available tool groups
OS/platform
desktop automation capability
browser bridge
audio devices summary
configured integrations
```

Ne secrets.

Manifest:

```text
capability != authorization
```

PermissionEngine ostaje autoritet.

---

# 38. TOOL SURFACE — OMARCHY OA-7

Ne optimizovati unaprijed.

Mjeriti:

```text
enabled tools count
schema bytes
estimated tokens
session setup time
tool selection errors
```

Tek ako postoji dokaz problema:

```text
essential tools
specialized tools
safe discovery
```

PermissionEngine se ne mijenja.

---

# 39. DETERMINISTIC COMPOUND TOOLS — OMARCHY OA-8

Uvesti samo kada realni usage pokaže problem.

Kandidati ostaju:

```text
app_launch_and_wait
app_focus_or_launch
window_wait
browser_open_and_wait
window_arrange
```

Nema:

```text
general shell
arbitrary powershell
arbitrary subprocess
```

Compound risk >= najrizičniji mutirajući child step.

---

# 40. OBSERVABILITY — OMARCHY OA-9

Minimalno rano:

```text
voice.session_connect_start
voice.session_connected
voice.session_disconnected
voice.session_reconnect

voice.input_stream_open
voice.input_warning

voice.speech_started
voice.speech_stopped

voice.user_transcript
voice.response_created
voice.first_audio
voice.response_done
voice.response_failed
```

Tool:

```text
voice.tool_requested
voice.tool_started
voice.tool_finished
voice.tool_failed
```

Confirmation:

```text
voice.confirmation_required
voice.confirmation_approved
voice.confirmation_rejected
voice.confirmation_expired
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

Missing event pair:

```text
None
```

ne lažna nula.

---

# 41. RICKY DOCTOR — OMARCHY OA-10

Zadržati CLI:

```text
python -m desktop --doctor
```

Provjere:

```text
PySide6
Qt WebEngine
QWebChannel
React bundle found
backend spawn
backend auth
SQLite
Realtime config
input device
output device
mic capture
speaker playback
ToolRegistry
PermissionEngine
UIA
screenshot
browser bridge
Capability Manifest
```

Machine-readable:

```text
--json
```

Svaki FAIL:

```text
cause
+
fix hint
```

---

# 42. ECHO / DUPLEX — OMARCHY OA-11

Ne mijenjati full-duplex unaprijed.

Mjeriti:

```text
playback active
user VAD during playback
false interruption
echo suspected
```

Half-duplex samo kao:

```text
measured fallback
```

Ako se uključi, UI mora jasno reći.

---

# 43. VOICE/TEXT PARITY — OMARCHY OA-12

Formalna matrix:

```text
LOW RISK
COMPUTER MODE REQUIRED
CONFIRMATION REQUIRED
BLOCKED ACTION
OUTBOUND ACTION
```

Za isti intent:

```text
voice security decision
=
text security decision
```

Razlika smije biti samo:

```text
modalitet/UI prezentacija
```

---

# 44. NOVI FAZNI SISTEM

Novi kanonski prefiks:

```text
CR = Canonical Runtime
```

Mapiranje sa starim planovima je informativno.

```text
CR-0  Baseline + reconciliation
CR-1  Embedded React host spike
CR-2  QWebChannel compatibility bridge
CR-3  Python voice + React integration
CR-4  Voice reliability + confirmation gate
CR-5  Main daily-driver cutover
CR-6  Native windows / companion / computer mode parity
CR-7  Remaining UI/backend parity cleanup
CR-8  Omarchy context/capability/parity
CR-9  Full diagnostics/observability/hardening
CR-10 Packaging + Windows cutover
CR-11 Electron retirement
CR-12 Linux/macOS/Omarchy OS follow-up
```

---

# 45. CR-0 — BASELINE I RECONCILIATION

## Cilj

Zaključati stvarno trenutno stanje.

## Obavezno

```text
git status
git branch --show-current
git log -1 --oneline
```

Branch:

```text
qt-desktop-migration
```

Pročitati:

```text
AGENTS.md
CLAUDE.md

NAS_AGENT_PYTHON_ONLY_CUTOVER_MASTER_PLAN.md
NAS_AGENT_OMARCHY_LESSONS_IMPLEMENTATION_PLAN.md
docs/QT_MIGRATION_PLAN_2026-07-20.md
docs/MIGRATION_PLAN.md

src/App.tsx
src/lib/realtime.ts
src/vite-env.d.ts
src/components/pixel/*
src/components/ArtifactPanel.tsx
src/components/CompanionOrb.tsx
src/styles/*

desktop/main.py
desktop/core/process_bridge.py
desktop/voice/*
desktop/ui/orb*
desktop/ui/voice*
desktop/ui/tool_bridge.py
desktop/ui/confirmation_dialog.py

python_backend realtime/settings/tools/permission/confirmation modules
```

## Test baseline

Pokrenuti aktuelne:

```text
backend tests
desktop tests
React/Vitest tests
typecheck/build
relevant integration tests
```

Ne hardkodirati očekivani broj.

## Gate CR-0

PASS kada:

```text
HEAD poznat
dirty state poznat
test baseline poznat
React window.ricky contract poznat
voice contract poznat
backend security contract poznat
stari dokumenti označeni kao superseded tamo gdje su konfliktni
```

---

# 46. CR-1 — EMBEDDED REACT HOST SPIKE

## Cilj

Dokazati da trenutni React UI možemo prikazati bez Electron-a i bez redraw-a.

## Implementirati minimalni spike

```text
QApplication
QMainWindow
QWebEngineView
load existing Vite production bundle
```

Bez toolova i voice-a je u redu za ovaj prvi spike.

## Obavezno vizuelno provjeriti

```text
IdleScreen
TopBar
Sidebar
Settings
Plans drawer layout
Dictation
Artifact panel layout
responsive behavior
SVG icons
avatar assets
i18next
Mermaid
```

## Screenshot parity

Uporediti sa Electron verzijom na istoj rezoluciji.

Cilj nije pixel-perfect automated diff u prvoj iteraciji.

Ali ne prihvatiti:

```text
fundamental layout break
fonts missing
assets missing
CSS cascade broken
SVG broken
scroll broken
```

## Izmjeriti

```text
cold start time
idle RAM
process count
web bundle load time
packaged-size estimate
```

Sačuvati kao baseline.

## Gate CR-1

PASS:

```text
existing React GUI renders correctly in QWebEngineView
Electron nije pokrenut
nema ponovnog crtanja UI-ja
```

Ako FAIL zbog fundamentalnog QWebEngine problema:

```text
tek tada pywebview fallback spike
```

---

# 47. CR-1B — PYWEBVIEW FALLBACK SPIKE

Ova faza se NE radi ako CR-1 prođe i mjerne vrijednosti su prihvatljive.

Aktivira se samo ako Qt WebEngine ima ozbiljan problem.

Testirati:

```text
pywebview
Windows WebView2
existing React bundle
window controls
bridge
multi-window feasibility
package size
RAM
```

Odluka mora biti dokumentovana mjerenjem.

Ne raditi obje host arhitekture paralelno dugoročno.

---

# 48. CR-2 — QWEBCHANNEL COMPATIBILITY BRIDGE

## Cilj

Zamijeniti Electron preload/IPC bez izmjene desetina React komponenti.

## Python

Implementirati:

```text
RickyWebBridge(QObject)
```

## JavaScript

Implementirati:

```text
src/lib/rickyBridge.ts
```

koji kreira:

```text
window.ricky
```

## Prvi endpointi

```text
getSettings
updateSettings

listPlans
createPlan
getPlan
updatePlan
updatePlanStep

listEvents

listPendingConfirmations
approveConfirmation
rejectConfirmation
cancelConfirmation

rewriteText

listScreenshots
deleteAllScreenshots

getBrowserBridgeStatus
startBrowserPairing
getBrowserPairingStatus
cancelBrowserPairing

minimizeApp
toggleMaximizeApp
quitApp
```

Tool execute može biti uključen u ovoj fazi ili CR-3, zavisno od slicing-a.

## Gate CR-2

React Settings/Plans/Activity rade kroz:

```text
React
→ QWebChannel
→ Python
→ BackendClient
→ FastAPI
```

bez Electron IPC-a.

---

# 49. CR-3 — PYTHON VOICE + REACT INTEGRACIJA

## Cilj

Postojeći React voice UX vozi postojeći Python Realtime voice engine.

## React više NE kreira

```text
RickyRealtimeClient
RTCPeerConnection
microphone stream
AudioContext
OpenAI SDP request
```

## Novi flow

```text
React mic button
→ window.ricky.startVoice()
→ QWebChannel
→ RealtimeWorker.start()
```

State:

```text
RealtimeWorker.state_changed
→ QWebChannel
→ React
→ existing setVoiceState()
```

Transcript:

```text
RealtimeWorker.user_transcript
→ React transcript state
```

Output:

```text
RealtimeWorker.assistant_transcript
→ React transcript state
```

Audio level:

```text
RealtimeWorker.audio_input_level
→ QWebChannel
→ React orb
```

## Text message

Existing text prompt mora raditi.

Ako Python session nema sendText parity:

```text
dodati session inbox command
```

## Dictation

Existing React DictationScreen ostaje.

Python session dobija:

```text
setDictationMode(True/False)
```

koji kontroliše Realtime session.update.

## Gate CR-3

PASS:

```text
React UI
+
Python mic
+
Python OpenAI WS
+
Python speaker
```

radi E2E bez `src/lib/realtime.ts`.

---

# 50. CR-4 — VOICE RELIABILITY + CONFIRMATION GATE

## Prioritet

KRITIČAN.

## Scenario matrix

Za oba aktuelna Realtime modela:

### V1 normalan kratki govor

```text
mic signal
speech_started
transcript
assistant audio
```

### V2 15-30 sec srpski turn

### V3 kratka pauza u rečenici

### V4 barge-in

### V5 read-only tool

### V6 confirmation-required tool

### V7 reject confirmation

### V8 repeated start/stop

### V9 network disturbance

### V10 audio device change

### V11 reconnect

### V12 text prompt through same active session

### V13 dictation enter/exit

## Gate CR-4

```text
Python voice E2E PASS
ToolExecutor path PASS
PermissionEngine PASS
confirmation exact-retry PASS
no browser mic PASS
no direct renderer OpenAI PASS
diagnostics enough to locate mic problem PASS
```

---

# 51. CR-5 — DAILY-DRIVER CUTOVER

## Cilj

Normalni development/user start:

```text
python -m desktop
```

pokreće novu arhitekturu.

Flow:

```text
Python shell
→ backend
→ React WebEngine UI
→ Python voice
```

Electron ostaje samo rollback.

## Electron freeze

Od ovog trenutka:

```text
electron/
```

dobija status:

```text
LEGACY / FALLBACK
```

Nema novih feature-a.

React nije legacy.

## Soak

Pokriti realan rad:

```text
voice
text
settings
model switching
device switching
tools
confirmations
plans
screenshots
image generation
browser bridge
computer mode
restart
sleep/wake
network reconnect
```

## Gate CR-5

Korisnik više nema operativnu potrebu za Electron verzijom.

---

# 52. CR-6 — NATIVE WINDOWS / COMPANION / COMPUTER MODE

## 6A Native PySide6 Orb

Zadržati i povezati na centralni VoiceState.

Provjeriti:

```text
always on top
drag
lock
multi-monitor
audio reactivity
stop
open main
tray
```

## 6B React MiniComputerWindow

Spike kroz drugi:

```text
QWebEngineView
```

u malom native PySide6 host window-u.

## 6C Confirmation while main hidden

Koristiti:

```text
native ConfirmationDialog
```

ako je potrebno.

Nema duplicate pending actiona.

## 6D Kill switch

Global:

```text
Ctrl+Alt+K
```

ili potvrđeni postojeći shortcut.

Mora lokalno:

```text
stop voice
stop playback
cancel local computer-control state
request backend cancellation best-effort
```

Backend failure ne blokira kill-switch.

---

# 53. CR-7 — PREOSTALI UI/BACKEND PARITY

Pošto React ostaje, ova faza je mnogo manja nego stari PySide6 port plan.

Ne portujemo widgete.

Samo uklanjamo Electron-specific infrastrukturu iza njih.

Posebno:

```text
screenshots file source
thumbnail native dialogs
save-as
window controls
browser bridge
artifact paths
companion messages
computer-mode switching
```

## Mermaid

React Mermaid renderer ostaje.

Nema potrebe tražiti Python Mermaid zamjenu.

Ovo je direktna ušteda u odnosu na stari full PySide6 plan.

## Localization

i18next ostaje.

Nema potrebe praviti novi Qt translation system za glavni UI.

Native orb/menu tekst može imati svoj mali localization adapter.

---

# 54. CR-8 — OMARCHY CONTEXT / CAPABILITY / PARITY

Implementirati:

```text
OA-5 Desktop Context Snapshot
OA-6 Capability Manifest
OA-12 Voice/Text Security Parity
```

Ove funkcije su backend/runtime funkcije.

Ne zavise od toga da li presentation crta React ili QWidget.

---

# 55. CR-9 — FULL OBSERVABILITY / DOCTOR / HARDENING

Implementirati:

```text
OA-9 full observability
OA-10 Ricky Doctor
OA-11 echo/duplex hardening
```

plus:

```text
WebEngine bridge diagnostics
React bundle diagnostics
QWebChannel health
```

Doctor mora moći reći:

```text
React loaded: YES
QWebChannel ready: YES
Backend connected: YES
Voice WS: YES
Mic frames: YES
```

---

# 56. CR-10 — WINDOWS PACKAGING

Primarni:

```text
PyInstaller
```

Package sadrži:

```text
Python
PySide6
Qt WebEngine dependencies
web_dist/
backend modules
voice dependencies
assets
```

Node/Electron se ne bundle-uju.

## Obavezno mjeriti

```text
installer size
installed size
cold start
idle RAM
voice RAM
CPU idle
CPU speaking
process count
```

## WebEngine deployment

Posebno testirati:

```text
QtWebEngineProcess
resources
locales
Qt platform plugins
GPU/software rendering behavior
```

## Clean machine gate

```text
install
launch
React UI
backend
voice
tool
confirmation
quit
relaunch
uninstall
```

Bez Node/npm/Electron.

---

# 57. CR-11 — ELECTRON RETIREMENT

Tek nakon:

```text
daily-driver soak PASS
voice PASS
computer mode PASS
critical parity PASS
packaging PASS
rollback tag PASS
korisnik odobri
```

## Brisati kandidati

```text
electron/
electron-builder config
Electron-only scripts
Electron-only dependencies
Electron-only tests
old preload IPC
old BrowserWindow code
src/lib/realtime.ts ako više nema nijedan validan non-test consumer
```

## NE brisati

```text
src/
React
ReactDOM
Vite
TypeScript
CSS
assets
i18next
Mermaid
```

## Finalni package runtime

```text
Electron = 0
Node runtime = 0
browser microphone = 0
renderer OpenAI auth = 0
```

---

# 58. CR-12 — LINUX / OMARCHY OS / MACOS POSLIJE WINDOWS STABILIZACIJE

Ovo ne blokira Windows.

## Omarchy/Linux

Omarchy lessons-learned već primjenjujemo na arhitekturu.

Ako se kasnije Naš Agent stvarno pokreće na Omarchy/Linux:

testirati:

```text
Qt WebEngine
Wayland
XWayland
audio devices / PipeWire through PortAudio
always-on-top orb
global shortcut
window inspection
screen capture
computer-use platform adapters
browser bridge
packaging
```

Ne kopirati:

```text
hyprctl
wtype
ydotool
```

u Windows core.

Ako Linux treba te implementacije:

```text
platform adapter
```

iza istog kanonskog service contracta.

## macOS

Kasnije:

```text
Qt WebEngine/macOS behavior
microphone permission
Accessibility permission
window controls
packaging/signing/notarization
```

---

# 59. TEST STRATEGIJA

## Unit

```text
voice audio
voice devices
voice event parsing
guards
model resolver
bridge payload validation
settings validation
capability manifest
desktop context
```

## Qt component

```text
RickyWebBridge
QWebChannel registration
MainWindow
OrbWindow
native dialogs
kill switch
```

## React

Zadržati/proširiti Vitest:

```text
Settings
Plans
Dictation
bridge adapter
voice hook
confirmation
screenshots
artifact rendering
```

## Integration

```text
QWebChannel method -> BackendClient
QWebChannel signal -> React handler
voice -> React state
React -> voice command
tool -> confirmation -> retry
```

## Manual

```text
mic
speaker
VAD
barge-in
device switching
multi-monitor
orb
mini window
packaged build
sleep/wake
network interruption
```

---

# 60. BRIDGE SECURITY TESTOVI

Obavezno:

```text
renderer cannot access OPENAI_API_KEY
renderer cannot access backend bearer token
renderer cannot arbitrary-fetch backend through generic bridge
renderer cannot invoke arbitrary Python method
invalid payload rejected
invalid model rejected backend-side
file paths sandboxed
native dialogs user-triggered
```

---

# 61. VOICE FAILURE INJECTION

Gdje praktično:

```text
credential fail
missing authoritative model
WS disconnect
failed response
rate limit
duplicate call_id
stale generation
tool timeout
confirmation reject
backend down
mic open failure
speaker failure
selected device missing
```

---

# 62. PERFORMANCE BUDŽET

Ne postavljati izmišljene apsolutne limite bez baseline-a.

CR-1 mjeri Electron baseline i QWebEngine candidate.

Uporediti:

```text
startup
idle RAM
active voice RAM
CPU idle
CPU voice
first UI paint
speech_to_first_audio
package size
```

Ako QWebEngine regression bude neprihvatljiv korisniku:

```text
CR-1B pywebview fallback
```

Ne raditi full PySide6 redraw kao prvi odgovor na performance problem.

---

# 63. ROLLBACK STRATEGIJA

Do CR-11:

```text
Electron legacy path ostaje buildable
```

Prije svakog velikog cutovera:

```text
clean commit
tag ili poznat SHA
tests
manual evidence
```

Ako novi shell failuje:

```text
rollback shell
```

Backend data schema ne treba mijenjati samo zbog UI hosta.

---

# 64. BRANCH I COMMIT DISCIPLINA

Glavna migration branch:

```text
qt-desktop-migration
```

Preporučeni slice:

```text
feat(shell): embed existing React app in QWebEngineView
feat(bridge): add QWebChannel window.ricky compatibility layer
feat(voice): drive React UI from Python RealtimeWorker
feat(voice): add text and dictation commands to Python session
fix(confirm): finish structured confirmation bridge
feat(settings): expose audio devices through native bridge
feat(shell): port native file and window actions from Electron
feat(orb): connect PySide6 orb to canonical voice signals
feat(computer-mode): host React mini view from PySide6
feat(diagnostics): add bridge and voice doctor checks
feat(context): add Desktop Context
feat(context): add Capability Manifest
test(parity): voice/text permission parity
build(desktop): package React + PySide6 runtime
chore(cutover): retire Electron runtime
```

Ne mega-commit.

---

# 65. AGENT PODJELA

## Claude — arhitektonski reviewer

Posebno:

```text
CR-0
CR-1 architecture spike
QWebChannel security boundary
voice lifecycle changes
confirmation bridge
kill-switch
final cutover
Electron deletion
```

## Codex — diff/API reviewer

Posebno:

```text
bridge contract
React window.ricky parity
backend API parity
test gaps
security regression
packaging diff
```

## Coding agenti

Dobri izolovani paketi:

```text
QWebEngine host
QWebChannel bridge
React adapter
audio selector UI wiring
file dialog wiring
screenshot URL adapter
mini view host
diagnostics
```

Svaki reviewer gleda stvarni diff.

Agent report nije dokaz sam za sebe.

---

# 66. STOP USLOVI

## STOP-C1

Da bi React radio, mora se vratiti browser microphone kao production capture.

## STOP-C2

Da bi voice radio, model-facing tool mora zaobići ToolExecutor.

## STOP-C3

Permanentni OpenAI API key mora u React/WebEngine.

## STOP-C4

QWebChannel bridge mora izložiti generic arbitrary Python execution.

## STOP-C5

Confirmation se mora oslabiti u odnosu na backend PermissionEngine.

## STOP-C6

Agent želi ponovo crtati cijeli React GUI bez dokaza da QWebEngine host ne može raditi.

## STOP-C7

Agent želi implementirati pywebview paralelno sa QWebEngine produkcijskim putem bez mjerne potrebe.

## STOP-C8

Agent uvodi drugi mic capture radi orb-a.

## STOP-C9

Electron se briše prije daily-driver/package rollback gate-a.

## STOP-C10

React se označava za brisanje samo zato što Electron odlazi.

## STOP-C11

Omarchy Linux-specific mehanizam se ubacuje u Windows core bez platform adaptera.

## STOP-C12

Current code više ne odgovara planu.

Tada:

```text
re-baseline
→ review
→ update plan
```

---

# 67. ŠTA NE RADITI

Ne raditi sada:

```text
full QWidget redraw
QML rewrite
novu bazu
novi Permission Engine
novi ToolRegistry
novi voice engine
novi memory system
arbitrary shell tool
drugi WebRTC voice
drugi microphone stream
parallel pywebview production shell
general provider framework
React redesign
cross-platform rewrite prije Windows cutovera
```

---

# 68. NAJKRAĆI KRITIČNI PUT

```text
CR-0
baseline
  ↓
CR-1
React radi u QWebEngineView
  ↓
CR-2
window.ricky radi preko QWebChannel
  ↓
CR-3
React voice UX vozi Python RealtimeSession
  ↓
CR-4
mic + tools + confirmation + diagnostics PASS
  ↓
CR-5
Python/Qt+React postaje daily driver
  ↓
CR-6
orb + mini computer mode + native controls
  ↓
CR-7
Electron-specific parity cleanup
  ↓
CR-8
Desktop Context + Capability Manifest + parity
  ↓
CR-9
Doctor + observability + duplex hardening
  ↓
CR-10
Windows package
  ↓
CR-11
delete Electron
```

Najvažniji milestone:

> Korisnik pokrene `python -m desktop`, vidi isti postojeći React Ricky GUI, razgovara preko Python Realtime voice runtime-a, koristi toolove i confirmations kroz Python backend security put, a Electron uopšte nije pokrenut.

---

# 69. DEFINITION OF DONE — WINDOWS

## Shell

```text
PySide6 owns application lifecycle
QWebEngineView owns React rendering
QWebChannel owns native bridge
```

## React

```text
existing GUI retained
CSS retained
i18next retained
Mermaid retained
Settings retained
Plans retained
Activity retained
Dictation retained
Artifacts retained
Screens retained
```

## Voice

```text
Python only
sounddevice
OpenAI WS
backend ephemeral credential
known input device
known output device
VAD trace
reconnect
barge-in
tool guards
diagnostics
```

## Security

```text
ToolExecutor one path
PermissionEngine one policy
human confirmation
payload binding
local kill switch
secrets backend-only
no renderer OpenAI auth
```

## Omarchy lessons

```text
Realtime resilience PASS
VoiceState/AudioLevel direct PASS
Confirmation v2 PASS
Desktop Context PASS
Capability Manifest PASS
Observability PASS
Doctor PASS
Voice/Text parity PASS
compound tools only if measured
```

## Runtime dependencies

```text
Electron = NO
Node end-user runtime = NO
npm end-user runtime = NO
Vite dev server production = NO
browser microphone = NO
React = YES, prebuilt assets
Qt WebEngine = YES
Python = YES
```

## Packaging

```text
install
launch
voice
tool
confirmation
restart
quit
uninstall
```

PASS na čistom Windows scenariju.

---

# 70. ŠTA SE MIJENJA U ODNOSU NA PRETHODNI PYTHON-ONLY MASTER PLAN

### OSTAVLJAMO

```text
Python voice
BackendProcess
Python backend
ToolExecutor
PermissionEngine
mic reliability
audio device selection
diagnostics
model selector
cutover-first razmišljanje
rollback
packaging
```

### MIJENJAMO

Staro:

```text
React -> PySide6 widgets
```

Novo:

```text
React -> QWebEngineView
```

Staro:

```text
React runtime = 0
```

Novo:

```text
Electron runtime = 0
Node runtime = 0
React presentation = retained
```

Staro:

```text
port every UI feature
```

Novo:

```text
port only Electron/native infrastructure behind existing React components
```

To je glavna optimizacija novog plana.

---

# 71. ŠTA SE MIJENJA U ODNOSU NA OMARCHY PLAN

Omarchy lessons ostaju.

Ali UI transport se generalizuje.

Staro:

```text
RealtimeWorker
→ Qt widget
```

Novo:

```text
RealtimeWorker
→ canonical VoiceSignals
→ native orb
→ QWebChannel
→ React
```

Omarchy nije shell arhitektura.

Omarchy je:

```text
source of runtime lessons
```

Naš Agent zadržava sopstveni jači backend/security model.

---

# 72. PRVI IMPLEMENTACIONI PAKET

Ne počinjati Desktop Contextom.

Ne počinjati novim dizajnom.

Ne počinjati package cleanupom.

Prvi paket:

```text
CR-1 — EMBED CURRENT REACT GUI IN PYSIDE6 QWEBENGINEVIEW
```

Acceptance:

```text
1. python -m desktop pokreće QMainWindow.
2. QMainWindow sadrži QWebEngineView.
3. QWebEngineView učitava postojeći React production bundle.
4. Idle/Settings/Plans/Dictation/Artifacts renderuju bez fundamentalnih grešaka.
5. SVG/assets/i18next rade.
6. Electron nije pokrenut.
7. Nema izmjena vizuelnog dizajna osim nužnih host compatibility popravki.
8. Izmjeriti startup/RAM/process count.
9. Agent report navodi stvarne rezultate.
10. Ne implementirati još kompletan bridge/voice ako time scope postaje prevelik.
```

Tek nakon toga:

```text
CR-2 — QWebChannel compatibility bridge
```

pa:

```text
CR-3 — Python voice -> existing React UI
```

---

# 73. KONAČNA KANONSKA ODLUKA

Naš Agent se ne vraća na Electron.

Naš Agent ne baca postojeći React GUI.

Naš Agent ne pravi drugi voice engine.

Naš Agent ne kopira Omarchy arhitekturu 1:1.

Kanonski cilj je:

```text
POSTOJEĆI REACT GUI
+
PYSIDE6 NATIVE SHELL
+
QWEBENGINEVIEW
+
QWEBCHANNEL
+
POSTOJEĆI PYTHON REALTIME VOICE
+
POSTOJEĆI PYTHON BACKEND
+
OMARCHY LESSONS-LEARNED
=
RICKY WINDOWS DAILY DRIVER
```

To je od sada aktivni pravac implementacije.

---

# 74. JEDNA REČENICA ZA SVE AGENTE

> Ne precrtavaj React GUI u PySide6; zadrži React kao presentation layer unutar PySide6/QWebEngineView, izbaci Electron i browser voice, koristi postojeći Python Realtime + backend security put, a Omarchy lessons ugradi u voice lifecycle, state/event, confirmation, context, capability, diagnostics i observability slojeve.
