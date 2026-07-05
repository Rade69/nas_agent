# FAZA 11 — Tool registry + bezbjedni lokalni toolovi

## Datum

2026-07-05

## Scope

Implementirana je FAZA 11 iz `docs/MIGRATION_PLAN.md`: migracija low-risk memory/artifact toolova (notes, records, artifacts) i system toolova (screen_snapshot, ui_inspect) iz Electron/PowerShell/JSON-db u Python backend, plus backend→UI event bridge (`/events`) za artifact updates i tool progress.

Nisu implementirane FAZA 12 (companion orb) ni FAZA 13/14 (computer-use v1/v2 — i dalje BLOCKED iza Security Gate 0). Legacy PowerShell computer-use toolovi ostaju na mjestu.

## GitNexus impact

Prije izmjene pokrenut je `npx gitnexus impact` (CLI, `--repo nas_agent`) na ključnim simbolima:

- `create_app` → risk **LOW**, 1 impaktovani (samo `main.py`).
- `create_default_registry` → risk **LOW**, 2 impaktovana, 1 modul.
- `handleToolsExecute` → risk **LOW**, 0 impaktovanih, 0 procesa.

Sve izmjene su aditivne (novi moduli + proširenje wire-ovanja u `main.py`/`tool_registry.py`), bez promjene ponašanja postojećih funkcija. Nakon izmjene indeks je osvježen (`npx gitnexus analyze`).

Napomena: ova faza je rađena preko FAZA 10 commit-a (`98076f6` / `87e1118`) koji je napravio paralelni agent (Claude) — permission/risk engine, cancellation registry, payload_hash binding. Moj rad je pomno integrisan preko tog stanja bez pregazivanja FAZA 10 modula.

## Šta je urađeno

### Storage (Python)

- `app/storage/repositories/notes_repo.py` — `NotesRepository` (create, list, search)
- `app/storage/repositories/records_repo.py` — `RecordsRepository` (create, list_in_collection, search, get, update sa field-merge, delete)
- `app/storage/repositories/artifact_repo.py` — `ArtifactRepository` (create, get, list sa type filter) — CRUD sloj nad `artifacts` tabelom iz FAZE 7
- `app/storage/repositories/event_repo.py` — `EventRepository` (emit, list_recent, list_since sa timestamp cursor) — koristi postojeću `activity_events` tabelu
- `app/storage/db.py` — dodate `notes` i `records` tabele u `SCHEMA_STATEMENTS` (čuvajući FAZA 10 MIGRATIONS: `confirmations.tool_name`/`payload_hash`/`expires_at`)

### Services

- `app/services/notes_service.py` — `NotesService` (ID format `note_<hex12>`)
- `app/services/records_service.py` — `RecordsService` (ID format `rec_<hex12>`)
- `app/services/artifact_service.py` — `ArtifactService` (emituje `artifact.created` event preko EventBus-a pri kreiranju; ID format `art_<hex12>`)
- `app/services/event_bus.py` — `EventBus` (emit, recent, since — backend→UI event bridge)

### Tool handlers (`app/tools/`)

- `app/tools/memory/notes.py` — `note_add`, `note_search`, `note_list`
- `app/tools/memory/records.py` — `records_create`, `records_search`, `records_update`, `records_delete` (handler-level `confirmed:true` guard + FAZA 10 permission engine binding preko `confirmation_id`)
- `app/tools/artifacts.py` — `artifact_create`, `artifact_get`, `artifact_list`, `artifact_show`
- `app/tools/system/screenshot.py` — `screen_snapshot` (Pillow `ImageGrab`, multi-monitor kompozit; bez `mss` dependency-ja)
- `app/tools/system/ui_inspect.py` — `ui_inspect` (stdlib `ctypes` za Win32 foreground window + `psutil` za process name; bez `pywinauto`)

### Tool registration

- `app/agent/tool_registry.py` — `_register_phase11_tools()` registruje svih 13 toolova sa `ToolDefinition` po `TOOL_CONTRACTS.md` formatu (`risk`, `requires_confirmation`, `requires_computer_mode`, itd.). `create_default_registry(services=...)` sada prima opcioni services dict.
  - `note_*`, `records_create`/`records_search`/`records_update`, `artifact_*` → risk=low, bez confirmation
  - `records_delete` → risk=critical, `requires_confirmation=True`
  - `screen_snapshot`, `ui_inspect` → risk=low, `requires_computer_mode=True`

### Wire-ovanje

- `app/main.py` — instancira `EventBus`, `NotesService`, `RecordsService`, `ArtifactService` (sa event_bus injection); zove `create_default_registry(services=phase11_services)`; emituje `backend.ready` event; uključuje `events_router`.
- `app/api/events.py` — `GET /events?since=<timestamp>` (cursor-based polling, vraća `events` + `next_cursor`).

### Electron bridge (delegacija sa fallback)

- `electron/services/pythonClient.cjs` — dodata `listEvents(since)` funkcija; `executeTool` već postoji iz FAZE 9.
- `electron/preload.cjs` — expose `listEvents` na `window.ricky`.
- `electron/main.cjs`:
  - `handleToolsExecute` sada rani-delegira FAZA 11 toolove Pythonu preko `executeTool()`; ako backend faila, pada natrag na legacy handler (po MIGRATION_PLAN.md "Keep legacy implementations available until the Python versions are verified").
  - `PHASE11_DELEGATED_TOOLS` set: `note_add`, `note_search`, `note_list`, `records_*`, `artifact_*`, `screen_snapshot`, `ui_inspect`.
  - `adaptPythonToolResponse()` konvertuje `ToolExecutionResponse` u legacy `{ok, artifact, ...}` shape koji `App.tsx` i Realtime function-call flow očekuju (ekstraktuje `result.artifact`).
  - `handleEventsList` IPC handler + `"events:list"` u allowlist-u.
  - **Ispravljena syntax greška iz FAZE 9 commit-a**: `handlePlanStepUpdate` nije imao `}` — uočeno tokom FAZE 11 rada i popravljeno (FAZA 9 commit je prošao jer vite ne parsira `main.cjs`, ali bi Electron crash-ovao pri učitavanju).

### React UI (event bridge polling)

- `src/vite-env.d.ts` — `BackendEvent` tip + `listEvents` u `window.ricky` interfejsu.
- `src/App.tsx` — `useEffect` koji poll-uje `/events` svakih 3s sa timestamp cursor; na `artifact.created` fetch-uje taj artifact preko `artifact_get` tool-a i prikazuje u `ArtifactPanel`; `tool.completed`/`tool.failed`/`backend.ready` dodaje u Activity timeline.
  - Artifacts kreirani preko model tool calls se već prikazuju kroz postojeći `onArtifact` flow iz `realtime.ts` — event bridge pokriva *out-of-band* artifact updates (background tool runs, budući agent runtime).

### Testovi

- `tests/test_phase11_tools.py` — 13 testova:
  - note_add (create + artifact), note_add validacija, note_search, note_list
  - records_create + search, records_update (field merge), records_delete (FAZA 10 confirmation_id binding sa payload_hash match)
  - artifact_create (emituje event), artifact_get, artifact_list
  - screen_snapshot/ui_inspect → COMPUTER_MODE_REQUIRED (FAZA 10 permission engine)
  - /tools lista sadrži sve FAZA 11 toolove
  - /events endpoint vraća cursor

## Zašto je urađeno

FAZA 11 pomera low-risk memory i system toolove u Python backend, čime Electron ostaje tanak shell (arhitektonsko pravilo). Event bridge omogućava backend→UI komunikaciju za artifact updates i tool progress bez WebSocket dependency-ja (polling je MVP kompromis). Sve tool definicije sada prate `TOOL_CONTRACTS.md` i `SECURITY_MODEL.md` risk levela, što FAZA 10 permission engine koristi za automatko gate-ovanje.

## Kako je urađeno

- **Tool execution kroz FAZA 10 permission engine**: svaki tool call prolazi kroz `ToolExecutor.execute()` koji zove `check_permission()` (FAZA 10). Za `records_delete` (critical) — zahtijeva `confirmation_id` u `context.confirmation_id`, i confirmation payload_hash mora matchati stvarne argumente. Za `screen_snapshot`/`ui_inspect` — `requires_computer_mode=True` → `COMPUTER_MODE_REQUIRED` ako `context.computer_mode` nije `true`. Ovo radi automatski jer su FAZA 11 toolovi registrovani sa ispravnim flagovima.
- **Event bridge**: `EventBus.emit()` upisuje u `activity_events` tabelu (iz FAZE 7). `GET /events?since=<ts>` vraća eventove sa timestampom većim od cursor-a, oldest-first. UI čuva `next_cursor` i poll-uje svakih 3s.
- **Electron delegacija**: `PHASE11_DELEGATED_TOOLS` set + try/catch fallback na legacy. `adaptPythonToolResponse()` čuva `execution_id`/`tool_state` (FAZA 10) u povratnoj vrijednosti.
- **Screenshot**: Pillow `ImageGrab.grab_all_monitors()` (multi-monitor) sa kompozitom na jedan canvas; fallback na `ImageGrab.grab()`. Bez `mss` dependency-ja.
- **ui_inspect**: stdlib `ctypes.windll.user32` za `GetForegroundWindow`/`GetWindowTextW`/`GetWindowThreadProcessId` + `psutil` za process name. Bez `pywinauto`.

## Šta nije dirano

- Nije diran `src/lib/realtime.ts` (WebRTC/OpenAI Realtime audio pipeline).
- Nije diran FAZA 10 permission engine / cancellation registry / payload_hash (samo integrisan preko tog stanja).
- Nije diran legacy PowerShell computer-use (`computer_*` alati) — oni ostaju za FAZU 13/14.
- Nije implementiran WebSocket (event bridge koristi polling — 3s interval).
- Nije migriran `web_search`/`image_generate`/thumbnail alate (to je FAZA 16).
- Nije diran `set_mode`/`artifact_show`/`show_menu`/`mermaid_render` — oni ostaju Electron-side (ne spadaju u FAZU 11 scope).

## Verifikacija

Pokrenuto:

```text
cd python_backend && python -m pytest -q
npm run typecheck
npm run build
node --check electron/main.cjs && node --check electron/services/pythonClient.cjs
node smoke (startPythonBackend + REST round-trip svih FAZA 11 toolova + events)
```

Rezultati:

```text
pytest: 59 passed (46 FAZA 10 + 13 FAZA 11), 1 warning (FastAPI TestClient deprecation)
typecheck: prošao (tsc --noEmit bez grešaka)
build: prošao (vite/rolldown)
node --check: čist (syntax greška iz FAZE 9 ispravljena)
node smoke:
  - tools list: 14 toolova (echo + 13 FAZA 11) — svi tu
  - note_add: ok, vraća note + artifact
  - records_create + search: radi, 1 record found
  - artifact_create: ok, emituje artifact.created event
  - events: 9 eventova, backend.ready + artifact.created prisutni, next_cursor postavljen
  - screen_snapshot bez computer_mode: COMPUTER_MODE_REQUIRED (FAZA 10 radi)
```

## Rizici/ograničenja

- **Polling umjesto WebSocket-a**: event bridge poll-uje svakih 3s. Za produktivno korištenje prihvatljivo; pravi push (WebSocket) dolazi kasnije.
- **Screenshot multi-monitor kompozit**: `grab_all_monitors()` se依赖 Pillow verziji; na starijim verzijama može pasti na `grab()` (single monitor). Testirano na trenutnoj Pillow verziji u repo-u.
- **ui_inspect `ui_tree_preview`**: vraća prazan niz (MVP — UIA inspekcija je eksplicitno odložena, vidi IMPLEMENTATION_PLAN FAZA 10 "Ne forsirati savršenu UIA inspekciju odmah").
- **records_delete legacy `confirmed:true` arg**: handler i dalje provjerava `confirmed:true` (legacy-compatible), ali FAZA 10 permission engine dodatno zahtijeva `confirmation_id` sa matching payload_hash. Oboje moraju biti zadovoljno — što je ispravno (critical alat, dvostruka zaštita).
- **Fallback na legacy**: ako Python backend nije dostupan, FAZA 11 toolovi padaju na legacy Electron handler (JSON db za notes/records, PowerShell za screenshot/ui_inspect). Ovo znači da notes kreirani preko legacy JSON db NEĆE biti u SQLite-u — poznati kompromis dok se ne verifikuje da Python verzije rade end-to-end (onda se legacy briše u FAZI 17).
- **Syntax greška iz FAZE 9 ispravljena**: `handlePlanStepUpdate` fali `}` — uođeno i popravljeno u ovoj fazi. Ovo je trebalo biti uhvaćeno u FAZI 9, ali `npm run build` ne parsira `main.cjs`. Preporuka: dodati `node --check electron/main.cjs` u CI/build skriptu.

## Potreban follow-up

- **FAZA 12** (companion orb) je sljedeća: zasebni `BrowserWindow`, orb prikazuje `VoiceState`, context menu, drag/position.
- **FAZA 13/14** (computer-use v1/v2) su i dalje BLOCKED iza Security Gate 0 — ali Gate 0 je sad blizu zatvaranja (FAZA 10 permission engine radi, FAZA 11 tool manifest postoji). Preostaju backend local auth token i path sandbox.
- **WebSocket push**: zamijeniti 3s polling stvarnim push kanalom kad se uvede.
- **UIA inspekcija**: `ui_inspect.ui_tree_preview` treba popuniti pravim UI tree-jem u FAZI 14 (computer-use v2).
- **CI skripta**: dodati `node --check electron/main.cjs` i `node --check electron/preload.cjs` u build pipeline da se syntax greške u main procesu uhvate prije Electron start-a.

## Potrebna korisnička potvrda

Prije commita treba potvrditi:

1. Da li želite da ručno testiram UI u Electron prozoru (`npm run dev`) — kreiranje note-a kroz voice/text, artifact prikaz kroz event bridge — ili su backend testovi + node smoke dovoljni?
2. Da li da commitujem i FAZA 9 syntax fix (`handlePlanStepUpdate` `}`) kao dio FAZE 11 commit-a, ili da to bude zaseban fix commit? (Trenutno bi bilo u FAZA 11 commit-u jer je uođeno tokom ovog rada.)
3. Worktree sadrži i nepratene `assets/Ricky-agent-3.png`, `assets/Ricky-agent-4-lokalizacija-podesavanje.png` — ostaju van commit-a kao i ranije?
