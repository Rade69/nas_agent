# UI Redesign — Korak 2 (PI_NEXT_STEPS.md)

## Datum

2026-07-06

## Izvor

`docs/PI_NEXT_STEPS.md` Korak 2, koji upućuje na:
- `docs/RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md` (arhitektura/ponašanje)
- `docs/RICKY_FINAL_UI_IMPLEMENTATION_PROMPT.md` (vizuelni izgled)

## Scope

Restilizacija postojećih komponenti (FAZA 8 voice-first shell, FAZA 9 confirmations/plans, FAZA 12 Companion orb) u dark premium voice-first layout sa sidebar-om, state-driven content area, i novim RickyOrb identitetom. Nije greenfield — postojeći realtime voice pipeline (`src/lib/realtime.ts`), backend, svi API-jevi i IPC kanali su netaknuti.

## Izmijenjeni fajlovi

### Novi fajlovi

| Fajl | Opis |
|---|---|
| `src/components/RickyOrb.tsx` | Stilizovano "R" u premium orb-u sa glow ring-om; VoiceState-reaktivne animacije (idle/listening/thinking/speaking/waiting_confirmation/muted/error) |
| `src/components/Sidebar.tsx` | Navigacija: Početna, Aktivnost, Planovi, Memorija, Snimci ekrana, Postavke; backend status indikator u footer-u |

### Izmijenjeni fajlovi

| Fajl | Opis |
|---|---|
| `src/styles.css` | +~500 linija: CSS varijable za dark premium temu, novi layout (app-shell-redesign), sidebar, top bar, RickyOrb, idle/dictation screens, confirmation modal restyle, bottom voice bar |
| `src/App.tsx` | Potpuno prepisan: sidebar + state-driven main content (home/activity/plans/memory/screens/dictation tabovi), Idle/Ready screen sa orb-om i brzim komandama, Dictation Mode editor, Stop kontrola, Computer Mode pill u top baru |

## Šta je implementirano

### Layout
- **app-shell-redesign**: sidebar (220px) + main content (1fr) + top bar (48px) + bottom bar (52px)
- **Sidebar**: 6 navigacionih stavki, backend status dot
- **Top Bar**: VoiceState pill (animirani dot), Computer Mode toggle (crveni kad je ON), companion orb dugme, close
- **Bottom Voice Bar**: status text, text input, Stop dugme kad je aktivno

### Ricky Orb (zamjena za RickyFace)
- Stilizovano "R" slovo u premium dark orb-u
- Plavi glow ring sa VoiceState-reaktivnim animacijama:
  - `idle`: miran plavi ring
  - `listening`/`transcribing`: pulse animacija
  - `thinking`: ljubičasti slow glow
  - `speaking`: zeleni pulse
  - `waiting_confirmation`: narandžasti ring
  - `muted`/`interrupted`: sivi, prigušen
  - `error`: crveni shake

### State-driven screens
- **Idle/Ready**: veliki orb, "Ricky je spreman", CTA mikrofon dugme (→ Stop kad je aktivno), "Ukucaj..." fallback, kartice "Zadnja aktivnost" i "Brze komande"
- **Dictation Mode**: veliki textarea editor, badge "DICTATION MODE", akcije: Zatvori/Obriši/Pošalji agentu
- **Activity tab**: postojeći ActivityTimeline u perzistentnom tabu
- **Plans tab**: postojeći PlansPanel u perzistentnom tabu
- **Memory/Screens/Settings**: placeholder paneli

### Stop / Cancellation
- Klik na Stop prekida Realtime konekciju (`disconnect()`)
- Dugme vidljivo samo kad je `isActive` (listening/transcribing/thinking/speaking/waiting_confirmation)

### Click-to-talk (ne hold-to-talk)
- Primarni CTA je toggle dugme: klik za connect, klik za disconnect
- "Hold to talk" više nije default UX

### No-Notepad rule
- Dictation koristi interni textarea, ne otvara Notepad
- Sav sadržaj ostaje unutar Ricky UI-ja

## Očuvano iz postojećeg koda

- `src/lib/realtime.ts` — netaknut
- `ConfirmationDialog.tsx` — netaknut (samo restilizovan kroz CSS)
- `PlansPanel.tsx` — netaknut
- `ActivityTimeline.tsx` — netaknut
- `ArtifactPanel.tsx` — netaknut
- `BottomVoiceBar.tsx` — netaknut (stara verzija se više ne koristi u novom layout-u)
- `VoiceTopBar.tsx` — netaknut (stara verzija, zamijenjena inline top bar-om u App.tsx)
- `RickyFace.tsx` — netaknut (zamijenjen RickyOrb-om)
- `CompanionOrb.tsx` — netaknut (companion window i dalje koristi staru verziju, FAZA 12)
- Svi IPC kanali, Python backend, preload.cjs, main.cjs — netaknuti

## Verifikacija

```text
typecheck: prošao
build: prošao (CSS 40KB, JS ~348KB)
pytest: 180 passed (bez regresije)
node --check: svi Electron moduli clean
smoke: prošao
```

## Backlog / Future

Nije implementirano u ovoj iteraciji:
- GUI lokalizacija (i18n ključevi) — UI koristi hardcodirane sr-Latn stringove
- Model Settings panel (odvojen Voice/Text/Document/Local prikaz)
- Companion orb vizuelni redizajn (još koristi stari RickyFace dizajn u companion window-u)
- VoiceSessionState model (Ephemeral Command / Dictation / Confirmation Review modovi)
- Realtime Event Router backend bridge (throttling, prioriteti)
- Voice Draft panel za diktat (koristi jednostavan textarea)
- Responsive breakpoints (sidebar collapse na <1024px)