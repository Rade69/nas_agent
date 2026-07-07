# RICKY GUI IMPLEMENTATION PROMPT — PIXEL-CLOSE REBUILD OF THE APPROVED MOCKUP

## Goal

Rebuild the Ricky GUI so that it matches the **approved mockup as closely as possible**.

This is **not** a loose redesign.
This is **not** a cosmetic refresh of the old screen.
This is **not** a "best effort" reinterpretation.

The objective is:

```txt
Create a GUI that is maximally visually and structurally identical
to the approved Ricky mockup,
using the prepared branding assets from assets/brending.
```

---

# 1. Critical instruction

## Treat this as a layout rebuild, not a theme update

The current/starter UI must **not** simply be recolored or slightly adjusted.

The agent must understand:

```txt
The old home screen layout is not the target.
The old plain R avatar is not the target.
The old artifacts/debug-style layout is not the target.
The target is the approved Ricky mockup.
```

If the current implementation still looks like:

```txt
old sidebar
+ plain R avatar
+ empty center
+ old chat bar
+ debug activity panel
+ old artifact block
```

then the task is **not finished**.

---

# 2. Source of truth

The source of truth for the implementation is:

1. the approved **dark Ricky mockup**
2. the approved **Ricky orb branding assets**
3. the approved **state-driven structure**
4. the prepared icons/assets inside:

```txt
C:\Users\38765\Desktop\Nas-agent\assets\brending
```

The agent must use those assets directly wherever applicable.

---

# 3. Branding / assets usage

## 3.1 Mandatory asset usage

Use the prepared assets from:

```txt
C:\Users\38765\Desktop\Nas-agent\assets\brending
```

Important files:

```txt
logo/ricky-logo-r.svg
logo/ricky-app-icon.png
logo/ricky-app-icon.ico

orb/ricky-orb-main.png
orb/ricky-orb-mini.png
orb/ricky-orb-idle.png
orb/ricky-orb-listening.png
orb/ricky-orb-speaking.png
orb/ricky-orb-thinking.png
orb/ricky-orb-warning.png
orb/ricky-orb-error.png
```

## 3.2 Orb usage rules

```txt
Main idle screen avatar           -> orb/ricky-orb-main.png
Minimized floating companion      -> orb/ricky-orb-mini.png
Header small icon                 -> logo/ricky-logo-r.svg or a small orb variant
State-specific view if needed     -> corresponding orb state image
```

## 3.3 Do not improvise new branding

Do not replace approved assets with:
- emoji
- random icon pack symbols
- generic microphone logo
- new custom avatar
- human avatar
- plain circle with simple text R

The approved Ricky identity is:

```txt
stylized glowing R
inside circular orb
with premium blue/cyan/violet voice ring look
```

---

# 4. Product direction

Ricky is a **premium dark desktop voice assistant UI**.

The application should feel:

- professional
- polished
- modern
- clean
- slightly futuristic
- voice-first
- visually branded
- safe and controlled

The UI must not feel like:
- a debug tool
- a random admin dashboard
- a generic chat app
- a placeholder prototype
- an Electron starter template

---

# 5. Screen model

The GUI must be implemented as a **state-based interface**.

Main states:

1. `Idle / Ready`
2. `Dictation Mode`
3. `Confirmation Mode`

Supporting areas:
- `Activity`
- `Plans`
- `Memory`
- `Screens`
- `Settings`

These are part of the UI system, but they must not overpower the primary state content.

---

# 6. Exact layout intent

## 6.1 Overall shell

The main desktop window must visually contain:

```txt
- top bar
- left sidebar
- central main content area
- right-side supporting cards on the idle view
- bottom voice/text input area
```

This must look close to the approved mockup:
- not too dense
- not too sparse
- balanced
- premium
- aligned
- controlled

---

# 7. Top bar specification

## 7.1 Layout zones

### Left section
Must contain:
- small Ricky icon/orb/logo
- `Ricky`
- current state text (example: `Spreman`)

Example visual meaning:

```txt
[Ricky icon] Ricky   Spreman
```

### Middle / right-middle
Must contain:
- `Computer mode` pill / badge
- example:
  - `Computer mode: ISKLJUČEN`
  - `Computer mode: UKLJUČEN`

### Right section
Must contain:
- utility controls/icons if needed
- window controls:
  - minimize
  - maximize / restore
  - close

## 7.2 Visual rules

- top bar must be thin and elegant
- spacing must be generous
- no clutter
- text must be readable
- status must not be duplicated everywhere else

## 7.3 One status source rule

If top bar says `Spreman` or `Diktiranje`, the same exact status should **not** also be repeated loudly in multiple different places unless there is a good reason.

---

# 8. Sidebar specification

## 8.1 Sidebar items

The left sidebar must contain these primary sections:

```txt
Početna
Aktivnost
Planovi
Memorija
Snimci ekrana
Postavke
```

Each should use the prepared icons from `assets/brending/icons/navigation`.

## 8.2 Visual style

- slim but not tiny
- dark background slightly different from main canvas
- active item clearly highlighted
- hover states must be visible
- sidebar must feel integrated, not boxed awkwardly

## 8.3 Do not keep old clutter

If there is an old artifact/debug block in the sidebar or left column, remove it from the main layout.

### Explicitly remove from primary layout:
- old artifacts preview block
- raw file path panel
- debug-style backend log panel
- placeholder blocks from old screen

---

# 9. Idle / Ready screen — exact intent

This is the most important state and must match the mockup closely.

## 9.1 Visual hierarchy

The center must clearly focus on:

1. Ricky orb
2. "Ricky je spreman" style heading
3. supporting line
4. main voice CTA
5. text fallback input

The right side must show **supporting cards**, not dominant competing content.

## 9.2 Required main center content

### Center zone
Must include:
- large Ricky orb (`ricky-orb-main.png`)
- title:
  - `Ricky je spreman`
- subtitle:
  - something like `Klikni mikrofon ili reci "Ricky"`
- main voice action button
- text input field below

### Bottom text/voice input
Must feel voice-first.

That means:
- microphone or voice CTA is primary
- typing is secondary fallback

Do not make it look like a standard chat app input first.

## 9.3 Right supporting cards

The approved idle view should include supporting cards on the right, such as:

### Card 1 — Recent activity / Zadnja aktivnost
Examples:
- Email poslan šefu
- Nacrt izvještaja spreman
- Otvoren dictation mode
- Screenshot snimljen

### Card 2 — Quick commands / Brze komande
Examples:
- Napiši email šefu
- Napravi screenshot
- Otvori Notepad
- Planiraj sastanak sutra u 10h

## 9.4 What must NOT appear on idle screen

Do **not** show:
- raw backend log spam as user activity
- repeated “Backend ready” entries as primary UX content
- oversized debug widgets
- old artifact preview block
- big empty unused dark area
- ugly global scrollbars caused by bad layout overflow

---

# 10. Ricky orb implementation rules

The orb is a central identity element, not a small decorative item.

## 10.1 Main orb
Use:
```txt
orb/ricky-orb-main.png
```

It must be:
- centered
- clearly visible
- the visual anchor of the idle state

## 10.2 Behavior
If motion/state switching is implemented, use the proper variants:

```txt
idle        -> ricky-orb-idle.png
listening   -> ricky-orb-listening.png
speaking    -> ricky-orb-speaking.png
thinking    -> ricky-orb-thinking.png
warning     -> ricky-orb-warning.png
error       -> ricky-orb-error.png
```

## 10.3 Absolutely avoid
Do not render:
- plain text “R” inside a flat dark circle
- generic placeholder avatar
- human face
- extra random glow effects unrelated to approved branding

---

# 11. Bottom input area

## 11.1 Intent

The lower interaction bar should support:
- voice interaction
- text fallback
- send/confirm interaction

It must look like part of the approved Ricky design, not like a generic chat footer.

## 11.2 Requirements

- comfortable height
- clear rounded container
- refined spacing
- voice CTA present
- text input present
- send action present
- subtle but polished design

## 11.3 Voice-first rule

The visual priority should be:

```txt
voice first
text second
```

That means the input area should visually communicate:
- speak first
- type if needed

---

# 12. Dictation Mode specification

The dictation screen must be a **real separate state**, not just a tiny transcript box added to the idle screen.

## 12.1 Purpose
When user dictates longer content, the UI should shift into a focused editor state.

## 12.2 Required structure

Must include:
- visible `DICTATION MODE` / `Diktiranje` badge or label
- auto-save / status line if needed
- large editable text area
- clean action row

### Primary action
- `Pošalji agentu`

### Secondary actions
- `Nastavi diktiranje`
- `Doradi`
- `...`

Doradi can group:
- Formalizuj
- Skrati
- Provjeri pravopis
- Prevedi

## 12.3 Rules

- editor must dominate the screen
- unrelated side clutter must be reduced
- do not show old idle screen layout unchanged
- do not keep oversized side cards if they break focus

---

# 13. Confirmation Mode specification

This is a critical security UX feature.

## 13.1 Mandatory rule
Confirmation must be a **dominant modal**, not a small footer banner or weak secondary block.

## 13.2 Behavior
When Ricky wants to execute a risky or external action:
- dim background
- show modal centered
- make it visually unavoidable

## 13.3 Required modal content
Include fields such as:
- Akcija
- Prima / Cilj
- Predmet
- Rizik
- Ističe za

Buttons:
- `Izmijeni`
- `Otkaži`
- primary confirm button such as:
  - `Pošalji email`
  - `Dozvoli jednom`

## 13.4 Visual importance
This modal must clearly overpower background content.

If the modal can be visually ignored, the implementation is wrong.

---

# 14. Activity screen/panel rules

## 14.1 Activity content must be user-meaningful

Do not display raw debug/system logs as the main user-facing activity history.

### Bad:
- Backend ready
- Health OK
- Event poll success
- Repeated technical system pings

### Good:
- Email poslan šefu
- Nacrt izvještaja spreman
- Screenshot snimljen
- Diktiranje završeno
- Plan kreiran

## 14.2 Presentation
Activity can be:
- a dedicated screen
- a drawer
- or a panel

But it must look polished and readable.

---

# 15. Plans screen/panel rules

Plans should be available as a dedicated section or drawer.

Suggested subdivisions:
- Aktivni
- Predloženi
- Završeni

It should look aligned with the Ricky visual system.

---

# 16. Settings rules

The settings section exists but must not dominate the idle screen by default.

It may include:
- language
- appearance
- privacy/security
- voice/audio
- models (future)

If a settings preview is visible on the main screen, it must be subtle. Prefer full settings section over permanently open right settings pane unless the approved layout explicitly needs it.

---

# 17. Color system

## 17.1 Semantic colors

Use strict color semantics:

- **blue / cyan** = primary, active, brand
- **green** = success
- **yellow / orange** = warning / confirmation / risk
- **red** = error / blocked / dangerous
- **gray** = neutral / secondary

## 17.2 Important warning
Do not use warning color for ordinary success or ordinary activity events.

If orange means “warning / confirmation”, keep it reserved for that purpose.

---

# 18. Typography / spacing / polish rules

## 18.1 Typography
The UI must use a clean modern system-like font stack or the project font stack, with:
- good readability
- medium weight headings
- subtle secondary text
- clear hierarchy

## 18.2 Spacing
The implementation must not feel cramped or randomly spaced.

Use consistent spacing system.
Example guideline:
- 8 px minor
- 12 px small
- 16 px normal
- 20/24 px section spacing
- 32 px larger content gaps

## 18.3 Borders / surfaces
Use:
- soft rounded corners
- subtle borders
- layered dark surfaces
- gentle shadows/glows
- no harsh mismatched boxes

---

# 19. Responsiveness / resizing

## 19.1 Priority rules
If the window narrows:
1. preserve central content
2. preserve orb + main CTA
3. preserve input bar
4. collapse secondary cards if needed
5. collapse sidebar if needed

## 19.2 Do not break layout
The UI must not:
- overflow ugly scrollbars everywhere
- leave huge dead empty areas
- overlap cards badly
- distort the orb
- break top bar alignment

---

# 20. Minimized / floating Ricky companion

Implement the minimized companion using:

```txt
orb/ricky-orb-mini.png
```

## Rules
- smaller than main orb
- more transparent / less intrusive
- visually consistent with main identity
- can act as floating companion

But this must **not** replace the main GUI orb.
It is an additional mode/component.

---

# 21. Explicit “do not” list

The implementing agent must NOT do the following:

```txt
1. Do not just recolor the old layout.
2. Do not keep the old artifacts panel in the primary screen.
3. Do not keep the plain old R avatar.
4. Do not show backend debug logs as primary user activity.
5. Do not turn the app into a generic chat UI.
6. Do not replace branding with generic icons.
7. Do not ignore the prepared assets folder.
8. Do not leave the center visually empty.
9. Do not place confirmation as a weak small card/banner.
10. Do not create a layout that is only “inspired by” the mockup.
```

---

# 22. Explicit “must do” list

The implementing agent MUST do the following:

```txt
1. Rebuild the home/idle screen structure.
2. Use the prepared Ricky orb assets.
3. Use the prepared icons from assets/brending.
4. Make the center focus match the mockup hierarchy.
5. Add right-side supporting cards on idle view.
6. Keep voice-first interaction visually primary.
7. Make dictation a true state.
8. Make confirmation a dominant modal.
9. Clean out old debug/artifact clutter from primary screen.
10. Deliver a screen that looks intentionally close to the approved mockup.
```

---

# 23. Acceptance criteria

The implementation is accepted only if it satisfies the following:

## 23.1 Idle state acceptance
- looks visually close to the approved mockup
- has large branded Ricky orb in center
- has proper heading/subheading
- has voice-first CTA
- has clean text fallback input
- has polished right-side support cards
- does not show old artifact/debug clutter

## 23.2 Branding acceptance
- uses prepared Ricky orb assets
- does not use the old plain R circle
- header icon is updated
- overall branding feels consistent

## 23.3 Structure acceptance
- not just a recolored old layout
- state-based structure exists
- dictation mode exists
- confirmation modal exists
- sidebar/navigation is clean and intentional

## 23.4 Polish acceptance
- spacing is consistent
- typography is refined
- surfaces look premium
- no awkward overflow
- no ugly empty center
- no debug look

---

# 24. Final instruction to the agent

Implement the Ricky GUI as a **pixel-close reconstruction of the approved mockup**, not as an interpretation.

Think in these terms:

```txt
Use the mockup as the target.
Use assets/brending as the visual source.
Refactor the structure.
Remove the old clutter.
Rebuild the hierarchy.
Match the orb identity exactly.
Make the UI feel premium and intentional.
```

If after implementation the result still looks like “the previous app with some styling changes”, the task has failed.

The final result should clearly look like:

```txt
the approved Ricky mockup has been translated into the real app
```

not like:

```txt
a partial adaptation of the old screen
```
