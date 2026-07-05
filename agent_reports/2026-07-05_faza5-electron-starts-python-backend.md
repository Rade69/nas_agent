# FAZA 5 - Electron pokreće Python backend

## Datum

2026-07-05

## Scope

Implementirana je samo FAZA 5 iz `docs/MIGRATION_PLAN.md`: Electron u dev modu pokreće Python backend, čeka `/health`, forwarduje backend logove u terminal i gasi backend na app quit.

Nije implementirana FAZA 6. Nije mijenjan Realtime token/security tok. Nije mijenjan `src/lib/realtime.ts`. Nisu migrirani realni toolovi.

## GitNexus impact

Prije izmjene je pokušano GitNexus impact/context nad relevantnim postojećim lifecycle simbolima:

- `prepareWindowData` u `electron/main.cjs`: risk `LOW`, `affected_processes: []`.
- file-level target `electron/main.cjs` i `registerIpcHandlers` nisu bili dostupni kao direktni GitNexus targeti u trenutnom indeksu.

Ručni blast radius: izmjena dodaje dva nova modula u `electron/services/` i minimalno kači `startPythonBackend` / `stopPythonBackend` u Electron lifecycle. Postojeći renderer, `src/lib/realtime.ts`, legacy PowerShell toolovi i tool handler ponašanje nisu mijenjani u okviru ove faze.

## Šta je urađeno

- Dodan `electron/services/pythonClient.cjs`:
  - `GET /health`
  - `GET /tools`
  - `POST /tools/execute`
  - timeout/error handling za backend requestove.
- Dodan `electron/services/pythonProcess.cjs`:
  - resolve `python_backend/` putanje
  - preferira `.venv/Scripts/python.exe` ako postoji, inače `python`
  - startuje `python -m uvicorn app.main:app --host 127.0.0.1 --port 8765`
  - čeka `/health`
  - forwarduje stdout/stderr sa `[python-backend]` prefiksom
  - gasi child process na quit
  - reuse postojeći backend ako je `/health` već dostupan.
- `electron/main.cjs` lifecycle dopunjen:
  - start backend-a nakon `app.whenReady()`
  - terminal error ako backend ne startuje
  - prozor se i dalje otvara da postojeći UI tok ne bude blokiran
  - `before-quit` za stop backend-a.
- `docs/MIGRATION_PLAN.md` tracker red za FAZU 5 označen kao urađen.

## Zašto je urađeno

FAZA 5 treba da poveže Electron lifecycle sa Python backend skeletonom iz FAZE 4 bez migracije stvarnih toolova i bez ulaska u Realtime/session security iz FAZE 6.

## Kako je urađeno

Backend process manager koristi `child_process.spawn` bez shell-a i hardkodovan dev command za Uvicorn. HTTP client koristi lokalni `127.0.0.1:8765` backend URL i kratak timeout. Ako backend već radi, proces manager ga ne duplira nego ga označi kao external/reused.

## Šta nije dirano

- Nije diran `src/lib/realtime.ts`.
- Nije diran renderer UI.
- Nije dodan novi preload API.
- Nije dodan novi model-facing tool.
- Nije dodan arbitrary shell execution.
- Nisu migrirani PowerShell toolovi.
- Nije implementiran permission/risk layer.
- Nije implementiran Realtime credential endpoint iz FAZE 6.

## Verifikacija

Pokrenuto:

```text
node -e "...startPythonBackend({isPackaged:false})...stopPythonBackend()..."
python -m pytest
npm run build
```

Rezultati:

```text
Node smoke: backend startovao, /health vratio 200, status running, potom stop; port 8765 poslije toga nije radio.
pytest: 4 passed, 1 warning
npm run build: prošao
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation warning za trenutni dependency lanac.

## Rizici/ograničenja

- Backend dependency install je ranije urađen u globalni Python 3.14 environment, ne u lokalni `.venv`.
- Ako Python/FastAPI dependencies nisu instalirani na drugoj mašini, FAZA 5 će jasno ispisati backend start grešku u terminalu, ali neće blokirati UI.
- `electron/main.cjs` je već bio dirty zbog FAZE 3/tuđih izmjena; ovaj report opisuje samo FAZA 5 dodatke.
- Security Gate 0 još nije zatvoren; backend za sada nema auth token jer to nije acceptance criteria FAZE 5.

## Potreban follow-up

- FAZA 6 je rezervisana za Claude Code i treba premjestiti Realtime session credential minting u Python backend.
- Kasnije u Security PR-1 dodati backend local auth/token dizajn i self-test skeleton.
- Poželjno je kreirati lokalni `.venv` i koristiti ga za backend dependencies prije šireg testiranja.

## Potrebna korisnička potvrda

Prije commita treba potvrditi šta ulazi u commit, jer worktree sadrži postojeće dokumentacione i Electron izmjene koje nisu nastale u ovoj FAZI 5.