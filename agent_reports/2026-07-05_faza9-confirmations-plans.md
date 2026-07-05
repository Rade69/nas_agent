# FAZA 9 — Confirmations + Plans/Proposals

## Datum

2026-07-05

## Scope

Implementirana je samo FAZA 9 iz `docs/MIGRATION_PLAN.md`: storage + REST + Electron IPC bridge + React UI za **confirmations** (odobrenje rizičnih akcija) i **plans/proposals** (pohrana koraka umjesto Notepad-a).

Nije implementirana FAZA 10 (permission/risk layer koji automatski *issue*-a confirmation_id iz tool execution-a). Confirmations se već mogu kreirati ručno (preko API-ja / UI-ja), ali ih još uvijok ne izdaje sam tool executor — to dolazi u FAZI 10. Nije diran audio pipeline (`src/lib/realtime.ts`). Nije diran legacy PowerShell computer-use.

## GitNexus impact

GitNexus MCP alati nisu bili dostupni u ovoj sesiji (samo `read/bash/edit/write` alati su izloženi), pa je urađena **ručna blast-radius analiza** po CLAUDE.md proceduri za taj slučaj.

Ručni blast radius:

- `create_app()` (`python_backend/app/main.py`) — jedini pozivaoc `app = create_app()` u istom fajlu. Dodata registracija novih servisa u `app.state` i `include_router` za confirmations/plans. Risk: **LOW**.
- `App()` (`src/App.tsx`) — jedini pozivaoc je `src/main.tsx`. Dodat state za pending confirmation i plans, plus render `ConfirmationDialog` i `PlansPanel`. Risk: **LOW**.
- Sve ostalo su **novi, izolovani moduli** (schemas, repositories, services, api routers, komponente). Risk: N/A (novi kod).
- `electron/main.cjs` — dodati novi IPC handler-i u `registerIpcHandlers` map-u (allowlist). Postojeći handler-i nisu mijenjani. Risk: **LOW**.
- `electron/preload.cjs` — dodatne allowlisted funkcije; postojeće nisu dirane. Risk: **LOW**.
- `python_backend/app/storage/db.py` — proširena `confirmations` šema (`plan_id`, `summary` kolone) + idempotentni migration helper `_ensure_column` za postojeće dev baze. Risk: **LOW**.
- `python_backend/app/core/config.py` — `get_settings()` sada poštuje `RICKY_DATA_DIR` env varijablu (potrebno za izolovane testove). Risk: **LOW**.
- `python_backend/app/storage/repositories/tool_run_repo.py` — `utc_now_iso` premješten u `storage/db.py` kao dijeljeni utility (koriste ga confirmation_repo i plan_repo). Ponašanje nepromijenjeno. Risk: **LOW**.

## Šta je urađeno

### Backend (Python)

- Nove Pydantic schema-e:
  - `python_backend/app/schemas/confirmation.py` — `ConfirmationCreateRequest`, `ConfirmationResponse`, `ConfirmationListResponse`, `ConfirmationDecisionResponse`
  - `python_backend/app/schemas/plan.py` — `PlanCreateRequest`, `PlanUpdateRequest`, `PlanStepUpdateRequest`, `PlanResponse`, `PlanListResponse`, `PlanStepResponse`
- Novi storage repositories:
  - `python_backend/app/storage/repositories/confirmation_repo.py` — `ConfirmationRepository` (create, get, list, resolve, list_pending)
  - `python_backend/app/storage/repositories/plan_repo.py` — `PlanRepository` (create sa steps, get, list, update, update_step)
- Novi service sloj:
  - `python_backend/app/services/confirmation_service.py` — `ConfirmationService` (propose, approve, reject, cancel; ID format `confirm_<hex12>`)
  - `python_backend/app/services/plan_service.py` — `PlanService` (create, get, list, update, update_step; ID format `plan_<hex12>`)
- Novi REST endpointi:
  - `python_backend/app/api/confirmations.py`
    - `POST /confirmations` — kreira pending confirmation (može referencirati `plan_id`)
    - `GET /confirmations` — lista (filter `status`, `limit`)
    - `GET /confirmations/pending` — samo pending
    - `POST /confirmations/{id}/approve`
    - `POST /confirmations/{id}/reject`
    - `DELETE /confirmations/{id}` — cancel
  - `python_backend/app/api/plans.py`
    - `GET /plans` — lista planova sa koracima
    - `POST /plans` — kreira plan sa ordered steps
    - `GET /plans/{id}` — detalji sa steps
    - `PATCH /plans/{id}` — update title/summary/status
    - `PATCH /plans/{id}/steps/{step_id}` — update step status/title/details
- `main.py` `create_app()` sada konstruiše `ConfirmationService` i `PlanService` nad novim repositorijima i registruje novu dva routera u `app.state` i `include_router`.
- `storage/db.py`:
  - `confirmations` šema proširena sa `plan_id TEXT, summary TEXT` kolonama
  - dodat idempotentni migration helper `_ensure_column` (pošto se koristi `CREATE TABLE IF NOT EXISTS`, nove kolone se ne bi pojavile na postojećoj dev bazi bez ove mjere)
  - `utc_now_iso()` premješten ovamo kao dijeljeni utility
- `core/config.py`: `get_settings()` čita `RICKY_DATA_DIR` env varijablu (omogućava izolovane testove u `tmp_path`).
- Novi testovi:
  - `tests/test_confirmations.py` (8 testova)
  - `tests/test_plans.py` (7 testova)

### Electron bridge

- `electron/services/pythonClient.cjs` — dodate funkcije: `listConfirmations`, `listPendingConfirmations`, `createConfirmation`, `approveConfirmation`, `rejectConfirmation`, `cancelConfirmation`, `listPlans`, `createPlan`, `getPlan`, `updatePlan`, `updatePlanStep`. Izvezen i `requestJson` (za query-param podršku).
- `electron/preload.cjs` — expose novih allowlisted funkcija na `window.ricky` (svaka mapira na tačno jedan imenovani IPC kanal — nema generic pass-through).
- `electron/main.cjs` — dodati tanki pass-through IPC handler-i (`handleConfirmationsList`, `handleConfirmationsPending`, `handleConfirmationCreate`, `handleConfirmationApprove`, `handleConfirmationReject`, `handleConfirmationCancel`, `handlePlansList`, `handlePlanCreate`, `handlePlanGet`, `handlePlanUpdate`, `handlePlanStepUpdate`) i registracija u `registerIpcHandlers` allowlist map-i. Nikakva business logika nije dodata u `main.cjs` (poštovano arhitektonsko pravilo).
- IPC kanali (naming konvencija po arhitekturi — dvotačka za Electron IPC): `confirmations:list`, `confirmations:pending`, `confirmations:create`, `confirmations:approve`, `confirmations:reject`, `confirmations:cancel`, `plans:list`, `plans:create`, `plans:get`, `plans:update`, `plans:update-step`.

### React UI

- Nove komponente:
  - `src/components/ConfirmationDialog.tsx` — modalni dialog koji prikazuje pending confirmation (action_name, summary, risk_level pill, plan_id, payload preview) sa dugmadima **Otkaži** / **Pokreni**. Binduje se na isti `confirmation_id` koji će se koristiti i za voice potvrdu ("da"/"pokreni" vs "ne"/"otkaži").
  - `src/components/PlansPanel.tsx` — panel koji lista planove sa koracima, statusima, i akcijama (Approve plan / Start / Mark completed / Reject) te advance-step dugme.
- `src/vite-env.d.ts` — dodati tipovi `Confirmation`, `Plan`, `PlanStep`, `ConfirmationStatus`, `PlanStatus`, `PlanStepStatus`, `RiskLevel` i proširen `window.ricky` interfejs sa svim novim funkcijama.
- `src/App.tsx`:
  - dodat state: `pendingConfirmation`, `confirmationBusy`, `plans`, `showPlans`, `busyPlanId`, `busyStepId`
  - `useEffect` koji poll-uje `/confirmations/pending` svakih 2.5s i automatski prikazuje novu pending confirmation
  - `useEffect` koji setuje `VoiceState` na `waiting_confirmation` dok je pending confirmation vidljiv
  - `useEffect` koji fetch-uje plans na mount
  - handler-i: `handleApproveConfirmation`, `handleRejectConfirmation`, `handleCancelConfirmation`, `handleUpdatePlanStatus`, `handleUpdateStepStatus`
  - render `ConfirmationDialog` i `PlansPanel` + toggle dugme za plans panel
- `src/styles.css` — dodat CSS blok za `.confirmation-overlay`, `.confirmation-dialog`, `.plans-panel`, `.plan-card`, `.plan-step`, risk pill-ove (low/medium/high/critical), plan status pill-ove.

## Zašto je urađeno

Voice-first arhitektura zahtijeva da rizične akcije imaju **confirmation_id** model (komanda "da" ne smije ništa uraditi bez aktivne potvrde — vidi `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md` "Voice confirmations") i da planovi budu **SQLite zapisi** umjesto Notepad fajlova. Ova faza postavlja storage + state-machine + UI sloj za oba, tako da FAZA 10 (permission/risk layer) već ima spreman kanal za izdavanje confirmation_id-ja iz tool execution-a.

## Kako je urađeno

- **Confirmation lifecycle**: `pending → approved | rejected | cancelled | expired`. Transition je idempotentan — ponovljen approve već odobrene confirmation vraća isti record. `resolve()` koristi `WHERE id = ? AND status = 'pending'` da izbjegne race.
- **Plan lifecycle**: statusi `draft | proposed | approved | running | completed | rejected | cancelled`. Koraci se kreiraju atomično sa planom (jedna transakcija), sa auto-generisanim `step_id` u formatu `<plan_id>-step-<index+1>`.
- **Plan ↔ Confirmation link**: confirmation može referencirati `plan_id` (kolona u `confirmations` tabeli) — omogućava "approve this plan before running step 3" tok iz arhitekture.
- **UI ↔ VoiceState veza**: kad god je `pendingConfirmation.status === "pending"`, `App` setuje `VoiceState` na `waiting_confirmation` (već postoji u `voiceState.ts` iz FAZE 8). Ovo je additive UI-side effect — `realtime.ts` audio pipeline nije diran.

## Šta nije dirano

- Nije diran `src/lib/realtime.ts` (WebRTC/OpenAI Realtime audio pipeline).
- Nije diran tool executor / tool registry (`python_backend/app/agent/`) — automatsko izdavanje confirmation_id-ja iz tool execution-a dolazi u FAZI 10.
- Nije diran legacy PowerShell computer-use (`electron/tools_legacy/powershell/`).
- Nije diran permission/risk layer (FAZA 10), allowlist aplikacija, risk model za tool execution.
- Nije implementiran backend push (activity_events webhook) — UI koristi 2.5s polling za pending confirmations; push dolazi kasnije.
- Nije implementirana voice-komanda binding ("da"/"ne") na confirmation_id — to zahtijeva integraciju sa Realtime function-calling tokom i stiže nakon FAZE 10 (permission layer koji issue-uje confirmation_id).

## Verifikacija

Pokrenuto:

```text
cd python_backend && python -m pytest -q
npm run typecheck
npm run build
node smoke (startPythonBackend + REST endpoints round-trip)
```

Rezultati:

```text
pytest: 26 passed, 1 warning (FastAPI/Starlette TestClient deprecation)
typecheck: prošao (tsc --noEmit bez grešaka)
build: prošao (vite/rolldown build)
node smoke: backend startovao, plan create (201), step update (completed),
            confirmation create sa plan_id, approve, pending-after=0, plans list (1)
            — sve rute potvrđene
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation (nevezan za FAZU 9).

## Rizici/ograničenja

- **Polling umjesto push-a**: UI poll-uje `/confirmations/pending` svakih 2.5s. Za produktivno korištenje je to prihvatljivo, ali pravi push kanal (preko activity_events ili WebSocket) dolazi kasnije — vidi follow-up.
- **Bez automatskog izdavanja confirmation_id-ja**: dok FAZA 10 ne doda permission/risk layer u `ToolExecutor`, confirmations se moraju kreirati ručno (preko API-ja ili UI-ja). UI poll će ih pokupiti kad god se pojave — što znači da kad FAZA 10 bude issue-ovala confirmation iz tool execution-a, dijalog će se automatski pojaviti.
- **Computer mode (mini companion)**: `ConfirmationDialog` se ne renderuje u mini `mode === "computer"` view-u (rani return). Ako se pending confirmation pojavi dok je korisnik u computer mode, neće je vidjeti dok se ne vrati u full view. Acceptable za MVP — computer mode je trenutno fokusiran na samu interakciju.
- **Migration helper je minimalan**: `_ensure_column` koristi `ALTER TABLE ADD COLUMN` bez default vrijednosti za NULL kolone. Za SQLite je to sigurno za `plan_id` i `summary` (oba nullable). Ako se u budućnosti doda NOT NULL kolona sa default, treba proširiti migration pristup (pun migration framework je van MVP scope-a).
- **SQLite šema proširena**: postojeće dev baze zadržavaju stare kolone; nove `plan_id`/`summary` kolone se dodaju idempotentno pri `initialize_database()`.

## Potreban follow-up

- **FAZA 10** (permission/risk/confirmation layer) je sljedeća: `ToolExecutor.execute()` treba provjeriti `tool.definition.requires_confirmation` i, ako je `true`, izdati `confirmation_id` (kreirati pending confirmation) i vratiti `PERMISSION_DENIED` sa `confirmation_id` u `details` dok korisnik ne approve-uje. UI poll već pokriva pojavljivanje dijaloga.
- **Voice binding**: nakon FAZE 10, Realtime function-call handler treba proslijediti `confirmed: true` sa `confirmation_id` kada korisnik kaže "da"/"pokreni", a model traži confirmation. Trenutno `requiresConfirmation()` u `electron/main.cjs` je legacy stub koji se ne veže na backend confirmation_id.
- **Backend push**: zamijeniti 2.5s polling WebSocket / activity_events push kanalom kad se uvede.
- **Document Engine epic** (Backlog) može kasnije koristiti `confirmations` sa `plan_id` za approval gate-ove nad dokumentima.

## Potrebna korisnička potvrda

Prije commita treba potvrditi:

1. Da li želite da ručno testiram UI u Electron prozoru (pokretanjem `npm run dev`) ili je `npm run build` + node smoke test dovoljno za ovu fazu?
2. Da li je prihvatljivo da computer mode (mini companion) ne prikazuje `ConfirmationDialog` (vidi ograničenje iznad), ili treba dodati i overlay u mini view?
3. Worktree već sadrži postojeće izmjene iz prethodnih faza (`AGENTS.md`, `CLAUDE.md` dirty, neprateni `assets/Ricky-agent-3.png` i `docs/RICKY_GUI_LOCALIZATION_PLAN.md`) — treba li FAZA 9 commitovati odvojeno ili zajedno sa tim izmjenama?
