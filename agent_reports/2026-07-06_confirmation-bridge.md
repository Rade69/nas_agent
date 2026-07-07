# Confirmation Bridge — implementacija

## Datum

2026-07-06

## Izvor

`docs/RICKY_CONFIRMATION_BRIDGE_BRIEF.md` — bug-fix backlog item (nije numerisana FAZA, sve FAZA 0-19 su već gotove).

## Problem

`computer_type_text`, `computer_click`, `computer_click_element`, `computer_set_text_element` i `records_delete` zahtijevaju `confirmation_id`. Backend ispravno vraća `CONFIRMATION_REQUIRED`, ali **niko ne čita `result.errorCode`** na renderer strani. Model dobije sirovi error, nema tool da predloži potvrdu, `ConfirmationDialog` se nikad ne aktivira automatski. Svaki confirmation-required tool call sa voice-a je dead end.

## Šta je urađeno

### 1. Auto-propose confirmation (`src/lib/realtime.ts`)

U `executeFunctionCalls()`, nakon `window.ricky.executeTool()`:
- Ako `result.errorCode === "CONFIRMATION_REQUIRED"`:
  - Traži `risk` iz `this.toolSpecs` (tool name → risk lookup)
  - Poziva `window.ricky.createConfirmation({ action_name, payload, risk_level, tool_name })` — postojeći FAZA 9 IPC kanal
  - Postavlja `VoiceState` na `waiting_confirmation`
  - Vraća modelu `{ ok: false, waiting_confirmation: true, message: "I need your approval..." }` umjesto sirovog errora — model ne retry-uje u petlji

### 2. Auto-retry (`src/App.tsx`)

U `handleApproveConfirmation()`:
- Nakon uspješne aprobacije (`POST /confirmations/{id}/approve`):
  - Čita `approved.tool_name` i `approved.payload` iz odobrene potvrde
  - Poziva `window.ricky.executeTool({ name: tool_name, arguments: payload, context: { confirmation_id, computer_mode: true } })`
  - Silent UI update: Activity log entry + artifact (ako postoji), bez verbalne najave

### 3. `confirmation_id` forwarding (`electron/main.cjs`)

U `handleToolsExecute()`:
- Čita `toolCall.context.confirmation_id` ako postoji
- Prosljeđuje ga Python backend-u kroz `context: { computer_mode, confirmation_id }`

### 4. Tool risk metadata (`electron/main.cjs` + `src/vite-env.d.ts`)

- `RickyToolSpec` proširen sa opcionim `risk` poljem
- `Confirmation` tip proširen sa `tool_name` poljem
- `createConfirmation` signature proširen sa `tool_name`
- `toolSpecs` u main.cjs: dodat `risk` za computer_* / records_delete / screen_snapshot / ui_inspect
- `handleRealtimeCreateToken`: strip-uje `risk` prije slanja OpenAI-ju (`toolSpecs.map(({ risk: _omit, ...rest }) => rest)`)

## Izmijenjeni fajlovi

| Fajl | Izmjena |
|---|---|
| `src/lib/realtime.ts` | ~20 linija: auto-propose confirmation bridge |
| `src/App.tsx` | ~25 linija: auto-retry nakon odobrenja |
| `electron/main.cjs` | `risk` na 8 toolSpecs + strip prije OpenAI-ja + `confirmation_id` forwarding |
| `src/vite-env.d.ts` | `RickyToolSpec.risk`, `Confirmation.tool_name`, `createConfirmation.tool_name` |

## Verifikacija

```text
typecheck: prošao
build: prošao
pytest: 180 passed (bez regresije)
node --check: svi Electron moduli clean
smoke: prošao
```

## Acceptance criteria ispunjenost

- ✅ `CONFIRMATION_REQUIRED` ne vraća sirovi error modelu — vraća `waiting_confirmation: true` poruku
- ✅ `ConfirmationDialog` se automatski prikazuje (postojeći polling u `App.tsx` ga pick-uje)
- ✅ Klik na "Pokreni" re-izvršava originalni tool call sa `confirmation_id`
- ✅ `records_delete` radi kroz isti bridge (nije computer-use-specific)
- ✅ Backend (`permission_engine.py`, `tool_executor.py`, `tool_registry.py`) netaknut
- ✅ Nema novog `propose_confirmation` toola u `toolSpecs`
- ✅ Nema novog dialog komponenta — `ConfirmationDialog.tsx` reusano