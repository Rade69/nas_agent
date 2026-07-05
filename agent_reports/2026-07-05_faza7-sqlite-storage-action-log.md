# FAZA 7 - SQLite storage i action log

## Datum

2026-07-05

## Scope

Implementirana je samo FAZA 7 iz `docs/MIGRATION_PLAN.md`: SQLite storage inicijalizacija sa MVP voice-first tabelama i `tool_runs` action log za Python tool execution.

Nije implementirana FAZA 6. Nisu dodavani realtime endpointi. Nisu dodavani novi storage REST endpointi. Nije diran Electron bridge osim ranije postojećih FAZA 5 fajlova.

## GitNexus impact

GitNexus nije prepoznao nove Python simbole iz FAZA 4/5 (`ToolExecutor`, `create_app`, `Settings`) kao direktne targete u trenutnom indeksu, pa je urađena ručna blast-radius analiza.

Ručni blast radius:

- `python_backend/app/main.py`: minimalna izmjena za `initialize_database(settings)` i `app.state.action_log`; bez novog routera, da se izbjegne konflikt sa Claude FAZA 6 radom.
- `python_backend/app/api/tools.py`: executor dobija opcioni `ActionLogService` iz app state-a.
- `python_backend/app/agent/tool_executor.py`: success/failure response se loguje u `tool_runs`.
- `python_backend/app/core/config.py`: dodan `data_dir` i `database_path`.
- Novi storage/service moduli su izolovani pod `python_backend/app/storage/` i `python_backend/app/services/`.

## Šta je urađeno

- Dodan SQLite storage sloj:
  - `python_backend/app/storage/db.py`
  - `python_backend/app/storage/repositories/tool_run_repo.py`
- Dodan service sloj za action log:
  - `python_backend/app/services/action_log.py`
- Dodane MVP tabele:
  - `settings`
  - `realtime_sessions`
  - `voice_turns`
  - `transcripts`
  - `activity_events`
  - `confirmations`
  - `plans`
  - `plan_steps`
  - `tool_runs`
  - `artifacts`
- `ToolExecutor` sada loguje:
  - uspješan `echo` execution
  - nepoznat tool
  - disabled tool
  - invalid arguments
- Dopunjen `.gitignore` za `python_backend/data/*.sqlite` i `python_backend/data/*.db`.
- Dodani testovi:
  - `tests/test_storage.py`
  - `tests/test_action_log.py`

## Zašto je urađeno

FAZA 7 uvodi lokalnu perzistenciju i audit trail kao temelj za kasnije voice turns, activity timeline, confirmations, plans i tool execution sigurnost. Ovo je urađeno prije migracije realnih toolova, da svaki budući Python tool ima već spreman logging kanal.

## Kako je urađeno

Korišten je Python standardni `sqlite3`, bez nove dependency. Baza se inicijalizuje pri `create_app()` kroz `initialize_database(settings)`. Default lokacija je:

```text
python_backend/data/ricky.sqlite
```

Testovi koriste `tmp_path` i ne zavise od lokalne dev baze.

## Šta nije dirano

- Nije diran `src/lib/realtime.ts`.
- Nije implementiran FAZA 6 realtime session endpoint.
- Nije dodan novi router u `main.py`.
- Nisu dodani frontend ili Electron IPC endpointi za storage.
- Nisu migrirani legacy PowerShell toolovi.
- Nije implementiran permission/risk layer iz FAZE 10.
- Nije implementirana FAZA 8/9 UI logika.

## Verifikacija

Pokrenuto:

```text
python -m pytest
node -e "...startPythonBackend({isPackaged:false})...stopPythonBackend()..."
npm run build
```

Rezultati:

```text
pytest: 8 passed, 1 warning
Node smoke: backend startovao, /health vratio 200, SQLite init prošao, backend stop
npm run build: prošao
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation warning.

## Rizici/ograničenja

- `main.py` je zajednička tačka sa Claude FAZA 6 radom. Ovdje nije dodat novi router; promjena je ograničena na DB init i action log service state.
- SQLite šema je MVP i nema migracioni framework; koristi `CREATE TABLE IF NOT EXISTS`.
- `tool_runs` za sada loguje Python toolove iz backend executor-a, ne legacy Electron/PowerShell toolove.
- Nema redaction sloja; to pripada kasnijim security fazama.

## Potreban follow-up

- FAZA 6 treba pažljivo merge-ovati svoje router/state izmjene u `main.py`.
- FAZA 8/9 mogu koristiti postojeće tabele za transcripts/activity/plans, ali treba dodati specifične repository/service module kad se implementiraju ti tokovi.
- FAZA 10/Security Gate treba dodati redaction i permission/risk policy prije high-risk toolova.

## Potrebna korisnička potvrda

Prije commita treba potvrditi šta ulazi u commit, jer worktree već sadrži postojeće dokumentacione i Electron izmjene koje nisu dio ove FAZE 7.