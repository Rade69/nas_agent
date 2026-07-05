# Ricky Assistant — UI Redesign Agent Prompt

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
