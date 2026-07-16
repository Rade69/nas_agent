# Agent Report — Plans Panel P0 (stabilizacija)

- Datum: 2026-07-16
- Agent: pi
- Faza: P0 — stabilizacija postojećeg panela

## Šta je urađeno

### 1. Loading i error stanja
- `plansLoading` / `plansError` state u App.tsx
- PlansPanel prikazuje spinner (`Loader2`) dok traje fetch
- PlansPanel prikazuje error poruku ako backend ne odgovori
- Props proslijeđeni kroz PixelMockupBoard

### 2. Inline forma za imenovanje plana
- "Novi plan" više ne kreira sa hardkodiranim naslovom "Novi plan"
- Klikom na dugme otvara se inline input + "Kreiraj" / "Otkaži"
- Enter potvrđuje, Escape otkazuje
- `onCreatePlan(title)` prima naslov kao parametar
- Auto-fokus na input polje

### 3. Bolja prazna stanja po tabu
- Aktivni: "Nema aktivnih planova. Aktivni planovi su zadaci koje si prihvatio i koji su u toku."
- Predloženi: "Nema predloženih planova. Agent će predložiti plan za zadatke sa više koraka."
- Završeni: "Nema završenih planova. Završeni, otkazani i odbijeni planovi se prikazuju ovdje."

### 4. Refresh nakon izmjena
- `handleUpdatePlanStatus` i `handleUpdateStepStatus` već ažuriraju lokalno stanje
- `refreshPlans` se poziva pri otvaranju drawer-a (postojeće ponašanje, potvrđeno)

## Fajlovi

### Izmijenjeni
- `src/components/PlansPanel.tsx` — loading/error, inline forma, per-tab empty states
- `src/components/pixel/PixelMockupBoard.tsx` — plansLoading/plansError props
- `src/App.tsx` — plansLoading/plansError state, handleCreatePlan(title)
- `src/i18n/locales/{sr-Latn,en,de,es,fr}.json` — 8 novih ključeva po locale-u

## Provjere
- `npx tsc --noEmit` ✅
- `npm run build` ✅
- `npx vitest` ✅ 244/244
- Ne dira browser bridge fajlove (Claude-ov rad)
