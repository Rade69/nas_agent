# RICKY UI IMPLEMENTATION PROMPT — FINAL GUI + MINIMIZED AVATAR

> **Napomena (2026-07-06, Claude Code integracija):** Ovo je **vizuelni redesign postojećih, već implementiranih i testiranih** komponenti (FAZA 8 voice-first UI, FAZA 9 confirmations/plans, FAZA 12 Companion orb), ne greenfield build. Ne brisati/ne prepisivati postojeći kod bez provjere — restilizovati ga. Postojeće komponente/API koje ovaj dokument redizajnira:
>
> - `src/components/CompanionOrb.tsx` (Companion window, već postoji — sekcija 10 ovdje ga vizuelno redizajnira)
> - `ConfirmationDialog` + `POST/GET /confirmations*` (`ConfirmationService`, `confirmation_id`/`tool_name`/`payload_hash`/`expires_at`/`risk_level`) — sekcija 6 ovdje
> - `PlansPanel` + `POST/GET /plans*` (`PlanService`) — sekcija 8 ovdje
> - `/events` polling + `EventBus` (aktivnost/artifact bridge, FAZA 11) — sekcija 7 ovdje
> - `VoiceState` model iz `src/lib/realtime.ts` (Realtime Event Router) — orb state u sekciji 9 mora mapirati na postojeće `VoiceState` vrijednosti, ne izmišljati paralelan state model
>
> Detaljan komponentni/IPC/event-boundary spec (uključujući već integrisan Voice Input UX dodatak — Ephemeral Command/Dictation/Confirmation Review modovi, click-to-talk umjesto hold-to-talk, No-Notepad pravilo) je u [RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md](./RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md) — taj dokument je autoritativan za arhitekturu/ponašanje, ovaj dokument je autoritativan za **finalni vizuelni izgled** (boje, layout, orb dizajn iz odobrenog mockup-a). Lokalizacija (jezici, `interface_language`, Settings model) je autoritativno u [RICKY_GUI_LOCALIZATION_PLAN.md](./RICKY_GUI_LOCALIZATION_PLAN.md) — sekcija 12 ovdje samo skicira primjer, ne duplirati pravila odatle.
>
> **Nedostajala i ovdje dopunjena stavka:** ovaj dokument u originalnoj verziji nije pominjao Stop/cancel kontrolu tokom aktivnog izvršavanja — vidi novu sekciju **3.4 Stop / Cancellation Control** ispod. Bez nje bi implementacija regresirala već postojeće FAZA 10 cancellation UX pravilo iz V4 dokumenta.

## Goal

Implement the final Ricky desktop UI based on the approved dark-mode mockup and the approved Ricky orb/avatar concept.

This task includes:

1. the **main Ricky application UI**
2. the **state-based screen behavior**
3. the **Ricky voice orb/avatar**
4. the **minimized / floating Ricky companion avatar**
5. the **interaction rules, visual hierarchy, and implementation constraints**

Do not redesign the product from scratch.
Do not simplify the identity into a generic microphone UI.
Follow the approved structure and visual direction.

---

# 1. Product Direction

Ricky is a **voice-first desktop assistant** with a professional dark UI.

The UI must feel:

- premium
- modern
- clean
- slightly futuristic
- professional, not childish
- assistant-like, not like a generic dashboard
- focused on clarity and control

The approved direction is:

```txt
dark premium desktop UI
+ blue/cyan primary accent
+ voice-first interaction
+ state-based main content
+ Ricky orb with stylized R in a glowing voice ring
```

---

# 2. Core Design Principles

## 2.1 State machine, not cluttered dashboard

The UI must support distinct states and should not overload the user with too many equally important panels at once.

Main states:

1. Idle / Ready
2. Dictation Mode
3. Confirmation Mode

Supporting panels should appear as needed, not all expanded with equal emphasis all the time.

## 2.2 One main status source

Do not duplicate the same status message in multiple unrelated places.

There should be one dominant status source for the current global state.

Examples:

- Ready / Spreman
- Listening / Diktiranje / Slušam
- Waiting confirmation / Čekam potvrdu
- Error / Greška

## 2.3 Confirmation must be unavoidable

Risky actions must use a dominant confirmation modal.

Do not render confirmation as a small banner or visually weak secondary card.

## 2.4 Warning color only for risk / caution

Color semantics must be strict:

- blue = primary / active / assistant / brand
- green = success / completed / safe positive result
- yellow/orange = warning / confirmation / attention / risk
- red = error / blocked / dangerous
- gray = neutral / secondary text / inactive

Do not use warning color for ordinary progress states.

## 2.5 Do not use Notepad or external apps as UI

Transcript review, draft editing, plans, confirmations and previews all happen inside Ricky UI.

---

# 3. Main Layout

Implement the UI structure based on the approved mockup.

## 3.1 Top Bar

Top bar contains:

- Ricky logo/avatar icon (small)
- app name: `Ricky`
- current global status text (e.g. `Spreman`, `Diktiranje`, `Čekam potvrdu`)
- Computer Mode pill
- utility icons/buttons on the right
- window controls on desktop

Recommended top bar zones:

### Left
- small Ricky orb or small circular Ricky icon
- `Ricky`
- current state text

### Center / right-center
- `Computer mode: ISKLJUČEN` or `Computer mode: UKLJUČEN`

### Right
- quick utility icon buttons
- minimize
- maximize
- close

Top bar must remain visually lightweight and not too tall.

---

## 3.2 Left Sidebar (main navigation)

Sidebar should exist in the main desktop view.

Sections:

- Početna
- Aktivnost
- Planovi
- Memorija
- Snimci ekrana
- Postavke

Bottom of sidebar can contain:

- Ricky version text
- backend state
- local/privacy indicator if still needed

Rules:

- Sidebar can collapse on smaller widths
- Sidebar active item must be clearly highlighted
- Sidebar should not dominate the layout
- On smaller screens it can collapse into icons or a drawer

---

## 3.3 Main content area

This is the primary state-driven workspace.

The main content changes based on the current Ricky state.

Do not keep every panel fully open at once.

---

## 3.4 Stop / Cancellation Control

This is a required safety control, not optional polish. It is missing from the
approved mockup screenshot but must still be implemented — see
`docs/SECURITY_HARDENING_PLAN.md` section 25 and the existing
`POST /tools/executions/{id}/cancel` endpoint (FAZA 10 cancellation state
machine), and the equivalent requirement already specified in
`RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md`.

Rules:

- Whenever Ricky is actively listening, thinking, speaking, or running a tool
  (`tool_state` is `preflight`/`commit_started`/`running`, or `VoiceState` is
  the equivalent active state), the primary voice CTA on the Idle/Ready screen
  must turn into a visible **Stop** control instead of (or alongside) the
  microphone icon.
- Clicking Stop calls the cancel endpoint for the in-flight execution and/or
  tears down the Realtime session, per the two-layer model in
  `SECURITY_HARDENING_PLAN.md` section 25 (voice interruption and tool
  cancellation are separate layers).
- The UI must report the *real* outcome, not an optimistic one: if the backend
  returns `tool_state: cannot_cancel_commit_started`, show that the action
  already committed and could not be stopped — do not show a generic
  "cancelled" success state in that case.
- This is independent of the Confirmation Modal's `Otkaži` button (section 6),
  which rejects a *pending* confirmation before execution starts, not an
  in-flight one.

---

# 4. Idle / Ready Screen

This is the default `Spreman` state.

## 4.1 Purpose

When Ricky is idle/ready, the user should clearly understand:

- Ricky is available
- how to start interaction
- what the last relevant activity was
- how to type instead of speaking

## 4.2 Main composition

Center area should include:

- large Ricky orb/avatar
- headline like: `Ricky je spreman`
- supportive line like: `Klikni mikrofon ili reci "Ricky"`
- main microphone action button — becomes a **Stop** control while Ricky is
  active (see 3.4); interaction is click-to-talk, not hold-to-talk (per the
  Voice Input UX addendum in V4_AFTER_REVIEW)
- text fallback input below

Right-side supporting cards may show:

- recent activity
- quick commands

These supporting cards must be visually secondary relative to the center orb and primary interaction.

## 4.3 Idle screen elements

Required:

- large Ricky orb centered
- main voice CTA button
- text input field
- recent activity card
- quick commands card

Recent activity card example:

- Email poslan šefu
- Nacrt izvještaja spreman
- Otvoren dictation mode
- Screenshot snimljen

Quick commands card example:

- Napiši email šefu
- Napravi screenshot
- Otvori Notepad
- Planiraj sastanak sutra u 10h

---

# 5. Dictation Mode Screen

This is the state when the user dictates a longer text or explicitly asks Ricky to write something.

## 5.1 Purpose

The editor becomes the main focus.
This is not a tiny transcript preview.
This is a large internal Ricky editor.

## 5.2 Visual structure

Top section should indicate dictation mode, for example:

- `DICTATION MODE`
- auto-save status
- cancel/close action

Main center area:

- large editable text editor
- text is displayed clearly with comfortable spacing

Bottom actions:

Primary:
- `Pošalji agentu`

Secondary:
- `Nastavi diktiranje`
- `Doradi`
- `...`

Doradi dropdown options may include:
- Formalizuj
- Skrati
- Provjeri pravopis
- Prevedi na engleski

Rules:

- editor must be the dominant visual element
- do not keep unrelated panels open around it
- action layout must remain clean
- do not overload the editor toolbar
- secondary text actions can be grouped in dropdowns

---

# 6. Confirmation Modal

This is the required pattern for risky actions.

## 6.1 Purpose

When Ricky wants to perform an action outside the app or something that needs user approval, the UI must open a dominant modal.

## 6.2 Example use cases

- send email
- type text into another app
- delete file
- open a sensitive app
- operate with elevated risk

## 6.3 Modal behavior

The modal must:

- dim the background
- sit above all other content
- visually dominate the screen
- clearly state what Ricky wants to do
- make the user consciously approve or cancel

## 6.4 Required content

The confirmation modal should include:

- title like `Ricky želi izvršiti ovu akciju`
- short subtitle/warning
- action summary table
- target or recipient
- subject/title if relevant
- risk level
- expiry time if applicable
- expandable detail area if needed

Example fields:
- Akcija
- Prima / Cilj
- Predmet
- Rizik
- Ističe za

Buttons:
- `Izmijeni`
- `Otkaži`
- primary confirm button like `Pošalji email`

## 6.5 Backend mapping

These fields are not free-form — they must bind to the real confirmation
record from `ConfirmationService`/`permission_engine.py` (FAZA 9/10):

- `Akcija` → `tool_name` / `action_name`
- `Prima` / `Cilj` / `Predmet` → fields inside `payload` (tool-specific)
- `Rizik` → `risk_level`
- `Ističe za` → countdown to `expires_at`
- confirm button → `POST /confirmations/{id}/approve`, then the tool call is
  retried with that `confirmation_id` (the permission engine validates it is
  bound to the exact `tool_name` + `payload_hash`, not just "approved")
- `Otkaži` → `POST /confirmations/{id}/reject` (rejects the pending proposal;
  this is not the same as cancelling an already-running tool — see 3.4)

## 6.6 Color rule

Risk badge and warning accent may use yellow/orange.
Do not use that same warning color for normal completed actions.

---

# 7. Activity Drawer

Activity should be available as a separate panel/drawer or dedicated screen.

## 7.1 Purpose

User can inspect detailed history without cluttering the default voice experience.

## 7.2 Content

Each activity item may show:

- status icon
- action summary
- supporting detail
- timestamp

Examples:
- Email poslan šefu
- Nacrt izvještaja spreman
- Otvoren dictation mode
- Screenshot snimljen
- Alat izvršen

Include a CTA like:
- `Prikaži cijelu historiju`

Backend mapping: this drawer renders the existing `/events` polling feed
(`EventBus`, FAZA 11) — restyle the existing activity list component, do not
build a new data source.

---

# 8. Plans Drawer

Plans should be available as a separate panel/drawer or screen.

## 8.1 Purpose

Allow Ricky to show active, suggested and completed plans/tasks.

## 8.2 Sections

Tabs or segmented control:
- Aktivni
- Predloženi
- Završeni

Each plan card can contain:
- title
- subtitle / time
- badge status

Examples:
- Sedmični izvještaj prodaje
- Podsjetnik: Sastanak tim
- Analiza konkurencije

Primary CTA:
- `Novi plan`

Backend mapping: this drawer renders the existing `PlanService` /
`POST/GET /plans*` REST API (FAZA 9) — restyle `PlansPanel`, do not build a
new plan data model.

---

# 9. Ricky Orb / Main Avatar

This is a crucial part of the design.

## 9.1 Concept

Do not use a human-like face.

Use the approved Ricky visual identity:

```txt
stylized glowing R
inside a premium circular orb
surrounded by a glowing voice-reactive ring
```

## 9.2 Visual characteristics

The Ricky orb should include:

- the approved stylized `R` symbol
- deep dark circular base
- glowing blue/cyan center
- surrounding luminous ring
- outer voice-reactive wave ring with blue/purple/cyan energy feel
- premium assistant aesthetic

It should feel like:
- AI assistant identity
- futuristic but professional
- clean and visually alive
- not childish
- not like a human portrait

## 9.3 Color direction

Primary orb colors:
- electric blue
- cyan
- subtle violet/purple highlights
- deep navy/dark background

Do not use too many different accent colors.
Keep it controlled and premium.

## 9.4 State behavior of orb

The orb must visually react to state. Map directly to the existing
`VoiceState` type in `src/lib/voiceState.ts` — do not invent a parallel state
model:

### `idle`
- calm glow
- soft pulse
- stable ring
- low motion

### `listening` / `transcribing` (Dictating)
- outer ring becomes more active
- subtle waveform-like motion
- slightly brighter glow
- communicates that Ricky is hearing the user

### `thinking`
- smoother slow pulse
- less waveform energy
- more concentrated glow

### `speaking`
- ring visibly pulses in a voice-like manner
- strongest controlled animation
- similar spirit to premium voice assistants like Siri-inspired orb motion
- avoid chaotic animation

### `waiting_confirmation`
- orb calms down
- warning state is carried by modal, not by chaotic orb behavior

### `interrupted` / `muted`
- distinct from `error` — these are user-initiated states (Stop pressed, mic
  muted), not failures; orb should look deliberately calmed/silenced, not
  broken

### `error`
- orb should reduce blue glow and optionally show a restrained red accent or error indicator

## 9.5 Do not overcomplicate

The orb can be visually rich, but it should remain clean.
It must not become noisy, overly decorative or game-like.

---

# 10. Minimized / Floating Ricky Companion Avatar

This must also be implemented.

## 10.1 Purpose

When Ricky main window is minimized/hidden, Ricky should remain available as a floating companion orb on the desktop.

This floating version should preserve the identity of the main orb.

## 10.2 Core rule

The minimized companion is the **same Ricky avatar concept** as the main orb, but adapted for persistent desktop presence.

It should be:

- smaller
- lighter
- more transparent
- less visually aggressive
- still clearly recognizable as Ricky

## 10.3 Visual behavior

Compared to the main orb, the minimized orb should have:

- reduced size
- reduced glow intensity
- partially transparent background
- softer ring detail
- preserved stylized `R`
- preserved voice ring identity

Suggested behavior:

### Idle
- 60–80% opacity
- soft subtle glow
- calm ring

### Hover
- increases opacity
- glow becomes stronger
- indicates interactivity

### Listening / Speaking
- becomes more vivid
- pulse animation becomes clearer
- still not too distracting

### Inactive for some time
- may fade slightly more
- remain visible but not intrusive

## 10.4 Interaction

Floating companion orb should support:

- drag and reposition on screen
- click: open or restore Ricky main window
- optional hover controls or context menu
- optional right-click/context menu:
  - Open Ricky
  - Start listening
  - Mute
  - Settings
  - Exit

## 10.5 Positioning behavior

Support future behaviors such as:

- always on top (optional)
- snap to screen edge
- remain where user placed it
- optionally auto-dim when inactive

## 10.6 Important UX rule

The floating companion orb must feel like a subtle desktop companion, not a big intrusive neon sticker.

So:
- preserve identity
- soften presentation
- keep transparency
- reduce visual aggression

---

# 11. Responsive Behavior

Define responsive rules.

## 11.1 Width priorities

At narrower widths:

### Under ~1366px
- supporting right-side cards become smaller or stack
- sidebar may reduce width
- whitespace is reduced carefully

### Under ~1024px
- sidebar can collapse
- recent activity / quick commands should become drawers, tabs or stacked panels
- main state content remains priority

### Confirmation modal
- must always stay clearly dominant
- never become a tiny card in a corner

## 11.2 Priority order

When space is tight, prioritize:

1. current state content
2. confirmation if active
3. voice controls
4. text input/editor
5. secondary panels
6. tertiary metadata

---

# 12. Localization / Language Awareness

The UI text should be localization-friendly.

Current approved UI examples are in Serbian Latin / BCS context.

Examples:
- Spreman
- Početna
- Aktivnost
- Planovi
- Memorija
- Snimci ekrana
- Postavke
- Zadnja aktivnost
- Brze komande
- Diktiranje
- Pošalji agentu
- Izmijeni
- Otkaži

Do not hardcode everything in a way that blocks future i18n support.

Canonical source for supported languages, the `interface_language` setting,
translation keys, and the `Postavke` (Settings) screen content is
[RICKY_GUI_LOCALIZATION_PLAN.md](./RICKY_GUI_LOCALIZATION_PLAN.md) — implement
against that, not against the short example list above.

---

# 13. Interaction Rules

## 13.1 Voice-first
The UI should clearly support voice-first usage.

## 13.2 Text fallback
The text input remains available as fallback.

## 13.3 Internal workflow
Draft review, dictation, confirmations and plan interaction all happen inside Ricky UI.

## 13.4 Do not overload
Even if multiple modules exist, do not show every possible panel fully expanded at once.

---

# 14. Implementation Notes for the Agent

When implementing, preserve the approved visual identity:

```txt
dark premium assistant UI
+ left sidebar
+ top bar
+ state-driven main area
+ glowing stylized R orb
+ Siri-like voice pulse ring
+ floating minimized companion orb
```

Do not replace the Ricky orb with:
- human face
- generic smiley
- plain microphone-only symbol
- flat generic app icon

The approved identity is:
- stylized `R`
- inside orb
- glowing voice ring
- same identity reused in large main view and minimized companion view

---

# 15. Deliverables

Implement or prepare the UI for these deliverables:

1. Main window — Idle / Ready screen
2. Main window — Dictation Mode screen
3. Main window — Confirmation Modal state
4. Activity drawer / panel
5. Plans drawer / panel
6. Ricky orb main component
7. Minimized floating Ricky companion orb component
8. Basic interaction states for orb animations
9. Stop / cancellation control wired to `POST /tools/executions/{id}/cancel` (see 3.4) — not just visual, must reflect real `tool_state`

---

# 16. Acceptance Criteria

The task is successful when:

- the main UI visually matches the approved dark Ricky design direction
- the stylized glowing R orb replaces the older simple avatar
- the orb looks premium and voice-assistant-like
- the orb reacts visually to state (idle/listening/speaking/etc.), mapped to the existing `VoiceState` type — no parallel state model
- the minimized floating orb preserves the same identity
- the minimized orb is more transparent and less intrusive
- confirmation appears as a dominant modal, backed by the real `ConfirmationService` fields (see 6.5)
- a visible Stop control is present and honest about outcome whenever a tool/voice turn is active (see 3.4) — this is a hard requirement, not implied by the mockup screenshot alone
- dictation mode puts the editor in focus
- activity and plans are available but not visually overwhelming, and both are restyles of the existing `/events` and `/plans*` backed components, not new data sources
- the layout remains professional and coherent

---

# 17. Final Summary for the Implementing Agent

Implement Ricky as a dark, premium, voice-first desktop assistant UI.

Use a state-based main layout with:

- Idle / Ready screen
- Dictation Mode
- Confirmation Modal
- Activity drawer
- Plans drawer

Use the approved Ricky avatar/orb as the core visual identity:

- stylized glowing `R`
- inside circular orb
- surrounded by a voice-reactive glowing ring
- inspired by premium assistant voice orb motion
- reused in the main UI and in minimized floating companion mode

The minimized Ricky companion must:
- keep the same identity
- be smaller
- be more transparent
- be less visually aggressive
- still clearly communicate Ricky state

Do not simplify the design into a generic recorder.
Do not use a human avatar.
Do not use Notepad or other external apps as substitute UI.
