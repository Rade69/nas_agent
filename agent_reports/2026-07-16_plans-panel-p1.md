# Agent Report — Plans Panel P1 (koraci, progress, pause)

- Datum: 2026-07-16
- Agent: pi
- Faza: P1 — koraci plana (UI proširenje)

## Šta je urađeno

### 1. Progress indikator
- Brojač "3/7" u headeru svake plan kartice (completed + skipped / ukupno)
- CSS: `.plan-progress` — plavi pill, 11px font

### 2. Sljedeći korak (next step highlight)
- Prvi `pending` ili `in_progress` korak dobija `.plan-step-next` klasu
- CSS: plavi `border-left: 2px` + plava pozadina — vizuelno istaknut

### 3. Pause dugme
- Za `running` planove: dugme "Pauziraj" pored "Označi završenim"
- Pause vraća plan u `approved` status (backend nema `paused` status)
- CSS: `.plan-action.plan-pause` — žuti ton

### 4. Error detail za korake
- Ako `step.details.error` postoji, prikazuje se ispod koraka
- CSS: `.plan-step-error` — crveni tekst, grid span

## Fajlovi
- `src/components/PlansPanel.tsx` — progress, next step, pause, error
- `src/styles/11-pixel-shell.css` — plan-progress, plan-step-next, plan-step-error, plan-pause
- `src/i18n/locales/{5}.json` — "pause" ključ

## Provjere
- `tsc --noEmit` ✅
- `npm run build` ✅