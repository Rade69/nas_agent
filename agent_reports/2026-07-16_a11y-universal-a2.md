# Agent Report — A2 (potvrde koje se ne mogu propustiti)

- Datum: 2026-07-16
- Agent: pi
- Faza: A2 — focus management + Escape + objava u ConfirmationDialog i MiniComputerWindow

## Šta je urađeno

### ConfirmationDialog.tsx
- **Focus na kontejner** (NE na Odobri): `dialogRef` + `tabIndex={-1}` + `requestAnimationFrame(focus)` kad dijalog postane vidljiv. Enter na novootvorenom dijalogu NE radi ništa — odobrenje ostaje namjerno (sekcija 8).
- **Restore fokusa**: `previousFocusRef` čuva `document.activeElement` prije otvaranja; na zatvaranju `requestAnimationFrame(prev.focus())` vraća fokus.
- **Escape = Odbij/Otkaži** (sigurna, NE-destruktivna akcija — NIKAD odobri).
- **Focus trap**: Tab/Shift+Tab kruži unutar dijaloga — `resolveDialogKeyDown()` čista funkcija odlučuje o wrap-anju.
- **aria-labelledby/aria-describedby**: `confirmation-dialog-title` + `confirmation-dialog-desc` (action_name + risk) — screen reader čita ŠTA se potvrđuje kad fokus uđe.
- **`onKeyDown`** na kontejneru.

### MiniComputerWindow.tsx — confirmation kartica
- Isti obrazac: `cardRef` + `tabIndex={-1}` + `role="dialog"` + `aria-modal` + `aria-label`.
- **Escape → reject** (isti safe pristup).
- **Ne dirana** postojeća `armed` delay / single-use logika.

### resolveDialogKeyDown() — čista funkcija (testabilna)
Ekstraktovana odlučna logika (focus trap + Escape) u čistu funkciju — testabilna u node okruženju (bez jsdom dependency-ja). Vraća:
- `{ type: "escape" }` — Esc na pending+!busy
- `{ type: "wrap-focus", target: "first"|"last" }` — Tab wrap
- `{ type: "default" }` — ništa

## Šta NIJE dirano (security + email grana)
- `armed` 250ms delay (S-4/S-30) — netaknut
- Single-use potvrde (S-04) — netaknuto
- `isEmailDraftConfirmation` / `emailNeverSent` / `prepareDraft` — netaknuto
- `confirmation.approve` dugme `disabled={!armed}` — netaknuto
- Browser-tab rad — netaknut

## Testovi — 13 novih (ukupno 244)
`ConfirmationDialog.test.ts`:
- Escape → escape akcija (pending+!busy)
- Escape when busy → default
- Escape NIKAD ne vraća "approve" (security property, petlja kroz sve kombinacije)
- Tab na zadnjem → wrap na prvi
- Tab na srednjem → default (normalan Tab)
- Tab na prvom → default
- Shift+Tab na prvom → wrap na zadnji
- Shift+Tab na kontejneru (-1) → wrap na zadnji
- Shift+Tab na srednjem → default
- Tab sa 0 focusable → default
- Drugi tasteri (Enter, ArrowDown, slova) → default
- **Enter na kontejneru NIKAD ne odobrava** (security property)

## Provjere (sve obavezne iz brifa)
| Provjera | Rezultat |
|----------|---------|
| `npm run build` | ✅ built |
| `npx tsc --noEmit` | ✅ čist |
| `npx vitest run` | ✅ 244/244 (13 novih) |

## NVDA — zahtijeva ručno testiranje recenzenta
Pi ne može pokrenuti NVDA. Fokus/restore/Escape su standardni pattern-i, ali konačnu potvrdu da screen reader:
- pročita sadržaj pri otvaranju (aria-labelledby/describedby)
- čuje Escape = odbij
- ne izađe iz dijaloga na Tab
mora uraditi recenzent po smoke matrix (sekcija 7, tačke 4-8).

## Fajlovi
- Izmijenjeni: `src/components/ConfirmationDialog.tsx`, `src/components/pixel/MiniComputerWindow.tsx`
- Novi: `src/components/ConfirmationDialog.test.ts`

## Rizici
- Niski — additivno za focus/Escape, ne mijenja postojeću logiku
- `resolveDialogKeyDown` je čista funkcija — DOM wiring verifikovan typecheck-om, NE unit testom (nema jsdom)
