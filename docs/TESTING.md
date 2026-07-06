# Testing — RileyJarvis Windows Hybrid

> **Posljednje ažuriranje:** FAZA 18 / 2026-07-06
> **Povezano:** `docs/MIGRATION_PLAN.md`, `CLAUDE.md`

---

## Brzi start

```bash
# Pokreni sve provjere (typecheck + syntax check + build + pytest + smoke)
npm run quality

# Samo Python backend testovi
cd python_backend && python -m pytest

# Samo TypeScript typecheck
npm run typecheck

# Samo Electron syntax check
npm run check

# Samo smoke test (zahtijeva instaliran Python backend)
npm run smoke
```

---

## Struktura testova

### Python backend (`python_backend/tests/`)

| Fajl | Šta pokriva | Broj testova | Faza |
|------|-------------|-------------|------|
| `test_health.py` | `/health` endpoint | 1 | FAZA 4 |
| `test_tools.py` | `/tools`, `/tools/execute` (echo tool) | 2+ | FAZA 4 |
| `test_storage.py` | SQLite inicijalizacija + `tool_runs` logging | 2 | FAZA 7 |
| `test_action_log.py` | `ActionLogService` + `ToolRunRepository` | 2 | FAZA 7 |
| `test_realtime.py` | `/realtime/session` endpoint | 2+ | FAZA 6 |
| `test_confirmations.py` | Confirmation lifecycle (create/approve/reject/pending/idempotent) | 8 | FAZA 9 |
| `test_plans.py` | Plan/PlanStep CRUD + status transitions | 7 | FAZA 9 |
| `test_permission_engine.py` | FAZA 10 permission checks (`COMPUTER_MODE_REQUIRED`, `CONFIRMATION_REQUIRED`) | 5+ | FAZA 10 |
| `test_cancellation.py` | `CancellationRegistry` (execution_id lifecycle) | 3+ | FAZA 10 |
| `test_tool_executor_permission.py` | `ToolExecutor` + permission engine integracija | 3+ | FAZA 10 |
| `test_auth.py` | Security PR-1 local auth token (fail-open, 401, 200) | 6 | Security PR-1 |
| `test_agent_runtime.py` | `LocalDesktopAssistant` (agent runtime) | 6 | FAZA 15 |
| `test_phase11_tools.py` | Notes, records, artifacts, screenshot, ui_inspect + events bridge | 13 | FAZA 11 |
| `test_phase16_integrations.py` | web_search, image_generate integracije | 7 | FAZA 16 |
| `test_schemas.py` | Schema edge-case validacija | 5+ | FAZA 18 |
| `test_events.py` | `/events` endpoint edge-case | 3+ | FAZA 18 |

### Electron smoke test (`scripts/smoke-test.cjs`)

- Pokreće Python backend
- Provjerava `/health`
- Provjerava `/tools` (svi registrovani toolovi)
- Izvršava `echo` i `note_add` testne pozive
- Provjerava `/events` (backend.ready + cursor)
- Gasi backend i provjerava da više ne odgovara
- Vraća exit code 0 (sve prošlo) ili 1 (greška)

### Frontend (React/TypeScript)

- `npm run typecheck` (`tsc --noEmit`) — provjerava sve TypeScript fajlove
- `npm run build` — Vite + rolldown produkcijski build (automatski u `npm run quality`)

---

## Pokretanje pojedinačnih testova

```bash
# Svi Python testovi
cd python_backend && python -m pytest -v

# Jedan fajl
cd python_backend && python -m pytest tests/test_tools.py -v

# Jedan test
cd python_backend && python -m pytest tests/test_tools.py::test_execute_echo_tool -v

# Sa --tb=short za kraći traceback
cd python_backend && python -m pytest -q --tb=short
```

---

## Quality gate pipeline

`npm run quality` izvršava redom:

```
1. npm run typecheck  → tsc --noEmit
2. npm run check      → node --check za electron/*.cjs fajlove
3. npm run build      → tsc --noEmit && vite build
4. npm run test       → python -m pytest -q (backend testovi)
5. npm run smoke      → node scripts/smoke-test.cjs (end-to-end)
```

Ako bilo koji korak faila, pipeline se zaustavlja (`&&` chain).

---

## Pre-commit checklist

Prije svakog commit-a (per `CLAUDE.md`):

1. `npm run typecheck` — TypeScript čist
2. `npm run check` — Electron syntax čist
3. `npm run build` — build prolazi
4. `cd python_backend && python -m pytest -q` — svi backend testovi prolaze
5. `node scripts/smoke-test.cjs` — end-to-end smoke prolazi (ako su dirani backend/Electron fajlovi)
6. `npx gitnexus detect-changes --scope compare --base-ref <ref> --repo nas_agent` — validacija blast radius-a
7. `npx gitnexus analyze` — osvježi indeks

---

## CI pipeline prijedlog (GitHub Actions)

```yaml
name: Quality Gate

on: [push, pull_request]

jobs:
  backend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e python_backend/
      - run: pip install httpx python-dotenv
      - run: cd python_backend && python -m pytest -q

  frontend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
      - run: npm run typecheck
      - run: npm run check
      - run: npm run build
```

---

## Poznati problemi

1. **FastAPI/Starlette `TestClient` deprecation warning** — `httpx` vs `httpx2`. Ne utiče na funkcionalnost, planirano za update kad `httpx2` bude stabilan.
2. **`pytest` upozorenje o `PYTHONPATH`** — riješeno kroz `pyproject.toml` (`[tool.pytest.ini_options] pythonpath = ["."]`).
3. **Smoke test zahtijeva instaliran Python backend** — `npm run smoke` falluje ako `uvicorn`/`fastapi` nisu instalirani. Pokreće se samo u `npm run quality` nakon `npm run test` (koji bi failovao ranije).
4. **`assets/Ricky-agent.png`** — `git` ga prikazuje kao `M` (modified) zbog CRLF konverzije. Nije stvarni diff.
