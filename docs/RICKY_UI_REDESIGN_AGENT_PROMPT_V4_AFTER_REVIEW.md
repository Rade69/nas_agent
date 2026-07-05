# Ricky Assistant — Voice-First UI + Companion Agent Prompt REVISED

> **Napomena (2026-07-05, Claude Code integracija):** Sekcija "Implementation Phases" ispod je bila pisana protiv starije verzije `MIGRATION_PLAN.md` — originalni FAZA 6/7/8/10 brojevi su se sudarali sa stvarnim, drugačijim, već završenim fazama istog broja. Ispravljeno ispod (brojevi uklonjeni, zamijenjeno "Redesign step 1-4"). Sekcije E i F suštinski dupliraju `SECURITY_HARDENING_PLAN.md` sekciju 25 "Realtime Event Flow and Cancellation Safety" (kanonski izvor za cancellation/event-volume pravila), a sekcija B duplira `RICKY_GUI_LOCALIZATION_PLAN.md` (kanonski izvor za lokalizaciju). U slučaju razilaženja, ta dva dokumenta su autoritativna.

## Purpose

Use this prompt with Codex, Claude Code, or another coding agent to redesign the Ricky Assistant UI and Companion Mode.

This version corrects the previous UI prompt.

Critical correction:

```txt
Do not replace or bypass the existing src/lib/realtime.ts OpenAI Realtime/WebRTC voice pipeline.

The UI redesign must wrap and improve the existing low-latency voice-first path.
Python backend is not the MVP audio engine.
```

The goal is to turn Ricky from a demo-looking assistant into a serious **voice-first desktop companion** with a visual control center.

---

# Product Direction

Ricky Assistant is:

```txt
voice-first desktop companion
+ visual control center
+ safe local tool runtime
```

Ricky Assistant is not:

```txt
chat app with microphone
coding assistant
VSCode/Cursor replacement
developer automation tool
custom Python STT/TTS experiment
```

Voice is primary. Text input remains available, but secondary.

---

# Existing Voice Pipeline Must Be Preserved

The app already has:

```txt
src/lib/realtime.ts
```

Treat this as the existing primary voice engine.

Assume the current voice path is:

```txt
Electron renderer / src/lib/realtime.ts
  -> WebRTC
  -> OpenAI Realtime API
  -> streamed audio response back to renderer
```

This existing path may already cover:

```txt
- server-side VAD
- transcript events
- streamed TTS/audio response
- interruption
- mood/state mapping
```

Do not replace this with:

```txt
microphone -> Python -> STT -> agent -> TTS -> Python -> audio output
```

That is out of scope for the MVP.

---

# Core Architecture Assumption

```txt
Voice-first React UI + Companion Orb
        ↓
src/lib/realtime.ts as Realtime WebRTC voice client
        ↓
Renderer Realtime Event Router
        ↓
Electron preload / IPC
        ↓
Electron main process as thin shell and bridge
        ↓
Python backend as session/security/storage/tools layer
```

## React/Renderer owns

```txt
- voice-first UI
- existing Realtime voice client
- OpenAI raw Realtime event handling
- VoiceState mapping
- Companion orb UI
- push-to-talk UI
- text fallback input
- Output / Activity / Plans / Memory / Screens
- visual confirmation UI
```

## Python backend owns

```txt
- Realtime session/client-secret endpoint
- standard OpenAI API key protection
- activity timeline persistence
- transcript persistence
- confirmations
- plans/proposals storage
- local tool registry
- safe local tool execution
- SQLite storage
```

## Python backend does not own in MVP

```txt
- microphone capture
- VAD
- STT engine
- TTS engine
- audio playback
- replacement for src/lib/realtime.ts
```

---

# High-Level UI Goal

The UI must always make these things obvious:

```txt
1. Is Ricky listening?
2. What did Ricky hear?
3. Is Ricky transcribing, thinking, speaking, or waiting for confirmation?
4. Is the Python backend connected?
5. Is Computer Mode ON or OFF?
6. What action does Ricky want to take?
7. Is confirmation required?
8. Where are results shown?
9. Where are activity history and plans stored?
10. How can the user stop Ricky immediately?
```

If the user cannot immediately understand what Ricky is doing, the design failed.

---

# Visual Direction

Use a professional dark UI.

Suggested color tokens:

```txt
Background:        #080B10
Panel:             #11161D
Panel 2:           #151B24
Panel 3:           #0D1117
Border:            #263241
Border soft:       #1C2530

Primary blue:      #3EA6FF
Primary blue dark: #1877D2
Primary soft:      #9DDCFF

Text main:         #F4F7FB
Text secondary:    #C9D3DF
Text muted:        #8D9AAA

Success:           #22C55E
Warning:           #F5A524
High risk:         #F97316
Danger:            #EF4444
Critical:          #DC2626

Input bg:          #111821
Button bg:         #17212C
Button hover:      #1E2B38
```

Avoid:

```txt
- childish cartoon styling
- huge empty spaces
- oversized avatar taking most of the app
- chat-first layout
- unlabeled icons
- unsafe computer-use actions hidden behind cute UI
```

---

# Target Layout

Create a voice-first layout like this:

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ Ricky Assistant   Listening/Ready   Backend connected   Computer Mode: OFF  │
├──────────────────────────────┬──────────────────────────────────────────────┤
│ Assistant / Voice Panel       │ Workspace                                    │
│                               │                                              │
│ Small Ricky orb/avatar        │ Tabs: Output | Activity | Plans | Memory | Screens
│ VoiceState                    │                                              │
│ Microphone / speaking state   │ Current result / artifact / transcript       │
│ Current action                │ Timeline / plan / screenshot details         │
│ Recent transcript preview     │                                              │
├──────────────────────────────┴──────────────────────────────────────────────┤
│ [ Hold to talk ]  Ricky is ready       [Type instead...] [Send] [Stop]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Text input exists, but it is secondary. The main bottom action is voice.

---

# Primary Workspace Tabs

Use these tabs:

```txt
Output
Activity
Plans
Memory
Screens
```

Do not make `Tools` a primary tab for normal users. Tools can be in Settings / Advanced later.

## Output

Main place for result, answer, artifact, summary, current transcript or generated content.

## Activity

Timeline of what Ricky heard, said, requested, and did.

Examples:

```txt
12:44 Listening started
12:44 Transcript: "Ricky, pogledaj šta je na ekranu"
12:44 screen_snapshot requested
12:45 UI inspect completed
12:45 Output created
```

## Plans

Internal proposals/tasks.

Statuses:

```txt
draft
pending_approval
approved
running
completed
failed
cancelled
archived
```

Plans are not `.txt` or `.md` files by default. They are UI/database records.

## Memory

Notes, records, saved useful information.

## Screens

Screenshots explicitly captured by user or during approved actions.

---

# VoiceState

Use this state model:

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

VoiceState must be visible in:

```txt
- TopBar
- AssistantAvatar / orb
- CompanionOrb
- BottomVoiceBar
- ActivityTimeline
- ApprovalDialog
```

---

# Component Requirements

## 1. Top App Bar

Required elements:

```txt
Left:
- App icon
- Ricky Assistant

Center:
- VoiceState badge:
  - Ready
  - Listening
  - Transcribing
  - Thinking
  - Speaking
  - Waiting confirmation
  - Interrupted
  - Muted
  - Error

Next:
- Python backend badge:
  - Connected
  - Disconnected
  - Starting
  - Error

Right:
- Computer Mode badge/toggle:
  - OFF by default
  - ON visually stronger
- Settings
- Companion
- Minimize
- Maximize/restore
- Close
```

Acceptance criteria:

```txt
- User immediately sees voice status.
- User sees backend status.
- Computer Mode is always visible.
- Companion action is clear.
```

---

## 2. Left Assistant / Voice Panel

The avatar remains but becomes smaller and functional.

Required elements:

```txt
- Smaller Ricky orb/avatar
- VoiceState visualization
- current voice status text
- microphone/speaking indicator
- current action card
- recent transcript preview
- Stop button when speaking/thinking/running
```

Avatar/orb states:

```txt
idle:
- calm blue ring

listening:
- blue pulse

transcribing:
- soft processing shimmer

thinking:
- purple/blue slow glow

speaking:
- audio wave/ring animation

waiting_confirmation:
- orange glow + question/alert indicator

error:
- red pulse/shake

muted:
- gray/muted state

backend_disconnected:
- disabled-looking state
```

Acceptance criteria:

```txt
- Avatar no longer dominates screen.
- Voice state is understandable without reading logs.
- User can stop Ricky when needed.
```

---

## 3. BottomVoiceBar

Replace chat-first command bar with voice-first control.

Required layout:

```txt
[ Hold to talk ]  Ricky is ready / Listening / Speaking     [Type instead...] [Send] [Stop]
```

Requirements:

```txt
- Hold to talk is primary.
- Text input is secondary.
- Stop is visible during speaking/thinking/waiting/running.
- Mute option is available.
- Push-to-talk must connect to existing src/lib/realtime.ts flow, not Python STT.
```

Acceptance criteria:

```txt
- UI feels voice-first.
- Text remains available.
- User can interrupt quickly.
```

---

## 4. Realtime Event Router UI Integration

Add a renderer-side event router.

Suggested files:

```txt
src/lib/realtime.ts
src/lib/realtimeEventRouter.ts
src/lib/voiceStateMapper.ts
```

Rules:

```txt
- Preserve existing src/lib/realtime.ts WebRTC path.
- Do not rewrite it unless necessary.
- Map OpenAI raw events to internal app events.
- Send transcript/activity events to Python backend when available.
- Do not execute local risky tools directly from renderer.
```

Event naming:

```txt
Raw OpenAI event:
conversation.item.input_audio_transcription.completed

Internal app event:
voice.final_transcript
activity.created
```

Acceptance criteria:

```txt
- Existing voice pipeline still works.
- VoiceState is driven by realtime events.
- Activity/transcript persistence can be added without touching audio path.
```

---

## 5. Approval Dialog / Plans UI

When Ricky wants to do a risky action, show a visual confirmation.

Example:

```txt
Ricky predlaže ove korake

1. Otvori aplikaciju
2. Provjeri aktivni prozor
3. Unesi tekst

Risk: HIGH
Target: notepad.exe

[Otkaži] [Pokreni]
```

Rules:

```txt
- No Notepad planning.
- No automatic .txt/.md plan files.
- Plans are UI/database records.
- Export only on explicit user request.
- "Da/yes" must not approve anything without active confirmation_id.
```

Acceptance criteria:

```txt
- User sees action before execution.
- User can approve/reject visually.
- Voice confirmation and visual confirmation refer to same confirmation_id.
```

---

# Companion Mode / Floating Ricky

Add a second UI mode called **Companion Mode**.

When the full app is hidden, a small animated Ricky orb remains on screen.

Important correction:

```txt
Companion orb must integrate with existing src/lib/realtime.ts voice state.
It must not own its own audio/STT/TTS pipeline.
It must not execute unsafe tools directly.
```

## Core concept

```txt
Normal Mode
= full voice-first Ricky Assistant window

Companion Mode
= small floating Ricky orb on desktop
```

The companion orb should be:

```txt
- small
- animated
- draggable
- always on top
- user-controlled
- able to restore main window
- able to show VoiceState/backend status
- able to expose compact right-click menu
```

Self-walking movement is OFF by default.

---

## Companion Mode Behavior

When user clicks:

```txt
Companion
```

the app should:

```txt
1. Hide main Ricky Assistant window.
2. Open/show small transparent floating Ricky orb.
3. Keep orb always on top.
4. Allow user to drag orb.
5. Restore main window on selected interaction.
6. Keep voice/backend state visible through orb animation.
```

Recommended interaction model for testing:

```txt
Option A:
single click = push-to-talk / start listening
double click = restore main window
right click = menu

Option B:
single click = restore main window
hold click = push-to-talk
right click = menu
```

Do not lock this too early. Test which is easier.

Acceptance criteria:

```txt
- Main window enters Companion Mode.
- Orb appears.
- Orb can restore main window.
- Orb shows VoiceState.
- App does not quit.
- Realtime voice pipeline is not broken.
```

---

## Companion Window Technical Requirement

Use a second Electron BrowserWindow.

Do not fake Companion Mode only with CSS.

Suggested window options:

```ts
{
  width: 84,
  height: 84,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  resizable: false,
  skipTaskbar: true,
  hasShadow: false,
  focusable: true
}
```

Acceptance criteria:

```txt
- Companion Mode uses separate Electron window.
- Window is frameless and transparent.
- Orb is compact.
- Companion logic is isolated from main.cjs as much as practical.
```

---

## Companion Orb Visual States

Required states:

```txt
idle / ready
listening
transcribing
thinking
speaking
waiting_confirmation
interrupted
muted
error
backend_disconnected
```

Visual behavior:

```txt
idle:
- calm blue ring

listening:
- blue pulse

transcribing:
- subtle processing shimmer

thinking:
- purple/blue glow

speaking:
- audio-wave ring

waiting_confirmation:
- orange glow + alert marker

interrupted:
- quick fade/reset

muted:
- gray muted state

error:
- red pulse/shake

backend_disconnected:
- disabled muted state
```

Acceptance criteria:

```txt
- User can understand state from orb alone.
- Waiting confirmation and error are impossible to miss.
- Speaking/listening are clearly different.
```

---

## Companion Context Menu

Right-click menu items:

```txt
Open Ricky
Hold to talk / Start listening
Stop
Mute / Unmute
Take screenshot
Inspect UI
Computer Mode: OFF/ON
Settings
Quit
```

Rules:

```txt
- Open Ricky restores full app.
- Quit exits entire app.
- Stop calls existing realtime interrupt flow.
- Mute affects voice interaction state.
- Screenshot and Inspect UI go through backend/tool permission layer if available.
- Computer Mode cannot be enabled silently.
```

Acceptance criteria:

```txt
- Context menu works.
- Dangerous actions are not silently executed.
- Companion renderer does not directly execute tools.
```

---

## Companion Dragging and Position

Requirements:

```txt
- User can drag orb.
- App remembers last orb position.
- Orb does not open outside visible screen area.
- If monitor layout changes, reset to safe default.
```

Suggested setting:

```json
{
  "companionMode": {
    "lastPosition": {
      "x": 1200,
      "y": 700
    },
    "dockToEdge": false,
    "idleMovement": false
  }
}
```

Acceptance criteria:

```txt
- Position persists.
- Orb remains visible.
- Dragging does not accidentally trigger restore/listening.
```

---

---

# Post-Review Corrections — Must Be Fixed Before Implementation

This section adds corrections based on review of the latest voice-first GUI mockup.

The mockup direction is approved as a strong base, but the implementation must fix these issues:

```txt
1. Avoid duplicated voice wave animations.
2. Integrate GUI localization into Settings and all visible UI labels.
3. Keep transcript language behavior clear.
4. Separate Voice Realtime Model from Text/Document/Local models.
5. Make Computer Mode ON a safety-focused UI state.
6. Avoid IPC flooding from high-frequency Realtime events.
7. Distinguish voice interruption from Python tool cancellation.
```

These are not optional polish items. They prevent confusion, architectural drift, unsafe UI behavior and future refactor pain.

---

## A. Voice Visual Hierarchy Rules

The UI must not show multiple independent voice animations at the same time.

Problem to avoid:

```txt
- wave animation around Ricky orb,
- wave icon in Output empty state,
- wave animation inside Hold to talk,
- all moving independently.
```

This creates visual noise and makes it unclear which element represents the actual voice state.

### Rule

```txt
Only one primary voice animation source should be active per state.
```

### State-specific visual hierarchy

```txt
idle / ready:
- Ricky orb is calm.
- Hold to talk is visible but calm.
- Output empty state can show a static voice icon.
- No animated waveforms.

listening:
- BottomVoiceBar / Hold to talk is the primary animation.
- Ricky orb may show a blue listening ring.
- Do not animate separate side waveforms around the face.

transcribing:
- Ricky orb shows subtle processing shimmer.
- BottomVoiceBar shows "Processing..." or "Transcribing...".
- No decorative waveforms.

thinking:
- Ricky orb shows slow blue/purple glow.
- Workspace can show a subtle loading state.
- No audio wave animation.

speaking:
- Ricky orb/avatar is the primary speaking animation.
- BottomVoiceBar changes to Stop / Interrupt focus.
- Hold to talk should not pulse as if the user is still speaking.

waiting_confirmation:
- voice wave animations stop.
- ApprovalDialog / confirmation panel is the visual focus.
- Orange warning/confirmation styling is dominant.

error:
- red state is shown in TopBar, orb, and relevant card.
- No audio wave animation.
```

### Acceptance criteria

```txt
- Listening and speaking are visually different.
- There are not three separate voice wave animations moving at once.
- Waiting confirmation clearly overrides decorative voice animations.
- Stop / Interrupt is visible during speaking, thinking, tool execution, and confirmation.
```

---

## B. GUI Localization Integration

> Kanonski izvor je [RICKY_GUI_LOCALIZATION_PLAN.md](./RICKY_GUI_LOCALIZATION_PLAN.md) (backlog epic u `MIGRATION_PLAN.md`). Sekcija ispod je sažetak istih pravila primijenjen na ovaj konkretan UI redizajn — u slučaju razilaženja, taj dokument je autoritativan.

The UI must support interface localization from the beginning.

Supported initial interface languages:

```txt
sr-Latn
en
de
es
fr
```

Meaning:

```txt
sr-Latn = Serbian Latin / Srpski latinica
en      = English
de      = Deutsch
es      = Español
fr      = Français
```

### Rule

```txt
No hardcoded user-facing strings.
All visible GUI text must use i18n translation keys.
```

This applies to:

```txt
- TopBar
- Voice Center
- BottomVoiceBar
- Workspace tabs
- Output empty state
- Activity
- Plans
- ApprovalDialog
- Settings
- Companion menu
- Computer Mode UI
- Risk labels
- Error messages
- Tooltips
```

### Settings location

Add in Settings:

```txt
Settings
  General
  Appearance
  Language
  Voice & Audio
  Privacy & Security
  Computer Mode
  Shortcuts
  Notifications
  About Ricky Assistant

  Models (Future)
    Model Manager
    Voice Realtime Model
    Text Fallback Model
    Document Processing Model
    Local Model
```

Language settings UI:

```txt
Language / Jezik

Options:
- Srpski latinica
- English
- Deutsch
- Español
- Français
```

Selected language is stored as:

```json
{
  "interface_language": "sr-Latn"
}
```

English should remain fallback language.

### Transcript language rule

Interface language and transcript language are not the same thing.

Rule:

```txt
GUI labels follow interface_language.
Transcript shows what the user actually said.
```

Example:

```txt
interface_language = sr-Latn

Label:
Šta je Ricky čuo

Original transcript:
"Open Notepad and write a short note."
```

Optional future feature:

```txt
Show translated transcript
```

If enabled, UI may show:

```txt
Original:
"Open Notepad and write a short note."

Prevod:
"Otvori Notepad i napiši kratku bilješku."
```

Do not silently replace original transcript with a translation.

### Activity localization rule

Activity should store structured event data, not only translated strings.

Good:

```json
{
  "type": "tool.started",
  "tool": "screen_snapshot",
  "timestamp": "2026-07-05T12:44:00Z"
}
```

UI translates display text at render time.

Bad:

```json
{
  "message": "Screenshot started"
}
```

This allows old Activity history to render correctly after the user changes interface language.

---

## C. Model Settings Rules

Do not show a single ambiguous field:

```txt
Default Model: gpt-4o-mini
```

This is misleading because the voice-first Realtime path and text/document/local model paths are different.

### Required separation

Model settings must distinguish:

```txt
Voice Realtime Model
Text Fallback Model
Document Processing Model
Local Model
```

### MVP rule

For MVP, Model Manager is future-facing and should not allow changes that break `src/lib/realtime.ts`.

Display it as:

```txt
MODELS (Future)

Voice Realtime Model:
OpenAI Realtime session model

Text Fallback Model:
Not configured / future

Document Processing Model:
Not configured / future

Local Model:
Not configured / future
```

If a default is shown, be explicit:

```txt
Voice realtime model: configured by backend session
Text fallback model: not configured
```

### Acceptance criteria

```txt
- UI does not imply that one generic "Default Model" controls every path.
- Voice model and text/document/local models are visually separate.
- Model Manager cannot break the existing WebRTC Realtime voice pipeline.
- If model selection is not implemented, it is clearly marked as Future.
```

---

## D. Computer Mode Safety UI Rules

Computer Mode is high-risk.

When Computer Mode is OFF:

```txt
- normal voice-first UI is shown.
- Computer Mode badge remains visible.
```

When Computer Mode is ON:

```txt
- UI enters safety-focused mode.
- TopBar shows stronger warning/accent.
- Current action / target window becomes more prominent.
- Recent Actions / Activity becomes more important.
- Stop / Cancel is always visible.
- High-risk actions require ApprovalDialog.
```

### Required Computer Mode ON display

When enabled, show:

```txt
Computer Mode: ON
Ricky can interact with your mouse and keyboard.

Target window:
<process name> — <window title>

Pending action:
<tool name>
<payload summary>

Risk:
LOW / MEDIUM / HIGH / CRITICAL

[Cancel] [Allow once]
```

### ApprovalDialog must include

```txt
- tool name
- risk level
- target app/process/window
- payload summary
- confirmation_id
- expiration time if applicable
- Cancel
- Allow once
```

### Confirmation binding

A confirmation must be bound to:

```txt
- confirmation_id
- tool name
- payload hash
- target app/window
- risk level
- expiration time
```

If any of these change, the confirmation is invalid.

> Ovo je već implementirano na backend strani u FAZI 10 (`python_backend/app/agent/permission_engine.py` — `confirmation_id` vezan za tool_name/payload_hash/expires_at). Ova sekcija opisuje samo kako to UI treba prikazati; polje "target app/window" još nije backend-provjereno (active window validation je FAZA 11).

### Acceptance criteria

```txt
- Computer Mode ON is impossible to miss.
- The user always sees what Ricky wants to control.
- The user always sees the active target app/window for high-risk actions.
- Recent Actions / Activity shows pending and completed actions clearly.
- Stop / Cancel is visible and not hidden in a menu.
```

---

## E. Stop / Interrupt UI Accuracy

> Kanonski izvor je [SECURITY_HARDENING_PLAN.md](./SECURITY_HARDENING_PLAN.md) sekcija 25 "Realtime Event Flow and Cancellation Safety" (execution_id/cancellation_token state mašina, već implementirana u FAZI 10). Sekcija ispod je UI-strana primjena istog principa.

The UI must distinguish voice interruption from tool cancellation.

Do not show:

```txt
Cancelled
```

immediately after the user presses Stop unless backend/tool layer confirms that the tool was actually cancelled.

Use separate states:

```txt
Voice stopped
Tool cancellation requested
Tool cancelled before execution
Tool already started
Tool could not be fully cancelled
Action completed before cancellation
```

Example UI messages:

```txt
Ricky stopped speaking.
Cancelling current tool...
Tool cancelled before execution.
```

or:

```txt
Ricky stopped speaking.
The action had already started and could not be fully cancelled.
See Action Receipt.
```

Acceptance criteria:

```txt
- User is never misled into thinking an OS action stopped if it did not.
- Stop always stops voice output immediately.
- Tool cancellation status comes from backend/tool executor, not UI assumption.
```

---

## F. Realtime Event Volume Rules

> Kanonski izvor je [SECURITY_HARDENING_PLAN.md](./SECURITY_HARDENING_PLAN.md) sekcija 25.4-25.5 (isti sadržaj, backend strana). Trenutno stanje koda (provjereno 2026-07-05): `src/lib/realtime.ts` ne šalje nijedan raw event Python backend-u — event bridge iz ove sekcije još nije implementiran (FAZA 8/11).

Renderer may receive high-frequency Realtime events, but Python backend should not receive every delta.

Rule:

```txt
High-frequency Realtime deltas stay in renderer.
Backend receives final or aggregated events.
```

Do not persist every:

```txt
- response.audio.delta
- mic waveform tick
- partial transcript character
- UI animation state
```

Backend should receive:

```txt
- voice.turn_started
- voice.final_transcript
- voice.turn_completed
- voice.interrupted
- confirmation.required
- tool.started
- tool.completed
- tool.failed
- activity.created
```

Partial transcript persistence is optional and must be throttled:

```txt
max 1 event per 500-1000 ms
```

Event priority:

```txt
CRITICAL:
- confirmation.required
- tool.blocked
- tool.failed
- security.violation
- voice.interrupted

HIGH:
- tool.started
- tool.completed
- voice.final_transcript
- backend.error

MEDIUM:
- activity.created
- plan.updated
- artifact.created

LOW:
- partial transcript
- animation state
- mic level
- waveform
```

Acceptance criteria:

```txt
- IPC is not flooded by audio/transcript deltas.
- Activity log stays readable.
- Security and confirmation events are never dropped.
- Low-priority visual events can be dropped/throttled under load.
```

---

## G. Voice Input UX, Dictation Mode and No-Notepad Rule

> Dodatak (Codex, 2026-07-05, pregledao Claude Code). "No Notepad" pravilo NIJE novo — već je uspostavljena politika i već implementirana u FAZI 9 (plans/confirmations su SQLite zapisi, ne fajlovi — vidi `agent_reports/2026-07-05_faza9-confirmations-plans.md`). Ovaj dodatak generalizuje isto pravilo i na transcript/dictation prikaz. `VoiceSessionState` ispod je dodatni, ortogonalan sloj koji se kombinuje sa postojećim `VoiceState` (`src/lib/voiceState.ts`), ne zamjenjuje ga.

Ricky must not use Notepad (or any external app) as a UI workaround for transcript, draft, plan, or correction display. Voice input is also not required to be a "hold to talk" walkie-talkie model.

### Key rule — No Notepad for transcript, planning, draft preview or correction

Forbidden:

```txt
- opening Notepad to show a transcript,
- opening Notepad to show a plan,
- opening Notepad so the user can correct recognized speech,
- opening Notepad as a temporary draft editor,
- using any external app as a substitute for the Ricky UI.
```

Allowed:

```txt
- internal Ricky panel,
- internal dialog,
- editable text area inside an Output/Voice Draft panel,
- ApprovalDialog for risky actions,
- Plans panel for proposed steps.
```

### Voice input is not always a transcript view

Do not always show the full live transcript (UI clutter, backend load, privacy, most commands are short). Show transcript only when useful for user control.

### Three voice display modes

```txt
1. Ephemeral Command Mode  — quick commands/questions, no big panel, no full transcript retained.
2. Dictation / Voice Draft Mode — user wants Ricky to write/transcribe; opens a large editable panel.
3. Review / Confirmation Mode — command leads to a risky OS/file/document action; opens ApprovalDialog.
```

**1. Ephemeral Command Mode** — examples: "Ricky, otvori kalkulator.", "Kakvo je vrijeme danas?". UI shows at most a short "Ricky heard: ..." line, sends the final transcript to the agent, shows the result in Output/Activity, does not retain every partial transcript.

**2. Dictation / Voice Draft Mode** — triggered by phrases like "Diktiram bilješku.", "Napiši mi poruku...". Opens a large "Voice Draft" / "Diktirani tekst" panel with an editable text area and `[Nastavi diktiranje] [Ispravi] [Kopiraj] [Sačuvaj] [Pošalji agentu] [Otkaži]` actions. Text stays local and editable until the user explicitly sends/saves/copies it — never auto-executed against the OS.

**3. Review / Confirmation Mode** — triggered by risky actions ("Unesi ovaj tekst u aktivni prozor.", "Pošalji ovaj email."). Shows what Ricky understood, the proposed tool call, target app/window, the exact payload, risk level, and expiration — matching the `confirmation_id` binding already implemented in FAZA 10 (`python_backend/app/agent/permission_engine.py`: tool_name + payload_hash + expires_at). User can edit the text before execution, cancel, or allow once.

### VoiceSessionState (composes with VoiceState, does not replace it)

```ts
type VoiceSessionState =
  | "inactive"
  | "listening"
  | "paused"
  | "processing"
  | "dictation"
  | "reviewing"
  | "waiting_confirmation"
  | "completed"
  | "cancelled"
  | "error";
```

Example combinations: `VoiceState=listening` + `VoiceSessionState=dictation`; `VoiceState=waiting_confirmation` + `VoiceSessionState=reviewing`.

### Backend / event rules (consistent with SECURITY_HARDENING_PLAN.md section 25.4-25.5)

```txt
Partial transcript stays local in renderer.
Backend receives only final transcript, user-approved draft, or aggregated events.
```

- Dictation Mode: text is shown/corrected locally; only sent onward when the user clicks Send/Save/Copy.
- Ephemeral Command Mode: only the final transcript goes to the agent; no large transcript panel opens.
- Confirmation Mode: a `proposed_action` is created and shown in ApprovalDialog; executed only on explicit approval.

### Output tab behavior by mode

```txt
Ephemeral Command:  result or short status.
Dictation Mode:     large Voice Draft editor.
Confirmation Mode:  ApprovalDialog / proposed action.
Normal Result:      answer, artifact, or Review Packet.
No result:          empty state.
```

Avoid separate external windows where not necessary.

### Click-to-talk, not walkie-talkie, as the primary UX

Primary model is click-to-start voice session, not "Hold to talk / Release to send":

```txt
Klikni mikrofon → Ricky sluša → korisnik govori normalno → klikni Stop / Mute / Send / Cancel po potrebi.
```

Microphone is OFF by default; a click starts the voice session; Stop and Mute are always available; auto-timeout after prolonged silence. Push-to-talk/hold mode may exist later as an optional Settings toggle, not the default.

> Napomena: postojeći `BottomVoiceBar.tsx` (FAZA 8) već koristi toggle-dugme za konekciju (klik spoji/klik prekine), ne doslovan hold-gest — ova ispravka je manja u praksi nego što zvuči, uglavnom usklađuje labele/namjeru ("Hold to talk" tekst → "Govori"/click-to-start framing), ne zahtijeva rušenje postojećeg mehanizma.

### Settings addition

```txt
Voice & Audio
  Voice input mode:
    - Click to talk / voice session   (default)
    - Push to talk / hold mode        (optional, future)
```

### Additional Important Engineering Rules (continuing the numbering above)

```txt
19. Do not use Notepad or any external app as transcript/draft/plan UI.
20. Voice input has three display modes: Ephemeral Command, Dictation Draft, Confirmation Review.
21. Do not always show full live transcript.
22. Show large editable transcript panel only for dictation/write-output tasks or when user requests review/correction.
23. Primary voice UX is click-to-start voice session, not hold-to-talk.
24. Push-to-talk can be optional/future setting, not default.
25. Partial transcript stays local unless final/user-approved content must be sent.
26. Risky actions require confirmation panel inside Ricky UI.
```

### Acceptance criteria

```txt
- Notepad is explicitly forbidden for transcript/draft/plan UI.
- Hold-to-talk is no longer the default UX.
- Click-to-start voice session is the default UX.
- Full live transcript is not always shown.
- Large editable Voice Draft panel appears only when user dictates or asks to write/show text.
- Confirmation panel appears for risky actions.
- Partial transcripts are not spammed to backend.
- User can correct dictated text inside Ricky UI.
- User can stop/mute voice session at any time.
```

# Suggested React Component Structure

```txt
src/
  components/
    layout/
      AppShell.tsx
      TopBar.tsx
      LeftVoicePanel.tsx
      WorkspacePanel.tsx
      BottomVoiceBar.tsx

    assistant/
      AssistantAvatar.tsx
      VoiceStateBadge.tsx
      CurrentActionCard.tsx
      TranscriptPreview.tsx

    workspace/
      WorkspaceTabs.tsx
      OutputTab.tsx
      ActivityTab.tsx
      PlansTab.tsx
      MemoryTab.tsx
      ScreensTab.tsx

    safety/
      ApprovalDialog.tsx
      RiskBadge.tsx

    common/
      IconButton.tsx
      StatusPill.tsx
      Panel.tsx
      EmptyState.tsx

  companion/
    CompanionApp.tsx
    CompanionOrb.tsx
    CompanionContextMenu.tsx
    companion.css

  lib/
    realtime.ts
    realtimeEventRouter.ts
    voiceStateMapper.ts

  services/
    backendClient.ts
    activityClient.ts
```

Keep components small.

Do not put the redesign into one giant `App.tsx`.

---

# IPC / Event Boundaries

Use colon for IPC channels:

```txt
app:quit
app:minimize
app:maximize
app:enter-companion-mode
app:exit-companion-mode

voice:start
voice:stop
voice:interrupt
voice:mute
voice:unmute

realtime:get-session

confirmation:approve
confirmation:reject

backend:get-status

companion:restore-main-window
companion:get-state
companion:update-state
companion:save-position
companion:get-position
companion:show-context-menu
```

Use dot for internal app/backend events:

```txt
voice.state_changed
voice.final_transcript
activity.created
confirmation.required
tool.started
backend.connected
```

Keep raw OpenAI events under original names until mapped by event router.

---

# Implementation Phases

> **Ispravka (2026-07-05, Claude Code):** Originalna verzija je dodjeljivala FAZA 6/7/8/10 brojeve koji se sudaraju sa stvarnim, već završenim fazama istog broja u `MIGRATION_PLAN.md` (FAZA 6 = Realtime session security, FAZA 7 = SQLite storage, FAZA 8 = Voice-first UI refactor, FAZA 10 = Permission/cancellation engine — sve ✅ gotovo, drugačiji sadržaj od opisanog ispod). Brojevi su uklonjeni. Ovaj dokument je **redizajn postojećih komponenti** (FAZA 8 voice-first shell i FAZA 9 confirmations/plans već postoje i rade) — agent koji ovo implementira mora prvo pročitati `src/components/VoiceTopBar.tsx`, `BottomVoiceBar.tsx`, `ActivityTimeline.tsx` i FAZA 9 confirmation/plans UI prije redizajna, ne graditi paralelne duplikate. Broj faze se dodjeljuje isključivo u `MIGRATION_PLAN.md` kad korisnik odluči da ovaj redizajn uđe u aktivan rad (vidi "Backlog / Future Epics" tamo).

Do not create separate VF phase numbering that conflicts with `MIGRATION_PLAN.md`.

## Redesign step 1 — Voice-first shell redesign (bazirano na postojećoj FAZI 8)

Goal:

```txt
Redesign the existing voice-first shell (VoiceTopBar/BottomVoiceBar/RickyFace,
already implemented) into the TopBar / LeftVoicePanel / WorkspacePanel layout
described above, while preserving src/lib/realtime.ts.
```

Tasks:

```txt
1. Reuse existing VoiceState type (already in src/lib/voiceState.ts).
2. Redesign existing TopBar voice/backend status (VoiceTopBar.tsx).
3. Redesign existing BottomVoiceBar with click-to-start voice session as the
   primary action (not hold-to-talk — see section G "Voice Input UX, Dictation
   Mode and No-Notepad Rule"); add VoiceSessionState and a conditional Voice
   Draft panel for dictation.
4. Make text input secondary (already the case).
5. Add LeftVoicePanel (new layout wrapper around existing RickyFace).
6. Turn ActivityTimeline from overlay/popup into persistent Workspace tabs:
   Output / Activity / Plans / Memory / Screens.
7. Reuse existing Realtime Event Router (src/lib/realtimeEventRouter.ts).
8. Do not change audio path.
```

Acceptance criteria:

```txt
- UI is voice-first.
- Existing realtime voice path still works.
- Text input remains available.
- VoiceState visible in main UI.
- Activity is a persistent tab, not a popup overlay.
```

---

## Redesign step 2 — Activity + transcript tab

Goal:

```txt
Show what Ricky heard and did as a persistent workspace tab (not an overlay).
```

Tasks:

```txt
1. Convert ActivityTimeline into ActivityTab within WorkspacePanel.
2. Add transcript preview to LeftVoicePanel.
3. Add event rows for listening/transcript/response/interruption.
4. Send activity/transcript events to backend when the event bridge exists
   (see SECURITY_HARDENING_PLAN.md section 25.4 for throttling rules — not yet built).
5. Use mock fallback if backend event bridge is not ready.
```

Acceptance criteria:

```txt
- User can see what Ricky heard.
- User can see important voice events.
- UI works with mock and backend data.
```

---

## Redesign step 3 — Approval dialog + Plans tab (bazirano na postojećoj FAZI 9)

Goal:

```txt
Redesign the existing FAZA 9 confirmations/plans UI into ApprovalDialog + PlansTab
matching the new visual direction — the backend (ConfirmationService, /confirmations,
/plans, permission engine from FAZA 10) already exists and must not be reimplemented.
```

Tasks:

```txt
1. Redesign existing ApprovalDialog (already built in FAZA 9) to match new visual direction.
2. Turn Plans UI into a persistent PlansTab within WorkspacePanel.
3. Reuse existing confirmation_id field/flow — do not invent a new one.
4. Reuse existing approve/reject API calls.
5. Do not use Notepad.
6. Do not auto-export .txt/.md.
```

Acceptance criteria:

```txt
- User sees Ricky proposal in app.
- User can approve/reject.
- Plans appear in Plans tab.
- Export only exists as optional explicit action.
```

---

## Redesign step 4 — Companion orb voice integration (maps to real FAZA 12)

Goal:

```txt
Companion orb becomes voice entry point and state indicator.
```

Tasks:

```txt
1. Add companion BrowserWindow.
2. Add Companion button in TopBar.
3. Show floating orb.
4. Restore main window.
5. Reflect VoiceState.
6. Add right-click menu.
7. Add drag + position persistence.
8. Do not create independent audio pipeline.
```

Acceptance criteria:

```txt
- Companion Mode works.
- Orb displays voice state.
- Existing realtime pipeline remains intact.
- No unsafe tool execution from companion renderer.
```

---

# Non-Goals

Do not implement these in this UI task:

```txt
- Python audio runtime
- custom Python STT
- custom Python TTS
- replacement for src/lib/realtime.ts
- full backend implementation
- real Windows automation execution
- coding-agent features
- VSCode/Cursor replacement
- wake word always-listening as default
- self-walking orb by default
- automatic .txt/.md plan files
```

---

# Important Engineering Rules

```txt
1. Preserve src/lib/realtime.ts voice pipeline.
2. Do not move microphone/STT/TTS into Python.
3. Do not put all UI code into App.tsx.
4. Do not expand electron/main.cjs with business logic.
5. Keep the app runnable after every phase.
6. Use typed state.
7. Keep mock data isolated.
8. Voice is primary; text is fallback.
9. Safety states must be visible.
10. High-risk actions must not look harmless.
11. Companion renderer must not execute tools directly.
12. Plans are app records, not Notepad files.
13. Export only on explicit user request.
14. No hardcoded user-facing GUI strings; use i18n keys.
15. Do not animate independent voice waveforms in multiple places at once.
16. Separate Voice Realtime Model from Text Fallback / Document / Local models.
17. Computer Mode ON must switch UI into safety-focused mode.
18. UI must not claim a tool was cancelled until backend/tool executor confirms it.
19. Do not use Notepad or any external app as transcript/draft/plan UI.
20. Voice input has three display modes: Ephemeral Command, Dictation Draft, Confirmation Review.
21. Do not always show full live transcript.
22. Show large editable transcript panel only for dictation/write-output tasks or when user requests review/correction.
23. Primary voice UX is click-to-start voice session, not hold-to-talk.
24. Push-to-talk can be optional/future setting, not default.
25. Partial transcript stays local unless final/user-approved content must be sent.
26. Risky actions require confirmation panel inside Ricky UI.
```

> Napomena: pravila 1-18 su iz originalnog V4 dokumenta; 19-26 su iz Codex-ovog dodatka (2026-07-05, "Voice Input UX, Dictation Mode i No-Notepad Rule" — vidi sekciju G iznad za puni kontekst).

---

# Suggested First Agent Task

> **Napomena:** ovaj zadatak pretpostavlja greenfield rad. Pošto voice-first shell (FAZA 8) i confirmations/plans (FAZA 9) već postoje, stvarni prvi zadatak treba biti "Redesign step 1" iz "Implementation Phases" sekcije iznad (redizajn postojećeg), ne ovaj generički scaffold. Ostavljeno ispod kao istorijski referentni tekst.

Start with this task:

```txt
Refactor Ricky Assistant UI into a voice-first app shell while preserving the existing src/lib/realtime.ts OpenAI Realtime/WebRTC pipeline.

Create:
- TopBar with VoiceState and backend status,
- LeftVoicePanel with smaller Ricky orb/avatar,
- WorkspacePanel with Output / Activity / Plans / Memory / Screens tabs,
- BottomVoiceBar with click-to-start voice session as primary action (do not
  implement hold-to-talk as default — see section G),
- secondary text fallback input,
- VoiceSession state model, conditional Voice Draft panel, ephemeral
  heard-summary display, and confirmation review display (section G) — never
  use Notepad for transcript or draft review,
- Realtime Event Router stub,
- VoiceState mapper stub,
- GUI localization foundation for sr-Latn/en/de/es/fr,
- Settings entry for Language,
- Future-safe Models settings structure,
- Computer Mode safety-focused UI state,
- Voice Visual Hierarchy rules.

Do not implement Python STT/TTS.
Do not replace src/lib/realtime.ts.
Do not add backend business logic to electron/main.cjs.
Use mock data where backend is not ready.

Acceptance criteria:
- app runs,
- UI is visibly voice-first,
- existing realtime voice code is preserved,
- text input exists but is secondary,
- VoiceState is visible,
- Activity and Plans tabs exist,
- no Python audio pipeline is introduced,
- no hardcoded visible GUI strings are introduced,
- voice wave animations are not duplicated across multiple independent areas,
- Computer Mode ON has a clear safety UI state,
- Model settings do not show one ambiguous generic default model.
```

---

# Final Desired Result

The redesigned UI should feel like:

```txt
A voice-first local desktop assistant that stays under user control.
```

not:

```txt
A chat app with a mic button.
A toy assistant demo with a big face.
A risky automation bot.
A coding assistant.
```

The user must always understand:

```txt
- whether Ricky is listening,
- what Ricky heard,
- whether Ricky is thinking or speaking,
- what Ricky wants to do,
- whether confirmation is required,
- what Ricky already did,
- where results/plans are stored,
- how to stop or correct Ricky.
```
