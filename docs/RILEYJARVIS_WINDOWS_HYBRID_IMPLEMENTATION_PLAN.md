# RileyJarvis Windows Hybrid — implementacioni plan za Codex i Claude Code

## 0. Svrha dokumenta

Ovaj dokument je praktičan plan za postepenu migraciju RileyJarvis Windows porta iz trenutnog Electron/Node/PowerShell prototipa u hibridnu arhitekturu:

```text
React UI
  -> Electron preload / IPC
  -> Electron main process kao tanak shell/bridge
  -> Python backend kao mozak aplikacije
  -> Python tools: Windows automation, screenshot, UI inspect, storage, agent runtime, artifacts
  -> SQLite lokalna baza, logs, lokalni fajlovi
```

Cilj nije full rewrite. Cilj je postepeno izvlačenje logike iz `electron/main.cjs` u modularan Python backend, bez rušenja postojećeg UI-ja.

---

## 1. Glavna arhitektonska odluka

### 1.1 Electron/React ostaje UI sloj

Electron/React ostaje zadužen za:

- glavni prozor aplikacije,
- frameless UI,
- toolbar i mode switch,
- artifact panel,
- prikaz razgovora,
- IPC komunikaciju između renderer-a i main procesa,
- startovanje i gašenje Python backend procesa,
- prosljeđivanje eventa iz Python backend-a prema React UI-ju.

### 1.2 Python postaje mozak aplikacije

Python backend preuzima:

- agent runtime,
- tool registry,
- tool execution,
- Windows automation,
- screenshot,
- UI inspect,
- memoriju,
- action log,
- SQLite storage,
- AI model/API pozive,
- permission/risk/confirmation sloj,
- artifact generation.

### 1.3 `electron/main.cjs` ne smije ostati mozak

`electron/main.cjs` smije raditi samo:

- createWindow,
- app lifecycle,
- IPC setup,
- Python process management,
- bridge prema React UI-ju,
- bridge prema Python backend-u.

U `electron/main.cjs` ne dodavati novu poslovnu logiku, agent logiku, computer-use logiku, storage logiku ili OpenAI logiku.

---

## 2. Pravila za agente prije svake izmjene

Ovo važi za Codex, Claude Code i bilo kog drugog agenta.

### 2.1 Obavezna pravila

1. Ne raditi veliki refaktor u jednom koraku.
2. Svaka faza mora biti mali PR ili mali skup promjena.
3. Prije izmjene postojeće funkcije/klase/metode, prvo pročitati njen kontekst i call sites.
4. Ako je GitNexus dostupan za ovaj repo, prije izmjene simbola pokrenuti impact analysis.
5. Ako impact analysis pokaže HIGH ili CRITICAL rizik, stati i prijaviti korisniku prije promjene.
6. Prije commita pokrenuti testove i provjeru promjena.
7. Ne raditi find-and-replace rename simbola ako postoji GitNexus rename alat.
8. Ne brisati postojeće PowerShell toolove dok Python zamjena nije testirana.
9. Ne uvoditi shell execution tool koji model može pozvati slobodno.
10. Ne stavljati API ključeve, `.env.local`, logove sa tajnama ili `node_modules` u git.

### 2.2 GitNexus pravilo

Ako je GitNexus indeks podešen za ovaj repo:

```text
Prije izmjene:
  gitnexus_impact(target: "symbolName", direction: "upstream")

Za istraživanje:
  gitnexus_query(query: "concept")
  gitnexus_context(name: "symbolName")

Prije commita:
  gitnexus_detect_changes()
```

Ako GitNexus nije podešen za ovaj repo, agent mora to jasno navesti i koristiti ručnu analizu:

```text
- pronaći module koji se mijenjaju
- pronaći import/call references
- objasniti blast radius
- tek onda mijenjati
```

---

## 3. Ciljna struktura repozitorija

```text
repo-root/
  electron/
    main.cjs
    preload.cjs

    core/
      window.cjs
      ipc.cjs
      appLifecycle.cjs
      env.cjs

    services/
      pythonProcess.cjs
      pythonClient.cjs
      eventBridge.cjs
      toolBridge.cjs

    tools_legacy/
      powershell/
        runPowerShell.cjs
        computerOpenApp.cjs
        computerTypeText.cjs
        computerPressKey.cjs
        computerClick.cjs
        computerScroll.cjs
        screenSnapshot.cjs
        uiInspect.cjs

  src/
    App.tsx
    components/
      ArtifactPanel.tsx
      RickyFace.tsx
      Toolbar.tsx
    services/
      apiClient.ts
      eventClient.ts
    types/
      artifacts.ts
      tools.ts
      events.ts

  python_backend/
    app/
      main.py

      core/
        config.py
        paths.py
        logging.py
        errors.py
        lifecycle.py

      api/
        health.py
        tools.py
        artifacts.py
        events.py
        agent.py

      agent/
        runtime.py
        tool_registry.py
        tool_executor.py
        conversation_state.py
        prompt_builder.py
        model_client.py

      tools/
        system/
          open_app.py
          process_info.py
        windows/
          active_window.py
          screenshot.py
          ui_inspect.py
          keyboard.py
          mouse.py
          scroll.py
        files/
          read_file.py
          write_file.py
          list_files.py
        memory/
          notes.py
          records.py
        web/
          search.py
        images/
          generate.py

      security/
        permissions.py
        risk.py
        confirmations.py
        allowlist.py
        redaction.py

      storage/
        db.py
        models.py
        migrations/
        repositories/
          action_log_repo.py
          artifact_repo.py
          notes_repo.py
          records_repo.py
          settings_repo.py

      schemas/
        tool.py
        artifact.py
        event.py
        action_log.py
        common.py

      services/
        action_log.py
        artifact_service.py
        screenshot_store.py
        openai_client.py
        exa_client.py

    tests/
      test_health.py
      test_tools.py
      test_permissions.py
      test_storage.py
      test_action_log.py

    pyproject.toml
    README.md

  data/
    .gitkeep

  logs/
    .gitkeep

  docs/
    ARCHITECTURE.md
    MIGRATION_PLAN.md
    TOOL_CONTRACTS.md
    SECURITY_MODEL.md
    WINDOWS_AUTOMATION_NOTES.md
    PACKAGING_PLAN.md

  AGENTS.md
  CLAUDE.md
  package.json
  .env.example
  .gitignore
```

---

## 4. Tool contract

Svi toolovi moraju imati isti format, bez obzira da li su implementirani u Electron legacy sloju ili u Python backend-u.

### 4.1 Tool definition schema

```json
{
  "name": "screen_snapshot",
  "description": "Capture current desktop screenshot.",
  "input_schema": {
    "type": "object",
    "properties": {
      "monitor": {
        "type": "string",
        "enum": ["all", "primary", "active"],
        "default": "all"
      }
    },
    "required": []
  },
  "risk": "low",
  "requires_confirmation": false,
  "requires_computer_mode": false,
  "allowed_in_background": true,
  "timeout_ms": 5000,
  "implemented_by": "python",
  "enabled": true
}
```

### 4.2 Tool execution request

```json
{
  "tool_name": "computer_type_text",
  "arguments": {
    "text": "Hello world"
  },
  "context": {
    "computer_mode": true,
    "conversation_id": "optional-id",
    "request_id": "optional-id"
  }
}
```

### 4.3 Tool execution response

```json
{
  "ok": true,
  "tool_name": "computer_type_text",
  "result": {
    "typed_chars": 11
  },
  "artifact_ids": [],
  "event_ids": [],
  "action_log_id": "uuid",
  "duration_ms": 230
}
```

### 4.4 Error response

```json
{
  "ok": false,
  "tool_name": "computer_type_text",
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Tool requires computer mode and explicit confirmation.",
    "details": {
      "risk": "high",
      "requires_computer_mode": true
    }
  },
  "action_log_id": "uuid"
}
```

---

## 5. Security model

### 5.1 Risk levels

```text
low
medium
high
critical
```

### 5.2 Risk examples

```text
low:
  - read notes
  - create artifact
  - list tools
  - health check
  - screenshot without OCR or external upload

medium:
  - open app
  - search web
  - read file from allowed workspace
  - inspect active window

high:
  - type text
  - click
  - press key
  - edit file
  - paste clipboard
  - interact with browser

critical:
  - delete files
  - run shell command
  - install package
  - send email/message
  - execute arbitrary PowerShell/Python
  - access secrets
```

### 5.3 Permission rules

1. `critical` tools are disabled by default.
2. `high` tools require computer mode and explicit confirmation.
3. `medium` tools may require confirmation depending on context.
4. `low` tools can run without confirmation.
5. No model-facing arbitrary shell command tool.
6. File tools are restricted to allowed folders.
7. Sensitive values must be redacted from logs.
8. Every tool call must be logged.
9. Computer-use tools must capture active window before and after execution.
10. `computer_type_text`, `computer_click`, `computer_press_key`, `computer_scroll` must not execute if active app is not allowed or if computer mode is disabled.

---

## 6. Storage model

Koristiti SQLite u Python backend-u.

### 6.1 Minimalne tabele

```text
actions
artifacts
notes
records
settings
tool_runs
screenshots
conversations
memory_items
```

### 6.2 `tool_runs` tabela

```text
id                  TEXT PRIMARY KEY
timestamp           TEXT NOT NULL
tool_name           TEXT NOT NULL
input_json          TEXT NOT NULL
output_json         TEXT
status              TEXT NOT NULL
risk_level          TEXT NOT NULL
requires_confirmation INTEGER NOT NULL
computer_mode       INTEGER NOT NULL
active_window_before TEXT
active_window_after  TEXT
screenshot_before_path TEXT
screenshot_after_path  TEXT
error_code          TEXT
error_message       TEXT
duration_ms         INTEGER
```

### 6.3 `artifacts` tabela

```text
id              TEXT PRIMARY KEY
created_at      TEXT NOT NULL
type            TEXT NOT NULL
title           TEXT NOT NULL
content_json    TEXT NOT NULL
created_by_tool TEXT
conversation_id TEXT
```

---

## 7. Artifact model

Artifact tipovi:

```text
markdown
table
json
image
diagram
html_preview
log
code
```

Artifact payload primjer:

```json
{
  "id": "uuid",
  "type": "markdown",
  "title": "Analiza aktivnog prozora",
  "content": "...",
  "created_by_tool": "ui_inspect"
}
```

Python backend kreira artifact. React UI ga prikazuje. Electron samo prenosi event.

---

## 8. Faze implementacije

# FAZA 0 — Baseline i zaštita trenutnog stanja

## Cilj

Sačuvati verziju Windows porta koja trenutno radi, prije bilo kakvog refaktora.

## Zadatak za agenta

```text
Create a safe baseline for the current Windows port before any architecture migration.
Do not refactor application logic in this phase.
Add documentation files only if needed.
```

## Konkretni koraci

1. Napraviti novu granu:

```bash
git checkout -b hybrid-python-backend
```

2. Napraviti tag trenutnog stanja:

```bash
git tag windows-port-baseline
```

3. Provjeriti da app radi:

```bash
npm install
npm run dev
```

4. Provjeriti da `.env.local` i `node_modules` nisu u git-u.

5. Dodati ili dopuniti `.gitignore`:

```gitignore
node_modules/
.env
.env.local
.env.*.local
logs/
data/*.db
data/*.sqlite
data/screenshots/
python_backend/.venv/
python_backend/__pycache__/
python_backend/**/*.pyc
```

## Acceptance criteria

- Postoji branch `hybrid-python-backend`.
- Postoji tag `windows-port-baseline`.
- `npm run dev` i dalje pokreće aplikaciju.
- Nema promjene ponašanja aplikacije.

---

# FAZA 1 — Dokumentacija arhitekture

## Cilj

Zakucati odluku da Electron ostaje UI shell, a Python postaje backend/agent runtime.

## Zadatak za agenta

```text
Add architecture documentation for the planned Electron + Python hybrid migration.
Do not change runtime code in this phase.
```

## Fajlovi za dodati

```text
docs/ARCHITECTURE.md
docs/MIGRATION_PLAN.md
docs/TOOL_CONTRACTS.md
docs/SECURITY_MODEL.md
docs/WINDOWS_AUTOMATION_NOTES.md
docs/PACKAGING_PLAN.md
```

## Sadržaj `docs/ARCHITECTURE.md`

Mora sadržati:

```text
- React renderer = UI
- Electron main = app shell + IPC + process manager
- Python backend = agent runtime + tools + storage + automation
- SQLite = local persistent storage
- WebSocket/events = backend -> UI updates
- REST/HTTP = request/response tool execution
```

## Sadržaj `docs/MIGRATION_PLAN.md`

Mora sadržati faze iz ovog dokumenta.

## Sadržaj `docs/TOOL_CONTRACTS.md`

Mora sadržati standardni tool definition, tool execution request, response i error response.

## Sadržaj `docs/SECURITY_MODEL.md`

Mora sadržati risk levels, confirmation rules i zabranu arbitrary shell tool-a.

## Acceptance criteria

- Dokumentacija postoji.
- Jasno piše da se nova logika ne dodaje u `electron/main.cjs`.
- Nema runtime promjena.

---

# FAZA 2 — Ažurirati AGENTS.md i CLAUDE.md za ovaj projekat

## Cilj

Napraviti pravila za Codex/Claude Code koja odgovaraju ovom repo-u, a ne starom FieldFix-IT projektu.

## Zadatak za agenta

```text
Update AGENTS.md and CLAUDE.md so they describe the RileyJarvis Windows Hybrid architecture and agent workflow.
Preserve the GitNexus discipline, but remove or clearly mark FieldFix-IT-specific assumptions if this repository is not indexed as FieldFix-IT.
```

## Obavezno uključiti

```text
- Project name: RileyJarvis Windows Hybrid
- Architecture rule: Electron is UI shell, Python is backend brain
- Do not add new business logic to electron/main.cjs
- Prefer small PRs
- Use GitNexus impact analysis if the repository is indexed
- If GitNexus is not available, manually report blast radius
- Before commit: tests, lint, git status, change summary
```

## Predloženi AGENTS.md skeleton

```markdown
# RileyJarvis Windows Hybrid — Agent Rules

## Architecture rule
Electron/React is the UI shell. Python backend owns agent runtime, tools, storage, automation and AI integrations.

## Do not do
- Do not add new agent logic to electron/main.cjs.
- Do not add arbitrary shell execution tools exposed to the model.
- Do not remove legacy PowerShell tools until Python replacements are tested.
- Do not commit secrets, .env.local, node_modules, logs or local databases.

## Before editing
- Inspect the module and call sites.
- If GitNexus is available, run impact analysis before editing symbols.
- If GitNexus is not available, report manual blast radius.

## Before commit
- Run relevant tests.
- Run lint/type checks when available.
- Run gitnexus_detect_changes if available.
- Summarize affected modules and behavior changes.
```

## Acceptance criteria

- `AGENTS.md` i `CLAUDE.md` ne tvrde pogrešno da je repo FieldFix-IT, osim ako stvarno jeste.
- Pravila jasno forsiraju modularnu migraciju.
- Pravila ne traže nepostojeće alate kao obavezu ako nisu podešeni u ovom repo-u.

---

# FAZA 3 — Razbiti `electron/main.cjs` bez promjene ponašanja

## Cilj

Smanjiti `main.cjs` i izvući postojeće funkcije u module, bez promjene ponašanja.

## Zadatak za agenta

```text
Refactor electron/main.cjs into smaller Electron modules without changing behavior.
Do not introduce the Python backend yet.
Keep all existing Windows PowerShell behavior working.
```

## Nova struktura

```text
electron/
  main.cjs
  preload.cjs
  core/
    window.cjs
    ipc.cjs
    env.cjs
    appLifecycle.cjs
  tools_legacy/
    powershell/
      runPowerShell.cjs
      computerOpenApp.cjs
      computerTypeText.cjs
      computerPressKey.cjs
      computerClick.cjs
      computerScroll.cjs
      screenSnapshot.cjs
      uiInspect.cjs
```

## Koraci

1. Izvući `createWindow()` u `electron/core/window.cjs`.
2. Izvući env loading u `electron/core/env.cjs`.
3. Izvući IPC handler registraciju u `electron/core/ipc.cjs`.
4. Izvući `runPowerShell()` u `electron/tools_legacy/powershell/runPowerShell.cjs`.
5. Izvući svaki PowerShell computer-use tool u poseban fajl.
6. `main.cjs` ostaje entrypoint koji samo povezuje module.

## Važno

Ne mijenjati tool input/output format u ovoj fazi.

## Test

```bash
npm run dev
```

Ručno provjeriti:

```text
- app se otvara
- X dugme zatvara app
- artifact panel radi
- postojeći Windows tools rade kao ranije
```

## Acceptance criteria

- `main.cjs` je kraći i čitljiviji.
- Postojeći behavior nije promijenjen.
- Legacy PowerShell tools i dalje rade.
- Nema Python backend-a još.

---

# FAZA 4 — Python backend skeleton

## Cilj

Dodati prazan, ali funkcionalan Python backend.

## Zadatak za agenta

```text
Add a minimal Python FastAPI backend under python_backend/.
Do not connect it to Electron yet.
Implement /health, /tools and /tools/execute with dummy tools only.
```

## Struktura

```text
python_backend/
  app/
    main.py
    core/
      config.py
      logging.py
      errors.py
    api/
      health.py
      tools.py
    agent/
      tool_registry.py
      tool_executor.py
    schemas/
      tool.py
      common.py
  tests/
    test_health.py
    test_tools.py
  pyproject.toml
  README.md
```

## Minimalni endpointi

```text
GET /health
GET /tools
POST /tools/execute
```

## Dummy tool

Dodati dummy tool:

```text
echo
```

Input:

```json
{"text": "hello"}
```

Output:

```json
{"text": "hello"}
```

## Predložene dependencies

```text
fastapi
uvicorn[standard]
pydantic
python-dotenv
pytest
httpx
```

## Primjer komandi

```bash
cd python_backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8765
pytest
```

## Acceptance criteria

- `GET /health` vraća `{"ok": true}`.
- `GET /tools` vraća listu toolova.
- `POST /tools/execute` radi za `echo` tool.
- Testovi prolaze.
- Electron još nije spojen na Python.

---

# FAZA 5 — Electron pokreće Python backend

## Cilj

Electron treba automatski pokrenuti Python backend u dev modu.

## Zadatak za agenta

```text
Add Electron-side Python process management.
Electron should start the Python backend in dev mode, wait for /health, forward backend logs, and stop the process on app quit.
Do not migrate real tools yet.
```

## Dodati

```text
electron/services/pythonProcess.cjs
electron/services/pythonClient.cjs
```

## `pythonProcess.cjs` odgovornosti

```text
- resolve backend path
- start Python process
- wait for GET /health
- pipe stdout/stderr to Electron console
- expose backend status
- stop backend on app quit
```

## `pythonClient.cjs` odgovornosti

```text
- GET /health
- GET /tools
- POST /tools/execute
- handle timeout
- handle backend unavailable
```

## Dev start varijanta

U dev modu koristiti:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

ili Windows venv ako postoji:

```bash
python_backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

## Acceptance criteria

- `npm run dev` pokreće i Electron i Python backend.
- Ako Python backend ne startuje, UI ili terminal jasno prikaže grešku.
- Zatvaranje Electron aplikacije gasi Python backend.
- Legacy PowerShell tools i dalje rade.

---

# FAZA 6 — Tool bridge Electron -> Python

## Cilj

Electron treba moći pozvati Python tool preko standardnog contract-a.

## Zadatak za agenta

```text
Implement the Electron-to-Python tool bridge using the standard tool contract.
Add one UI/dev path that can call the Python echo tool and display the result.
Do not migrate real tools yet.
```

## Dodati

```text
electron/services/toolBridge.cjs
src/services/apiClient.ts
src/types/tools.ts
```

## Flow

```text
React UI
  -> preload API
  -> ipcMain handler
  -> toolBridge.cjs
  -> pythonClient.cjs
  -> Python POST /tools/execute
  -> result back to React UI
```

## IPC kanali

```text
python:health
python:list-tools
python:execute-tool
```

## Acceptance criteria

- UI može pozvati Python `echo` tool.
- Rezultat se prikazuje u UI-ju ili dev logu.
- Greške backend-a se uredno prikazuju.
- Nema migracije realnih toolova još.

---

# FAZA 7 — SQLite storage i action log

## Cilj

Dodati trajnu lokalnu bazu i logovanje svake tool akcije.

## Zadatak za agenta

```text
Add SQLite-backed storage to the Python backend.
Implement action/tool run logging for all Python tool executions.
Do not migrate Windows computer-use tools yet.
```

## Dodati

```text
python_backend/app/storage/db.py
python_backend/app/storage/models.py
python_backend/app/storage/repositories/action_log_repo.py
python_backend/app/services/action_log.py
python_backend/app/schemas/action_log.py
```

## Baza

Lokacija:

```text
data/ricky.sqlite
```

ili u dev modu:

```text
python_backend/data/ricky.sqlite
```

## Obavezno logovati

```text
tool_name
input_json
status
risk_level
computer_mode
output_json ili error
start/end/duration
```

## Acceptance criteria

- Python `echo` tool kreira zapis u `tool_runs`.
- Greška u toolu takođe kreira zapis.
- Testovi pokrivaju success i failure log.

---

# FAZA 8 — Migracija memorije: notes/records/artifacts

## Cilj

Prebaciti bezopasne toolove iz Node/JSON logike u Python/SQLite.

## Zadatak za agenta

```text
Migrate low-risk memory and artifact tools to the Python backend.
Keep legacy implementations available until the Python versions are verified.
```

## Toolovi za migraciju

```text
notes_create
notes_search
records_create
records_search
artifact_create
artifact_get
artifact_list
```

## Dodati

```text
python_backend/app/tools/memory/notes.py
python_backend/app/tools/memory/records.py
python_backend/app/services/artifact_service.py
python_backend/app/storage/repositories/notes_repo.py
python_backend/app/storage/repositories/records_repo.py
python_backend/app/storage/repositories/artifact_repo.py
```

## Acceptance criteria

- Python backend čuva notes u SQLite.
- Python backend čuva records u SQLite.
- Python backend kreira artifacts.
- UI može prikazati artifact koji dolazi iz Python backend-a.
- Legacy JSON baza se ne briše u ovoj fazi.

---

# FAZA 9 — Event bridge i artifact panel

## Cilj

Python backend treba moći poslati event UI-ju, posebno za artifact updates.

## Zadatak za agenta

```text
Implement backend-to-UI events for artifacts and tool progress.
Use WebSocket or a polling fallback, but prefer WebSocket if stable in the current app.
```

## Event tipovi

```text
backend:ready
tool:started
tool:completed
tool:failed
artifact:created
artifact:updated
permission:confirmation_required
```

## Event schema

```json
{
  "id": "uuid",
  "type": "artifact:created",
  "timestamp": "2026-07-04T12:00:00Z",
  "payload": {
    "artifact_id": "uuid"
  }
}
```

## Acceptance criteria

- Kada Python kreira artifact, React ArtifactPanel ga može prikazati.
- Tool progress se može prikazati u UI-ju ili dev logu.
- Ako WebSocket pukne, aplikacija ne pada.

---

# FAZA 10 — Screenshot i active window u Pythonu

## Cilj

Prebaciti `screen_snapshot` i osnovni `ui_inspect` u Python.

## Zadatak za agenta

```text
Implement Python versions of screen_snapshot and ui_inspect.
Do not remove the legacy PowerShell versions yet.
Return structured information about active window, process and screens.
```

## Predložene biblioteke

```text
mss
Pillow
psutil
pywinauto
```

## `screen_snapshot` output

```json
{
  "image_path": "data/screenshots/2026-07-04/uuid.png",
  "monitors": [
    {
      "index": 0,
      "x": 0,
      "y": 0,
      "width": 1920,
      "height": 1080
    }
  ]
}
```

## `ui_inspect` output

```json
{
  "active_window": {
    "title": "Untitled - Notepad",
    "process": "notepad.exe",
    "pid": 1234
  },
  "ui_tree_preview": []
}
```

U prvoj verziji `ui_tree_preview` može biti prazan ili minimalan. Ne forsirati savršenu UIA inspekciju odmah.

## Acceptance criteria

- Python `screen_snapshot` radi na Windows-u.
- Screenshot se snima u kontrolisan folder.
- Python `ui_inspect` vraća aktivan prozor i proces.
- Tool runs se loguju.
- Legacy PowerShell fallback ostaje.

---

# FAZA 11 — Permission system

## Cilj

Prije migracije tastature/miša dodati sigurnosni sloj.

## Zadatak za agenta

```text
Implement the Python permission/risk/confirmation layer before enabling high-risk computer-use tools.
No keyboard or mouse automation should bypass this layer.
```

## Dodati

```text
python_backend/app/security/risk.py
python_backend/app/security/permissions.py
python_backend/app/security/confirmations.py
python_backend/app/security/allowlist.py
python_backend/app/security/redaction.py
```

## Pravila

```text
- high risk requires computer_mode=true
- high risk requires confirmation unless explicitly configured otherwise
- critical disabled by default
- allowed apps checked for keyboard/mouse tools
- tool input/output redacted before log if sensitive
```

## Allowlist primjer

```json
{
  "allowed_apps": [
    "notepad.exe",
    "calc.exe",
    "chrome.exe",
    "code.exe"
  ],
  "blocked_apps": [
    "powershell.exe",
    "cmd.exe",
    "regedit.exe"
  ]
}
```

## Acceptance criteria

- High-risk dummy tool ne može raditi bez computer mode.
- High-risk dummy tool traži confirmation.
- Critical tool je disabled by default.
- Permission denied se loguje.

---

# FAZA 12 — Computer-use Python v1

## Cilj

Migrirati osnovne computer-use toolove u Python, ali sigurno.

## Zadatak za agenta

```text
Implement Python computer-use tools v1 behind the permission system.
Start with Notepad-only manual testing.
Keep legacy PowerShell tools as fallback.
```

## Toolovi

```text
computer_open_app
computer_type_text
computer_press_key
computer_click_coordinates
computer_scroll
```

## Biblioteke

```text
pywinauto
pyautogui
psutil
```

## Pravila

1. `computer_open_app` je medium risk.
2. `computer_type_text` je high risk.
3. `computer_press_key` je high risk.
4. `computer_click_coordinates` je high risk.
5. `computer_scroll` je high risk.
6. Svi high risk alati moraju proći permission check.
7. Prije i poslije akcije logovati active window.
8. Za high risk alate po mogućnosti napraviti screenshot before/after.

## Minimalni ručni test

```text
1. Otvori app.
2. Uključi computer mode.
3. Pozovi computer_open_app sa notepad.
4. Provjeri ui_inspect.
5. Pozovi computer_type_text "Test from Python backend".
6. Provjeri da tekst ide u Notepad.
7. Provjeri tool_runs log.
```

## Acceptance criteria

- Notepad test radi.
- Ako computer mode nije uključen, typing/click/press key ne rade.
- Ako aktivna aplikacija nije dozvoljena, tool se odbija.
- Svaka akcija je logovana.
- Legacy PowerShell fallback još postoji.

---

# FAZA 13 — Computer-use Python v2: UI element targeting

## Cilj

Smanjiti oslanjanje na koordinate i dodati klik/akciju po UI elementima.

## Zadatak za agenta

```text
Add element-based UI automation using pywinauto/UIA where possible.
Keep coordinate click as fallback only.
```

## Novi toolovi

```text
computer_find_elements
computer_click_element
computer_set_text_element
computer_get_element_text
```

## Element target schema

```json
{
  "app": "notepad.exe",
  "title_contains": "Untitled",
  "control_type": "Edit",
  "name": "Text Editor",
  "automation_id": "optional"
}
```

## Acceptance criteria

- `computer_find_elements` vraća listu osnovnih UI elemenata za Notepad.
- `computer_click_element` radi gdje je moguće.
- Ako element nije pronađen, vraća jasnu grešku.
- Coordinate click se koristi samo kao fallback.

---

# FAZA 14 — Agent runtime u Pythonu

## Cilj

Premjestiti agent brain u Python.

## Zadatak za agenta

```text
Implement a single-agent runtime in Python that can receive a user message, call registered tools, create artifacts, and return a response.
Do not build multi-agent orchestration yet.
```

## Moduli

```text
python_backend/app/agent/runtime.py
python_backend/app/agent/tool_registry.py
python_backend/app/agent/tool_executor.py
python_backend/app/agent/conversation_state.py
python_backend/app/agent/prompt_builder.py
python_backend/app/agent/model_client.py
```

## Endpointi

```text
POST /agent/message
GET /agent/conversations/{id}
```

## Runtime flow

```text
User message
  -> load conversation state
  -> load available tools
  -> build model prompt/request
  -> model returns text/tool calls
  -> execute tool calls through permission layer
  -> create artifacts/events if needed
  -> return final response
  -> log everything
```

## Važno

Ne uvoditi više agenata još. Samo:

```text
LocalDesktopAssistant
```

## Acceptance criteria

- Python agent može odgovoriti na običnu poruku.
- Python agent može pozvati low-risk tool.
- Python agent ne može zaobići permission layer.
- UI može poslati poruku i dobiti odgovor.

---

# FAZA 15 — Prebaciti OpenAI/Exa/image pozive u Python

## Cilj

AI i eksterni API pozivi treba da budu u Python backend-u, ne u Electron main procesu.

## Zadatak za agenta

```text
Move OpenAI/Exa/image service integrations from Electron main into Python services.
Keep environment variable compatibility with .env.local/.env.example.
```

## Dodati

```text
python_backend/app/services/openai_client.py
python_backend/app/services/exa_client.py
python_backend/app/tools/web/search.py
python_backend/app/tools/images/generate.py
```

## Pravila

1. API ključevi se čitaju iz env-a.
2. API ključevi se ne loguju.
3. Greške API-ja se vraćaju strukturisano.
4. Image output se čuva kao artifact.

## Acceptance criteria

- Web search radi iz Python backend-a.
- Image generation radi iz Python backend-a ako su ključevi dostupni.
- Electron više ne mora imati direktnu AI service logiku za migrirane dijelove.

---

# FAZA 16 — Deaktivacija legacy PowerShell toolova

## Cilj

Kada Python toolovi stabilno rade, legacy PowerShell toolove prebaciti u fallback ili ukloniti.

## Zadatak za agenta

```text
After Python replacements are verified, disable legacy PowerShell computer-use tools by default.
Keep a documented fallback flag for development only.
```

## Feature flag

```text
RICKY_USE_LEGACY_POWERSHELL_TOOLS=0
```

## Pravila

- Default: Python tools.
- Legacy: samo ako env flag uključen.
- Dokumentovati zašto legacy postoji.

## Acceptance criteria

- App koristi Python computer-use tools by default.
- Legacy PowerShell tools se ne pozivaju osim uz explicit env flag.
- Dokumentacija ažurirana.

---

# FAZA 17 — Test suite i quality gate

## Cilj

Uvesti minimum testova prije packaging faze.

## Zadatak za agenta

```text
Add automated tests and quality gates for the hybrid architecture.
Focus on backend tool execution, permission checks, storage, and Electron-Python process startup.
```

## Python testovi

```text
test_health.py
test_tools.py
test_permissions.py
test_storage.py
test_action_log.py
test_artifacts.py
```

## Electron testovi ili smoke skripte

```text
- backend starts
- health check passes
- tool bridge works
- backend process stops on app quit
```

## Quality commands

```bash
cd python_backend
pytest

cd ..
npm run build
```

Ako postoje lint/typecheck skripte:

```bash
npm run lint
npm run typecheck
```

## Acceptance criteria

- Backend testovi prolaze.
- Electron build prolazi.
- Ručni Notepad computer-use smoke test prolazi.

---

# FAZA 18 — Packaging plan

## Cilj

Napraviti instalabilnu Windows aplikaciju tek kada hibridna arhitektura radi.

## Zadatak za agenta

```text
Prepare packaging for Electron + bundled Python backend.
Do not start packaging until the Python backend is stable and legacy PowerShell tools are disabled by default.
```

## Opcije za Python packaging

```text
PyInstaller
Nuitka
```

## Finalna struktura

```text
Ricky/
  Ricky.exe
  resources/
    app.asar
    python_backend/
      ricky_backend.exe
      data/
      logs/
```

Electron u produkciji startuje:

```text
resources/python_backend/ricky_backend.exe --host 127.0.0.1 --port 8765
```

## Acceptance criteria

- Korisnik ne mora instalirati Python.
- App se pokreće duplim klikom.
- Backend se pokreće i gasi zajedno sa app-om.
- `.env.local` i API ključevi nisu upakovani slučajno.

---

## 9. Redoslijed PR-ova

```text
PR 01 - Baseline and docs
PR 02 - Project agent rules update
PR 03 - Split electron/main.cjs into modules
PR 04 - Add Python backend skeleton
PR 05 - Electron starts Python backend
PR 06 - Tool bridge Electron -> Python
PR 07 - SQLite storage and action log
PR 08 - Migrate notes/records/artifacts
PR 09 - Event bridge and artifact panel integration
PR 10 - Python screenshot and UI inspect
PR 11 - Permission/risk/confirmation system
PR 12 - Python computer-use v1
PR 13 - Python computer-use v2 element targeting
PR 14 - Python agent runtime
PR 15 - Move OpenAI/Exa/image integrations to Python
PR 16 - Disable legacy PowerShell tools by default
PR 17 - Test suite and quality gate
PR 18 - Packaging
```

---

## 10. Copy-paste master prompt za Codex ili Claude Code

> **Zastarjelo — ne koristiti direktno.** Brojevi faza ovdje ne odgovaraju više trenutnom stanju (vidi tabelu mapiranja u `docs/MIGRATION_PLAN.md`), a ovaj prompt ne pominje voice-first pravilo (`src/lib/realtime.ts` se ne smije zamijeniti Python audio pipeline-om). Koristi ažuriranu verziju u [MIGRATION_PLAN.md](./MIGRATION_PLAN.md#master-prompt-za-novi-agent-session) — ista namjena, ispravan sadržaj. Ova verzija je ostavljena samo kao istorijski zapis.

Koristi ovaj prompt kada pokrećeš novi agent session:

```text
You are working on RileyJarvis Windows Hybrid.

Goal:
Migrate the current Windows-adapted Electron RileyJarvis prototype to a modular hybrid architecture where React/Electron remains the UI shell and Python becomes the backend brain for tools, storage, Windows automation, artifacts and agent runtime.

Hard architecture rules:
- React renderer is UI.
- Electron main process is only app shell, IPC bridge and Python process manager.
- Python backend owns agent runtime, tools, storage, automation and AI integrations.
- Do not add new business logic to electron/main.cjs.
- Do not remove legacy PowerShell tools until Python replacements are implemented and tested.
- No arbitrary shell execution tool exposed to the model.
- All tool calls must go through a tool registry and permission/risk layer.
- All tool calls must be logged.

Workflow rules:
- Work phase by phase.
- Do not do a large rewrite.
- Before editing existing symbols, inspect context and call sites.
- If GitNexus is available for this repo, run impact analysis before editing symbols and run detect changes before commit.
- If GitNexus is not available, manually report blast radius before editing.
- After changes, run relevant tests/build commands.
- Summarize changed files, behavior changes, risks and next step.

Current task:
Implement only PHASE <NUMBER>: <PHASE NAME> from IMPLEMENTATION_PLAN.md.
Do not implement later phases.
```

---

## 11. Phase-specific prompt template

Za svaku fazu koristi:

```text
Implement PHASE <NUMBER>: <NAME>.

Scope:
<copy scope from implementation plan>

Do not:
- Do not implement later phases.
- Do not rewrite unrelated files.
- Do not change UI behavior unless this phase requires it.
- Do not remove working legacy behavior unless acceptance criteria says so.

Before editing:
- Inspect relevant files.
- Report expected blast radius.
- If GitNexus is available, run impact analysis.

After editing:
- Run relevant tests/build.
- Report changed files.
- Report behavior changes.
- Report any risk or unfinished item.
```

---

## 12. Najveće greške koje agenti moraju izbjeći

```text
- Full rewrite u Python odmah.
- Brisanje Electron UI-ja.
- Guranje nove logike nazad u electron/main.cjs.
- Preuranjen packaging.
- Korištenje koordinatnog klika kao primarnog rješenja dugoročno.
- Izlaganje shell command tool-a modelu.
- Miješanje storage logike između JSON, Electron i Python bez plana.
- Pravljenje multi-agent sistema prije stabilnog tool registry-ja.
- Uvođenje novih dependencies bez objašnjenja.
- Nevođenje action log-a.
```

---

## 13. Minimalna definicija uspjeha

Projekat se smatra uspješno migriranim u hibridnu arhitekturu kada:

```text
- Electron/React UI radi kao prije.
- Electron automatski startuje Python backend.
- Python backend ima /health, /tools, /tools/execute.
- Toolovi su registrovani u Python registry-ju.
- Tool calls prolaze kroz permission/risk layer.
- Tool calls se loguju u SQLite.
- Artifacts dolaze iz Python backend-a i prikazuju se u React panelu.
- Screenshot/ui_inspect rade iz Python-a.
- Osnovni computer-use radi kroz Python na Notepad smoke testu.
- Legacy PowerShell tools su disabled by default.
- Agent runtime je u Python-u.
- App se može buildati bez rušenja.
```

---

## 14. Kratka odluka za budućnost

Ako UI ostane važan i vizuelno bogat, zadržati Electron/React.

Ako aplikacija kasnije postane čisto poslovni desktop alat, može se razmotriti PySide6, ali tek nakon što Python backend postane stabilan.

Za sada: ne raditi full PySide6 rewrite.

