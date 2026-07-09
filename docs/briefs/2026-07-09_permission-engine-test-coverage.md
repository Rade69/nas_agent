# Pi brief — permission_engine.py test coverage (unit)

**Datum:** 2026-07-09
**Vlasnik plana:** Claude (planira + verifikuje). **Izvršilac:** pi.
**Tip:** Dodavanje testova — **NE mijenjati `permission_engine.py`** (karakterizacija postojećeg ponašanja).

## Cilj
Popuniti dvije stvarne rupe u `python_backend/tests/test_permission_engine.py`:
1. **`check_active_window()`** — trenutno **nema nijedan izolovani unit test** (security-kritičan fail-closed enforcement iz FAZA 13).
2. **`check_permission()` FAZA S-2 escalation grana** (`external_content_seen` → eskalira na confirmation) — nije direktno pokrivena.

## Pravila (obavezno)
1. **NE dirati `app/agent/permission_engine.py`** ni bilo koji drugi izvorni fajl. Samo dodaješ testove u `python_backend/tests/test_permission_engine.py` (ili novi `test_permission_active_window.py` ako je čišće).
2. **Karakterizacija:** testovi opisuju **stvarno trenutno ponašanje** — pokreni kod, potvrdi šta vraća, zapiši to. Ako neki test ne prolazi protiv postojećeg koda → to je nalaz za mene (upiši u "Found issues"), **NE mijenjaj izvor da test prođe**.
3. **Determinizam:** `_get_active_window_process()` zove Win32 API i zavisi od foreground prozora → **monkeypatch-uj ga**: `monkeypatch.setattr("app.agent.permission_engine._get_active_window_process", lambda: "powershell.exe")` (ili `lambda: None` za fail-closed slučaj). Testovi moraju proći cross-platform (i na ne-Windows CI).
4. Pytest mora ostati zelen: `cd python_backend && python -m pytest -q` — postojeći testovi + novi svi prolaze.
5. **Ne duplirati** `test_tool_executor_permission.py` (on testira kroz `ToolExecutor` — integracija). Ovdje pišeš **izolovane unit** testove direktno na `check_active_window`/`check_permission`.
6. **Ne commitovati** — javi kad završiš, Claude verifikuje.

## Priprema (pi uradi prvo)
- Pročitaj `app/schemas/tool.py` i potvrdi TAČNA imena/defaulte polja: `requires_active_window_match`, `allowed_apps`, `blocked_apps`, `reads_external_content`, `requires_computer_mode`, `risk`. Postojeći `low_risk_tool(**overrides)` helper u test fajlu je šablon — proširi ga preko `overrides` (ne diraj mu default).
- Pročitaj `check_active_window()` (permission_engine.py:62–103) i `check_permission()` S-2 blok (permission_engine.py:123–128) da testovi tačno odgovaraju granama i error kodovima.

## Testovi za `check_active_window` (7)
Uvezi `from app.agent.permission_engine import check_active_window`. Tool se pravi preko `low_risk_tool(...)` sa odgovarajućim overrides.

| # | Setup | Očekivano |
|---|---|---|
| 1 | `requires_active_window_match=False` (default) | vraća `None` (rani izlaz, active window se i ne pita) |
| 2 | `requires_active_window_match=True`, `allowed_apps=[]`, `blocked_apps=[]` | vraća `None` (nema šta da enforce-uje) |
| 3 | `requires_active_window_match=True`, `blocked_apps=["powershell.exe"]`, monkeypatch process→`"powershell.exe"` | `AppError`, `code == "ACTIVE_WINDOW_BLOCKED"` |
| 4 | isto kao #3 ali monkeypatch process→`"POWERSHELL.EXE"` (velika slova) | `ACTIVE_WINDOW_BLOCKED` (case-insensitive match — dokazuje `.lower()` poređenje) |
| 5 | `requires_active_window_match=True`, `allowed_apps=["notepad.exe"]`, monkeypatch process→`"chrome.exe"` | `AppError`, `code == "ACTIVE_WINDOW_NOT_ALLOWED"` |
| 6 | isto kao #5 ali monkeypatch process→`"notepad.exe"` | vraća `None` (dozvoljen) |
| 7 | `requires_active_window_match=True`, `blocked_apps=["x.exe"]`, monkeypatch process→`None` | `AppError`, `code == "ACTIVE_WINDOW_UNKNOWN"` (**fail-closed** — ovo je najvažniji test) |

## Testovi za `check_permission` S-2 escalation (4)
Koristi postojeći `make_request(**context_overrides)` — treba mu `external_content_seen` u `ToolExecutionContext` (provjeri ime polja u schema). Koristi `make_confirmations(tmp_path)`.

| # | Setup | Očekivano |
|---|---|---|
| 8 | tool `risk="medium"`, `reads_external_content=False`, `requires_confirmation=False`; request `external_content_seen=True`, bez `confirmation_id` | eskalira → `AppError` `code == "CONFIRMATION_REQUIRED"` |
| 9 | tool `risk="low"`, `reads_external_content=True`; request `external_content_seen=True` | **NE** eskalira → `None` (čitači su izuzeti, ne zaključavaju sami sebe) |
| 10 | tool `risk="low"`, `requires_computer_mode=True`, `reads_external_content=False`; request `external_content_seen=True`, `computer_mode=True`, bez `confirmation_id` | eskalira → `CONFIRMATION_REQUIRED` (computer-mode tool escalated) |
| 11 | tool `risk="medium"`, `reads_external_content=False`; request `external_content_seen=False` | **NE** eskalira → `None` (baseline: bez viđenog eksternog sadržaja nema eskalacije) |

> Napomena za #10: ako `requires_computer_mode=True` traži `computer_mode=True` u kontekstu da ne padne ranije na `COMPUTER_MODE_REQUIRED`, postavi ga — cilj je izolovati S-2 granu, ne computer-mode gate.

## Acceptance (pi provjeri prije nego javi)
- 11 novih testova (7 active-window + 4 S-2), svi zeleni.
- `python -m pytest -q` ukupno zeleno (postojeći + novih 11).
- `permission_engine.py` i svaki drugi izvor **nepromijenjen** (`git diff --stat` pokazuje samo test fajl).
- Svaki test monkeypatch-uje `_get_active_window_process` gdje dira active window (nema stvarnog Win32 poziva u testu).

## Izvještaj
`agent_reports/2026-07-09_pi-permission-engine-test-coverage.md`: lista dodatih testova, `pytest` izlaz (broj prije/poslije), potvrda "permission_engine.py nepromijenjen", "Found issues" ako neki test otkrije neočekivano ponašanje. **NE commitovati** — čeka Claude pregled.
