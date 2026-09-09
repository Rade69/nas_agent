# QM-1 — Process bridge (Qt ↔ Python backend)

## Datum

2026-09-09

## Scope

QM-1 iz `docs/QT_MIGRATION_PLAN_2026-07-20.md` — Qt shell pokreće, nadzire i bezbjedno komunicira sa `python_backend/` kao zasebnim procesom (Opcija A, §2.1). Zamjena za `electron/services/pythonProcess.cjs` + `pythonClient.cjs` auth mehaniku, u Pythonu.

## GitNexus impact

GitNexus MCP alati nisu dostupni u ovom okruženju. Ručna analiza: **čisto aditivna promjena**. Novi fajlovi isključivo u `desktop/` (novi sloj), plus proširenje `desktop/main.py` (`--backend` grana). `python_backend/`, `electron/`, `src/` netaknuti — 0% izmjena postojećeg koda. Jedini dodir sa postojećim sistemom je `desktop/main.py` koji pri pokretanju `--backend` dodaje `python_backend/` na `sys.path` i importuje `app.main` (read-only, bez izmjene). Rizik ~nula, nema HIGH/CRITICAL.

## Šta je urađeno

1. **`desktop/core/process_bridge.py`** — `BackendProcess` (spawn, Job Object, health, stop) + `BackendClient` (httpx sa Bearer) + `generate_session_token()` + `find_free_port()`.
2. **`desktop/core/win_job_object.py`** — Windows Job Object sa `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` preko ctypes-a (nula zavisnosti od pywin32), no-op na non-Windows.
3. **`desktop/main.py`** — proširen sa `--backend` granom (`run_backend()` importuje `app.main` i pokreće uvicorn na `settings.host/port`); `create_app`/`run_qt` razdvojeni radi testabilnosti.
4. **`desktop/__main__.py`** — omogućava `python -m desktop --backend` (dev spawn put).
5. **Testovi** — `desktop/tests/test_process_bridge.py` (10 testova) + `conftest.py` (sys.path + `integration` marker).

## Zašto je urađeno

Electron shell će biti uklonjen (QM-9), pa njegov process manager mora imati Qt/Python ekvivalent. Ključne odluke iz FABLE-5 review-a ugrađene od dana jedan: (a) spawn je frozen-safe — `sys.executable --backend`, nikad hardkodiran `"python"`; (b) gašenje djeteta garantuje OS kernel preko Job Object-a, ne `atexit` (koji se ne izvršava pri crash-u/End task-u).

## Kako je urađeno

- **Token:** `secrets.token_bytes(32).hex()` (64 hex, isto entropije kao Electron `randomBytes(32).hex()`), proslijeđen isključivo kroz `RICKY_LOCAL_TOKEN` env — test potvrđuje da se NE pojavljuje u command line args.
- **Spawn:** `_build_command()` grana na `sys.frozen` → `[sys.executable, "--backend"]` (frozen) / `[sys.executable, "-m", "desktop", "--backend"]` (dev); `cwd=repo_root`, env `RICKY_HOST/RICKY_PORT/RICKY_DATA_DIR/PYTHONUNBUFFERED`.
- **Job Object:** job kreiran, KILL_ON_JOB_CLOSE postavljen, proces dodijeljen, handle se čuva otvorenim dok backend živi; `stop()` zatvara handle → kernel ubija dijete. `atexit.register(self.stop)` kao dodatni sloj (uredno gašenje Qt-a). `terminate()`/`kill()` fallback za non-Windows.
- **Health:** `_wait_for_health()` poll-uje `GET /health` (sa Bearer) do timeout-a; rani izlaz ili timeout dižu `BackendProcessError` (fail-closed), stdout se drain-uje u background niti (izbjegava pipe deadlock).

## Šta nije dirano

- `python_backend/` — netaknut (0 izmjena), kako zahtijeva plan §3.1.
- `electron/services/pythonProcess.cjs` / `pythonClient.cjs` — netaknuti (ostaju dok Qt ne zamijeni Electron u QM-9).
- living-parent polling — namjerno izostavljen: redundantan na Windows-u uz Job Object, a dirao bi `python_backend/`; dodaje se tek u QM-9b/c (non-Windows) ako zatreba.

## Verifikacija

- `python -m pytest desktop/tests/test_process_bridge.py -m "not integration"` → **9 passed** (token/port/cmdline/env/fail-closed/Job Object dummy-proces test).
- `python -m pytest desktop/tests/test_process_bridge.py::test_backend_start_and_stop` → **1 passed** (stvarni backend spawn preko `python -m desktop --backend`, health OK, stop → psutil potvrđuje da proces ne postoji).
- Job Object dokazan: dummy `python -c "time.sleep(30)"` proces ubijen samim zatvaranjem job handle-a (bez `terminate()`).

## Rizici/ograničenja

- **Frozen-spawn test nije moguć u dev okruženju** — `sys.executable --backend` grana se može stvarno provjeriti tek sa PyInstaller build-om (QM-8). Mehanizam je pripremljen, ne i end-to-end dokazan.
- Job Object ctypes strukture su 64-bit pretpostavke (`c_size_t` za SIZE_T/ULONG_PTR); na 32-bit Windows bi mogle biti pogrešne — nije relevantno (cilj je 64-bit desktop).
- `init_broker` (browser bridge WebSocket na portu 9119) se i dalje pokreće pri backend startup-u — ako je port zauzet, backend start može puknuti; pre-postojeće ponašanje, ne QM-1 regresija.

## Potreban follow-up

- QM-2 — Companion orb integracija (`desktop/ui/orb.py` iz `spikes/pyside6_orb_spike.py`, ožičen na stvarni VoiceState).
- QM-8 — potvrditi frozen `--backend` spawn na čistoj mašini bez Python interpretera.

## Potrebna korisnička potvrda

- Ništa hitno. QM-2 (Companion orb) je po planu moj prvi prolaz integracije (portovanje spike-a), pi može raditi kontekst meni/lokalizaciju nakon toga.
