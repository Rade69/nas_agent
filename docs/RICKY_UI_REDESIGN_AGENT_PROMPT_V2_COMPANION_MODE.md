# Ricky Assistant — UI Redesign Agent Prompt

> **Superseded.** Replaced by [RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md](./RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md) — this version predates the correction that `src/lib/realtime.ts` must remain the primary voice/audio pipeline. Kept for historical reference only.

## Purpose

Use this prompt with Codex, Claude Code, or another coding agent to redesign the current Ricky Assistant desktop UI.

The goal is not to make the existing screen only “prettier”. The goal is to turn the UI from a demo-looking assistant into a serious, usable desktop AI tool for:

- local AI assistant interaction,
- artifact/result display,
- Python backend status visibility,
- tool execution visibility,
- computer-use safety,
- logs, memory, screenshots, and future automation workflows.

The current concept is good:

```txt
Left side  = assistant identity, status, current action, short conversation preview
Right side = workspace / artifacts / tools / logs / memory / screenshots
Bottom     = command input and quick actions
Top        = app status, backend status, computer mode, window controls
```

But the current implementation is too empty, too toy-like, and unclear for serious use.

---

# Core Architecture Assumption

This UI belongs to a hybrid desktop app:

```txt
React renderer UI
        ↓
Electron preload / IPC
        ↓
Electron main process as shell and bridge
        ↓
Python backend as agent brain, tools runtime, storage, and automation layer
```

Important rules:

- React is responsible for presentation and interaction.
- Electron main process should stay thin and should not become the business logic layer.
- Python backend will eventually own tools, memory, storage, logs, screenshots, and agent runtime.
- UI must be designed so it can display Python backend state clearly.
- Do not hard-code fake backend logic deep into the UI. Use mock data only when needed and isolate it.

---

# High-Level UI Goal

Redesign the app into a professional dark desktop assistant.

The UI must always make these things obvious:

```txt
1. What state the assistant is in.
2. Whether the Python backend is connected.
3. Whether computer mode is ON or OFF.
4. What tool is currently running.
5. Whether the app is waiting for user confirmation.
6. Where the user types or speaks a command.
7. Where results/artifacts appear.
8. Where logs, tools, memory, and screenshots can be inspected.
```

If the user cannot immediately understand what the agent is doing, the design failed.

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

Use rounded corners, subtle borders, consistent spacing, and restrained glow effects.

Avoid:

- childish cartoon styling,
- huge empty spaces,
- oversized avatar taking most of the app,
- unlabeled icons with unclear meaning,
- floating buttons placed without visual hierarchy.

---

# Target Layout

Create a layout like this:

```txt
┌──────────────────────────────────────────────────────────────────────────┐
│ Ricky Assistant   Ready   Python backend connected   Computer Mode: OFF  │
├─────────────────────────────┬────────────────────────────────────────────┤
│ Assistant Panel              │ Workspace                                  │
│                              │                                            │
│ Small avatar/orb             │ Tabs: Output | Tools | Logs | Memory | Screens
│ Status                       │                                            │
│ Current action               │ Main result / artifact area                │
│ Conversation preview         │ Recent tool runs / contextual section      │
│                              │                                            │
├─────────────────────────────┴────────────────────────────────────────────┤
│ Ask Ricky anything...                         [Mic] [Send]               │
│ [Screenshot] [Inspect UI] [Open App] [New Note]     Computer Mode: OFF   │
└──────────────────────────────────────────────────────────────────────────┘
```

The app should feel like a serious local AI workbench, not only a mascot screen.

It should also support a compact **Companion Mode**: when the full workbench is hidden, a small draggable animated Ricky orb remains on screen and can restore the full app.

---

# Component Requirements

## 1. Top App Bar

Add a clear top bar.

Required elements:

```txt
Left:
- App icon
- "Ricky Assistant"

Center / center-left:
- Assistant state badge:
  - Ready
  - Listening
  - Thinking
  - Running tool
  - Waiting confirmation
  - Error

Next to it:
- Python backend connection badge:
  - Connected
  - Disconnected
  - Starting
  - Error

Right:
- Computer Mode badge/toggle:
  - OFF by default
  - ON clearly visible and visually stronger
- Settings button
- Minimize
- Maximize/restore
- Close
```

The current X button must not look like a random floating debug control. It belongs in a proper window control group.

Acceptance criteria:

- User can immediately see backend status.
- User can immediately see assistant state.
- Computer mode is always visible.
- Window controls are aligned and visually consistent.

---

## 2. Left Assistant Panel

The avatar should remain, but it must be smaller and more useful.

Required elements:

```txt
- Smaller avatar/orb, not oversized.
- Avatar reflects state through color/glow/animation.
- Assistant name: Ricky
- Current status label.
- Current action card.
- Conversation preview card.
```

The avatar should not dominate the screen.

Suggested avatar states:

```txt
Ready:
- calm blue ring
- neutral face/orb

Listening:
- animated pulse
- stronger blue glow

Thinking:
- purple/blue subtle rotating glow

Running tool:
- yellow/orange progress accent

Waiting confirmation:
- orange accent and small question/alert indicator

Error:
- red accent

Backend disconnected:
- muted/gray avatar
```

Current action card should show:

```txt
CURRENT ACTION
No action running
```

or:

```txt
CURRENT ACTION
Running: screen_snapshot
Risk: LOW
```

or:

```txt
CURRENT ACTION
Waiting for confirmation: computer_type_text
Risk: HIGH
```

Conversation preview should show only recent messages, for example:

```txt
You      12:45
Open Notepad

Ricky    12:45
Waiting for confirmation...

You      12:46
Take a screenshot

Ricky    12:46
Screenshot saved
```

Acceptance criteria:

- Avatar is reduced and no longer wastes the majority of the left side.
- Status and current action are visible without reading logs.
- Conversation preview is compact but useful.

---

## 3. Right Workspace Panel

Replace the current empty artifact panel with a tabbed workspace.

Required tabs:

```txt
Output
Tools
Logs
Memory
Screens
```

The tab system should be visible and clean.

### 3.1 Output Tab

Purpose:

- Main place for artifacts and results.

Empty state:

```txt
No output yet
Ask Ricky to do something or use a tool to see results here.
[Ask Ricky something]
```

When content exists, support these artifact types conceptually:

```txt
- markdown
- table
- code
- image
- JSON
- diagram
- log summary
```

Do not implement all renderers immediately if that is too much. But the layout must be ready for them.

Acceptance criteria:

- Empty state is helpful, not just a blank box.
- Output area is visually primary.
- It can display cards or structured content later.

---

### 3.2 Tools Tab

Purpose:

- Show available tools from the Python backend or mock tool registry.

Each tool row/card should show:

```txt
- Icon
- Tool name
- Short description
- Risk level
- Confirmation requirement
```

Example tools:

```txt
screen_snapshot
Description: Capture current desktop screenshot
Risk: LOW
Confirmation: No

ui_inspect
Description: Inspect current UI and active window
Risk: MEDIUM
Confirmation: No

computer_open_app
Description: Open an application
Risk: HIGH
Confirmation: Required

computer_type_text
Description: Type text in active window
Risk: HIGH
Confirmation: Required

delete_file
Description: Delete a file from disk
Risk: CRITICAL
Confirmation: Required + allowlist
```

Risk colors:

```txt
LOW      green
MEDIUM   yellow
HIGH     orange
CRITICAL red
```

Acceptance criteria:

- Tools are understandable without reading code.
- Risk is visible.
- High/critical tools look clearly more serious.

---

### 3.3 Logs Tab

Purpose:

- Show timeline of tool runs and important backend/agent events.

Each log row should show:

```txt
time
tool/event name
status
duration
risk
```

Example:

```txt
12:44:30   screen_snapshot       OK        340 ms     LOW
12:45:01   computer_open_app     OK        520 ms     HIGH
12:45:18   computer_type_text    WAITING   —          HIGH
12:46:02   backend               ERROR     —          —
```

Statuses:

```txt
OK
Running
Waiting confirmation
Error
Blocked
Cancelled
```

Acceptance criteria:

- User can understand what the agent did.
- Waiting confirmation is visually obvious.
- Errors are visible but not visually chaotic.

---

### 3.4 Memory Tab

Purpose:

- Show notes, records, and saved context.

Initial mock layout can include:

```txt
Search memory...
Recent notes
Recent records
Saved context
```

Do not overbuild memory yet. The UI should only prepare the space.

Acceptance criteria:

- Memory is present as a workspace concept.
- It does not need full backend integration in the first UI pass.

---

### 3.5 Screens Tab

Purpose:

- Show screenshots captured by tools.

Initial mock layout:

```txt
Screenshots
- thumbnail grid
- timestamp
- related tool run
- click to preview larger
```

Acceptance criteria:

- Screens tab exists.
- Empty state is clear.
- Layout can later receive real screenshot paths from Python backend.

---

## 4. Bottom Command Bar

The app currently lacks a clear text input. Add one.

Required elements:

```txt
- Main input with placeholder:
  "Ask Ricky anything..."
- Send button
- Voice/microphone button
- Quick action buttons:
  - Screenshot
  - Inspect UI
  - Open App
  - New Note
- Computer Mode status/toggle on the right
```

Suggested layout:

```txt
[ Ask Ricky anything...                                ] [Mic] [Send]
[ Screenshot ] [ Inspect UI ] [ Open App ] [ New Note ]     Computer Mode: OFF
```

Behavior for now:

- Input can be UI-only if backend is not wired yet.
- Buttons may call existing handlers if available.
- Otherwise they can be placeholders with clearly named handler functions.

Acceptance criteria:

- User knows where to type.
- Send and mic are visually obvious.
- Quick actions are labeled, not only icons.

---

# Safety and Confirmation UI

Computer-use safety must be visible in the UI.

When a high-risk action is requested, show a confirmation card/modal.

Example:

```txt
Ricky wants to run a high-risk action

Tool:
computer_type_text

Target:
Active window: Notepad
Process: notepad.exe

Text:
"Example text..."

Risk:
HIGH

[Cancel] [Allow once]
```

For critical actions:

```txt
Critical action blocked by default
This tool requires explicit allowlist configuration.
```

Acceptance criteria:

- High-risk actions are never visually silent.
- Waiting confirmation state is reflected in:
  - top status,
  - avatar,
  - current action card,
  - logs.
- User remains in control.

---

# Data Model for UI State

Create a clean frontend state shape, even if populated with mock data first.

Suggested TypeScript types:

```ts
type AssistantState =
  | "ready"
  | "listening"
  | "thinking"
  | "running_tool"
  | "waiting_confirmation"
  | "error";

type BackendState =
  | "connected"
  | "disconnected"
  | "starting"
  | "error";

type RiskLevel =
  | "low"
  | "medium"
  | "high"
  | "critical";

type ToolStatus =
  | "ok"
  | "running"
  | "waiting_confirmation"
  | "error"
  | "blocked"
  | "cancelled";

type WorkspaceTab =
  | "output"
  | "tools"
  | "logs"
  | "memory"
  | "screens";

interface ToolInfo {
  name: string;
  description: string;
  risk: RiskLevel;
  requiresConfirmation: boolean;
}

interface ToolRun {
  id: string;
  timestamp: string;
  name: string;
  status: ToolStatus;
  durationMs?: number;
  risk?: RiskLevel;
}

interface ConversationPreviewItem {
  id: string;
  role: "user" | "assistant";
  text: string;
  time: string;
  status?: "ok" | "warning" | "error";
}

interface ArtifactItem {
  id: string;
  type: "markdown" | "table" | "code" | "image" | "json" | "diagram" | "log";
  title: string;
  content: unknown;
  createdAt: string;
}
```

Do not scatter unrelated state across many components without structure.

---

# Suggested React Component Structure

Refactor or create components like this:

```txt
src/
  components/
    layout/
      AppShell.tsx
      TopBar.tsx
      LeftAssistantPanel.tsx
      WorkspacePanel.tsx
      BottomCommandBar.tsx

    assistant/
      AssistantAvatar.tsx
      AssistantStatusBadge.tsx
      CurrentActionCard.tsx
      ConversationPreview.tsx

    workspace/
      WorkspaceTabs.tsx
      OutputTab.tsx
      ToolsTab.tsx
      LogsTab.tsx
      MemoryTab.tsx
      ScreensTab.tsx

    safety/
      ConfirmationModal.tsx
      RiskBadge.tsx

    common/
      IconButton.tsx
      StatusPill.tsx
      Panel.tsx
      EmptyState.tsx
```

Keep components small.

Do not put the entire redesign into one giant `App.tsx`.

---

# CSS / Styling Requirements

Use existing styling approach if the project already has `styles.css`.

Create or organize CSS sections:

```txt
/* Design tokens */
/* App shell */
/* Top bar */
/* Assistant panel */
/* Avatar */
/* Workspace */
/* Tabs */
/* Logs */
/* Tools */
/* Bottom command bar */
/* Buttons */
/* Risk badges */
/* Modals */
/* Responsive behavior */
```

Use CSS variables:

```css
:root {
  --bg: #080B10;
  --panel: #11161D;
  --panel-2: #151B24;
  --border: #263241;
  --primary: #3EA6FF;
  --text: #F4F7FB;
  --muted: #8D9AAA;
  --success: #22C55E;
  --warning: #F5A524;
  --high: #F97316;
  --danger: #EF4444;
}
```

Acceptance criteria:

- No random hard-coded colors scattered everywhere.
- UI remains readable at 1366x768 and 1440x900.
- Panels do not overlap.
- Bottom command bar does not cover content.
- Window close/minimize buttons are easy to reach.

---

# Implementation Phases

## Phase UI-1 — Layout Skeleton

Goal:

- Build the new app shell layout.

Tasks:

```txt
1. Add TopBar.
2. Add LeftAssistantPanel.
3. Add WorkspacePanel.
4. Add BottomCommandBar.
5. Keep existing app functionality working as much as possible.
6. Use mock UI state where backend data does not exist yet.
```

Acceptance criteria:

```txt
- App opens without runtime errors.
- Layout has top, left, right, and bottom sections.
- Existing window close functionality still works.
- No major visual overlap.
```

---

## Phase UI-2 — Assistant State and Avatar

Goal:

- Make assistant status visible and meaningful.

Tasks:

```txt
1. Resize avatar.
2. Add status-specific avatar visual states.
3. Add current action card.
4. Add conversation preview.
5. Add top status badge.
```

Acceptance criteria:

```txt
- Ready/listening/thinking/running/waiting/error states have different visuals.
- Avatar no longer dominates the screen.
- Current action is visible.
```

---

## Phase UI-3 — Workspace Tabs

Goal:

- Replace empty artifact panel with tabbed workspace.

Tasks:

```txt
1. Add Output tab.
2. Add Tools tab.
3. Add Logs tab.
4. Add Memory tab.
5. Add Screens tab.
6. Add useful empty states.
```

Acceptance criteria:

```txt
- User can switch tabs.
- Output tab is default.
- Tools tab shows tool cards/rows.
- Logs tab shows recent tool runs.
- Empty states are informative.
```

---

## Phase UI-4 — Bottom Command Bar

Goal:

- Add clear command input and quick actions.

Tasks:

```txt
1. Add main command input.
2. Add send button.
3. Add microphone button.
4. Add quick action buttons.
5. Add computer mode status/toggle.
```

Acceptance criteria:

```txt
- User clearly knows where to type.
- Quick actions have labels.
- Computer mode is visible.
```

---

## Phase UI-5 — Safety/Confirmation UI

Goal:

- Add visual safety layer for high-risk actions.

Tasks:

```txt
1. Add RiskBadge component.
2. Add ConfirmationModal component.
3. Add waiting confirmation UI state.
4. Show confirmation example using mock state if backend is not ready.
```

Acceptance criteria:

```txt
- High-risk action has visible confirmation UI.
- Waiting state is reflected in top bar, avatar/current action, and logs.
- Critical action messaging is clear.
```

---

## Phase UI-6 — Backend Integration Preparation

Goal:

- Prepare UI for Python backend without requiring full backend implementation.

Tasks:

```txt
1. Create frontend API/client layer for backend status.
2. Create typed mock data fallback.
3. Create functions for:
   - getBackendStatus()
   - getTools()
   - getRecentToolRuns()
   - sendCommand()
   - requestToolExecution()
4. Keep all mock data isolated.
```

Acceptance criteria:

```txt
- UI is not tightly coupled to hard-coded demo data.
- Mock data can later be replaced by real Python backend calls.
- No backend logic is buried in visual components.
```

---



---

# Companion Mode / Floating Ricky

Add a second UI mode called **Companion Mode**.

This mode replaces the idea of simply hiding the app. When the user hides/minimizes the main app, the full window should disappear and a small animated Ricky orb should remain on screen.

This is not a toy feature. It is a compact assistant presence that lets the user keep Ricky available without keeping the full workbench window open.

## Core Concept

```txt
Normal Mode
= full Ricky Assistant workbench window

Companion Mode
= small floating Ricky orb on the desktop
```

The companion orb should be:

```txt
- small
- animated
- draggable
- always on top
- optional / user-controlled
- able to restore the main window
- able to show assistant/backend status
- able to expose a compact right-click menu
```

Important:

```txt
The orb may have subtle idle animation.
It must not move around the screen by itself by default.
Automatic idle movement can exist later as an optional setting, but default must be OFF.
```

The assistant must remain under user control.

---

## Companion Mode Behavior

When the user clicks the main window action:

```txt
Companion
```

or:

```txt
Minimize to Companion
```

the app should:

```txt
1. Hide the main Ricky Assistant window.
2. Open/show a small transparent floating Ricky orb.
3. Keep the orb always on top.
4. Allow the user to drag the orb around the screen.
5. Restore the main window when the user left-clicks or double-clicks the orb.
6. Keep assistant/backend state visible through orb color/animation.
```

When the main window is restored:

```txt
1. Hide the companion window.
2. Restore/focus the main window.
3. Preserve previous main window state.
```

Acceptance criteria:

```txt
- Main window can enter Companion Mode.
- Companion orb appears.
- Orb can restore the main window.
- App does not quit when entering Companion Mode.
- Companion Mode does not break backend connection.
```

---

## Companion Window Technical Requirement

Do not fake Companion Mode with only CSS inside the main window.

Use a second Electron BrowserWindow.

Suggested windows:

```txt
mainWindow
= full Ricky Assistant workbench UI

companionWindow
= small transparent floating orb
```

Suggested Electron companion window options:

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

The exact size can be adjusted, but it should stay compact.

Acceptance criteria:

```txt
- Companion Mode uses a separate Electron window.
- The companion window is frameless and visually transparent around the orb.
- The companion window does not appear as a full app window in the taskbar.
```

---

## Companion Orb Visual States

The companion orb must reflect the same assistant states as the main avatar.

Required states:

```txt
Ready
Listening
Thinking
Running tool
Waiting confirmation
Error
Backend disconnected
```

Visual behavior:

```txt
Ready:
- calm blue ring
- subtle glow
- no strong movement

Listening:
- blue pulse animation
- slightly stronger glow

Thinking:
- purple/blue shimmer or slow rotating ring

Running tool:
- progress ring around orb
- yellow/orange accent

Waiting confirmation:
- orange glow
- small question/alert indicator

Error:
- red glow
- short shake animation or red pulse

Backend disconnected:
- gray/muted orb
- no glow
- disabled-looking state
```

Acceptance criteria:

```txt
- User can understand current state from the orb alone.
- Waiting confirmation and error states are impossible to miss.
- Running tool state should feel active but not chaotic.
```

---

## Companion Mode Context Menu

Right-clicking the companion orb should open a compact menu.

Suggested menu items:

```txt
Open Ricky
Ask quick command
Take screenshot
Inspect UI
Computer Mode: OFF/ON
Mute voice
Settings
Quit
```

Rules:

```txt
- Open Ricky restores the full main window.
- Quit exits the entire app.
- Screenshot and Inspect UI should call existing tool handlers if available.
- If backend/tool layer is not ready, keep handlers as named placeholders.
- Computer Mode must not be accidentally enabled.
```

Computer Mode rule:

```txt
If the user tries to enable Computer Mode from the companion menu,
show a confirmation first.
```

Acceptance criteria:

```txt
- Context menu opens on right-click.
- Open Ricky works.
- Quit works.
- Dangerous actions are not silently executed.
```

---

## Companion Mode Dragging

The orb must be movable by the user.

Requirements:

```txt
- User can drag the orb around the desktop.
- The app remembers the last orb position.
- The orb should not open outside the visible screen area.
- If the last position is invalid because monitor layout changed, reset to a safe default position.
```

Suggested default position:

```txt
Bottom-right area of primary display, with margin.
```

Suggested stored setting:

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
- Orb position persists between sessions.
- Orb remains visible after monitor/DPI changes.
- Dragging does not accidentally trigger restore.
```

---

## Optional Later Behavior: Dock / Snap

Do not implement this in the first pass unless simple.

Future behavior:

```txt
- Orb can snap to left/right screen edge.
- Orb can reduce opacity when idle.
- Orb becomes fully visible on hover.
- Orb can be docked as a small side tab.
```

Default:

```txt
Dock/snap behavior can be OFF until implemented properly.
```

---

## Optional Later Behavior: Idle Movement

Do not implement self-walking movement by default.

If implemented later:

```txt
Setting:
Companion Mode → Idle movement: ON/OFF

Default:
OFF
```

Rules:

```txt
- Movement must be subtle.
- Movement must stop on hover.
- Movement must stop when user drags the orb.
- Movement must never cover important UI intentionally.
- Movement must never happen during waiting confirmation or error states.
```

This is optional and low priority.

---

## Companion Mode Integration With Main UI

Update the main UI top bar or window controls.

Replace unclear:

```txt
Hide
```

with one of:

```txt
Companion
```

or:

```txt
Minimize to Companion
```

Recommended:

```txt
Companion
```

Add tooltip:

```txt
Minimize to floating Ricky companion
```

When Companion Mode is active and the main window is restored, show no duplicate companion orb.

Acceptance criteria:

```txt
- Main UI has a clear Companion action.
- The old Hide behavior is replaced or clearly separated.
- User understands that Ricky remains available after hiding the main window.
```

---

## Companion Mode IPC / Event Requirements

Add clean IPC boundaries.

Suggested IPC channels:

```txt
app:enter-companion-mode
app:exit-companion-mode
companion:restore-main-window
companion:get-state
companion:update-state
companion:show-context-menu
companion:save-position
companion:get-position
```

Do not let the companion renderer directly access unsafe APIs.

State should flow from the main app/backend to companion window:

```txt
Python backend / UI state
        ↓
Electron main
        ↓
main renderer + companion renderer
```

Acceptance criteria:

```txt
- Companion window receives assistant state updates.
- Companion window can request restore.
- Companion window does not own agent logic.
- Companion window does not execute tools directly without main process/backend validation.
```

---

## Companion Mode File/Component Structure

Suggested files:

```txt
electron/
  core/
    window.cjs
    companionWindow.cjs
  services/
    companionState.cjs
    companionPositionStore.cjs

src/
  companion/
    CompanionApp.tsx
    CompanionOrb.tsx
    CompanionContextMenu.tsx
    companion.css

  components/
    layout/
      TopBar.tsx
```

If the project currently has a simpler structure, adapt this without overengineering.

Do not put all companion logic directly into `main.cjs`.

Acceptance criteria:

```txt
- Companion window logic is isolated.
- Main app UI and companion UI are separate renderers or clearly separated routes.
- Existing main UI remains maintainable.
```

---

## Companion Mode Implementation Phases

### Phase CM-1 — Basic Companion Window

Goal:

```txt
Create the second Electron window and basic mode switching.
```

Tasks:

```txt
1. Add companionWindow creation logic.
2. Add Companion button in main UI.
3. On click, hide mainWindow and show companionWindow.
4. Render a simple Ricky orb in the companion window.
5. Left-click or double-click orb restores mainWindow.
6. Hide companionWindow after restore.
```

Acceptance criteria:

```txt
- Companion button works.
- Main window hides.
- Orb appears.
- Orb restores main window.
- App does not quit.
```

---

### Phase CM-2 — Draggable Orb and Position Persistence

Goal:

```txt
Make the companion orb usable on real desktop setups.
```

Tasks:

```txt
1. Allow dragging the orb.
2. Save last position.
3. Restore last position on next Companion Mode open.
4. Validate saved position against current display bounds.
5. Add safe fallback position.
```

Acceptance criteria:

```txt
- Orb is draggable.
- Position is remembered.
- Orb remains visible on changed monitor layout.
```

---

### Phase CM-3 — State Animations

Goal:

```txt
Mirror assistant/backend state inside the companion orb.
```

Tasks:

```txt
1. Add orb visual states:
   - ready
   - listening
   - thinking
   - running_tool
   - waiting_confirmation
   - error
   - backend_disconnected
2. Connect state updates from main UI/mock state first.
3. Prepare for backend-driven updates later.
```

Acceptance criteria:

```txt
- States are visually distinct.
- Waiting confirmation and error states are prominent.
- Backend disconnected is clearly muted/disabled.
```

---

### Phase CM-4 — Companion Context Menu

Goal:

```txt
Add compact right-click menu.
```

Tasks:

```txt
1. Add right-click context menu.
2. Add Open Ricky.
3. Add Take Screenshot.
4. Add Inspect UI.
5. Add Computer Mode OFF/ON item.
6. Add Settings.
7. Add Quit.
8. Add confirmation requirement for enabling Computer Mode.
```

Acceptance criteria:

```txt
- Right-click menu works.
- Open Ricky restores app.
- Quit exits app.
- Computer Mode cannot be enabled silently.
```

---

### Phase CM-5 — Polish and Optional Docking

Goal:

```txt
Improve behavior without making the companion annoying.
```

Tasks:

```txt
1. Add hover effect.
2. Add optional opacity reduction when idle.
3. Optionally add edge snap.
4. Add settings toggles if settings screen exists.
```

Acceptance criteria:

```txt
- Companion mode feels helpful.
- It does not block normal desktop usage.
- Self-moving behavior is not enabled by default.
```

---

# Updated Non-Goals

Do not implement these in the first Companion Mode pass:

```txt
- Orb walking around by itself by default
- Full settings panel for every companion behavior
- Voice wake word
- Real Python backend computer-use execution
- Complex animations that hurt performance
- Companion window owning agent logic
- Direct unsafe tool execution from companion renderer
```

---

# Updated First Agent Task Including Companion Mode

After the base UI shell is stable, give the agent this task:

```txt
Implement Companion Mode for Ricky Assistant.

Create a separate small transparent Electron companion window that shows a floating Ricky orb.

Add a "Companion" button to the main UI top bar. When clicked, hide the main window and show the companion window.

The orb must restore the main window on click or double-click.

Keep this phase simple:
- no real backend integration required,
- use mock assistant state,
- no self-moving orb,
- no unsafe tool execution.

Acceptance criteria:
- main window hides,
- companion orb appears,
- orb restores main window,
- app remains running,
- companion window is frameless, transparent, always-on-top, compact, and skipped from taskbar,
- companion logic is not dumped into electron/main.cjs.
```


# Non-Goals for First UI Redesign

Do not implement these in the first UI pass:

```txt
- Full Python backend
- Real OpenAI agent runtime
- Full tool execution engine
- Real Windows UI automation
- Complete memory system
- Packaging / installer
- Multi-agent architecture
```

This task is UI redesign and frontend structure only.

---

# Important Engineering Rules

Follow these rules strictly:

```txt
1. Do not put all UI code into App.tsx.
2. Do not expand electron/main.cjs with new business logic.
3. Do not remove working IPC/window controls unless replacing them safely.
4. Keep the app runnable after every phase.
5. Prefer small, reviewable commits.
6. Use clear component names.
7. Use typed state where possible.
8. Keep mock data isolated.
9. Do not hide safety states.
10. Do not make high-risk computer-use actions look harmless.
```

---

# Suggested First Agent Task

Start with this exact first task:

```txt
Refactor the current Ricky Assistant UI into a new app shell layout.

Create a top app bar, left assistant panel, right tabbed workspace, and bottom command bar.

Keep existing functionality working where possible. Do not change backend logic. Do not add new Electron main-process business logic.

Use mock frontend state for:
- assistant status,
- backend status,
- computer mode,
- tool list,
- recent tool runs,
- conversation preview.

Implement the layout with small React components and CSS variables.

Acceptance criteria:
- app runs,
- layout is stable,
- avatar is smaller,
- command input exists,
- workspace has Output / Tools / Logs / Memory / Screens tabs,
- backend and computer mode status are visible.
```

---

# Final Desired Result

The redesigned UI should feel like:

```txt
A professional local AI desktop workbench
```

not:

```txt
A toy assistant demo with a big face and empty panel
```

The user must always understand:

```txt
- what Ricky is doing,
- what Ricky can do,
- what Ricky just did,
- whether the backend is alive,
- whether computer control is enabled,
- where results are displayed,
- where to type the next command.
```
