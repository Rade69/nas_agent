# Ricky Assistant — Voice-First UI + Companion Agent Prompt REVISED

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

Do not create separate VF phase numbering that conflicts with `MIGRATION_PLAN.md`.

This UI prompt maps to these migration phases.

## FAZA 6 — Voice-first UI around existing realtime client

Goal:

```txt
Make the app visibly voice-first while preserving src/lib/realtime.ts.
```

Tasks:

```txt
1. Add VoiceState type.
2. Add TopBar voice/backend status.
3. Add BottomVoiceBar.
4. Make text input secondary.
5. Add LeftVoicePanel.
6. Add Workspace tabs: Output / Activity / Plans / Memory / Screens.
7. Add Realtime Event Router.
8. Map existing realtime events to VoiceState.
9. Do not change audio path.
```

Acceptance criteria:

```txt
- UI is voice-first.
- Existing realtime voice path still works.
- Text input remains available.
- VoiceState visible in main UI.
```

---

## FAZA 7 — Activity + transcript UI

Goal:

```txt
Show what Ricky heard and did.
```

Tasks:

```txt
1. Add ActivityTab.
2. Add transcript preview.
3. Add event rows for listening/transcript/response/interruption.
4. Send activity/transcript events to backend when available.
5. Use mock fallback if backend is not ready.
```

Acceptance criteria:

```txt
- User can see what Ricky heard.
- User can see important voice events.
- UI works with mock and backend data.
```

---

## FAZA 8 — Approval dialog + Plans UI

Goal:

```txt
Risky actions are confirmed in UI and plans are stored as internal records.
```

Tasks:

```txt
1. Add ApprovalDialog.
2. Add PlansTab.
3. Add confirmation_id field to UI state.
4. Add approve/reject UI calls.
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

## FAZA 10 — Companion orb voice integration

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
```

---

# Suggested First Agent Task

Start with this task:

```txt
Refactor Ricky Assistant UI into a voice-first app shell while preserving the existing src/lib/realtime.ts OpenAI Realtime/WebRTC pipeline.

Create:
- TopBar with VoiceState and backend status,
- LeftVoicePanel with smaller Ricky orb/avatar,
- WorkspacePanel with Output / Activity / Plans / Memory / Screens tabs,
- BottomVoiceBar with Hold to talk as primary action,
- secondary text fallback input,
- Realtime Event Router stub,
- VoiceState mapper stub.

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
- no Python audio pipeline is introduced.
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
