# Agent report — permission_engine.py unit test coverage (R2d)

**Datum pisanja:** 2026-07-09
**Brief:** `docs/briefs/2026-07-09_permission-engine-test-coverage.md`
**Izvršilac:** pi · **Vlasnik plana:** Claude (verifikuje).
**Tip:** Dodavanje unit testova — **nula izmjena produkcijskog koda**.
`permission_engine.py` netaknut; samo `test_permission_engine.py` proširen sa 11 testova.

## Scope

Dodata izolovana unit test pokrivenost za dvije stvarne rupe u testovima
`permission_engine.py`:

1. **`check_active_window()`** — 7 testova
2. **`check_permission()` S-2 escalation grana** (`external_content_seen`) — 4 testa

### Prije
- 11 testova u `test_permission_engine.py` (199 ukupno)
- `check_active_window`: **0 izolovanih unit testova** (samo indirektno kroz `test_tool_executor_permission.py` integraciju)
- S-2 `external_content_seen` eskalacija: **0 direktnih testova**

### Poslije
- 22 testa u `test_permission_engine.py` (210 ukupno)
- `check_active_window`: **7 izolovanih unit testova** (pokriveni svi error kodovi + fail-closed)
- S-2: **4 testa** (pokriveni: eskalacija medium toola, čitači izuzeti, computer-mode eskalacija, baseline bez externog sadržaja)

## Dodati testovi

### `check_active_window` (7 testova — fail-closed enforcement iz FAZA 13)

| # | Test | Setup (overrides + monkeypatch) | Očekivano | Rez.
| --- | --- | --- | --- | --- |
| 1 | `test_active_window_skips_when_flag_false` | `requires_active_window_match=False` (default) | `None` ✗ | **PASS** |
| 2 | `test_active_window_skips_when_no_lists` | `requires_active_window_match=True`, `allowed=[]`, `blocked=[]` | `None` | **PASS** |
| 3 | `test_active_window_blocked_exact_match` | `blocked=["powershell.exe"]`, monkeypatch→`"powershell.exe"` | `ACTIVE_WINDOW_BLOCKED` | **PASS** |
| 4 | `test_active_window_blocked_case_insensitive` | isto, monkeypatch→`"POWERSHELL.EXE"` | `ACTIVE_WINDOW_BLOCKED` | **PASS** |
| 5 | `test_active_window_not_allowed` | `allowed=["notepad.exe"]`, monkeypatch→`"chrome.exe"` | `ACTIVE_WINDOW_NOT_ALLOWED` | **PASS** |
| 6 | `test_active_window_allowed` | `allowed=["notepad.exe"]`, monkeypatch→`"notepad.exe"` | `None` | **PASS** |
| 7 | `test_active_window_unknown_fail_closed` 🔐 | `blocked=["x.exe"]`, monkeypatch→`None` | `ACTIVE_WINDOW_UNKNOWN` | **PASS** |

Svi testovi monkeypatch-uju `app.agent.permission_engine._get_active_window_process`
→ nema stvarnog Win32 poziva, testovi su cross-platform (prolazili bi i na ne-Windows CI).

### `check_permission` S-2 escalation (4 testa — prompt-injection containment)

| # | Test | Setup | Očekivano | Rez. |
| --- | --- | --- | --- | --- |
| 8 | `test_external_content_escalates_medium_tool` | `risk="medium"`, `reads_external_content=False`, `requires_confirmation=False`; kontekst `external_content_seen=True` | `CONFIRMATION_REQUIRED` | **PASS** |
| 9 | `test_external_content_does_not_escalate_readers` | `risk="low"`, `reads_external_content=True`; `external_content_seen=True` | `None` (čitači izuzeti) | **PASS** |
| 10 | `test_external_content_escalates_computer_mode_tool` | `risk="low"`, `requires_computer_mode=True`, `reads_external_content=False`; `external_content_seen=True`, `computer_mode=True` | `CONFIRMATION_REQUIRED` | **PASS** |
| 11 | `test_external_content_no_escalation_when_not_seen` | `risk="medium"`, `reads_external_content=False`; `external_content_seen=False` | `None` (baseline) | **PASS** |

## Verifikacija (acceptance criteria iz briefa)

| Kriterij | Očekivano | Dobiveno |
| --- | --- | --- |
| 11 novih testova (7+4) | 11 | ✓ 11 |
| svi 22 zeleni | ✓ | **22 passed** ✓ |
| `python -m pytest -q` ukupno zeleno | ✓ | **210 passed, 1 warning** ✓ (199 + 11) |
| `git diff --stat` samo test fajl | ✓ | `test_permission_engine.py` (+168/-1) |
| `permission_engine.py` nepromijenjen | ✓ | 0 izmjena u izvornom kodu |
| monkeypatch na `_get_active_window_process` | 0 Win32 poziva | ✓ svih 7 active-window testova monkeypatch-uje |

### pytest izlaz (finalni)
```
tests/test_permission_engine.py::test_active_window_skips_when_flag_false PASSED
... (svih 11 novih) ...
tests/test_permission_engine.py::test_external_content_no_escalation_when_not_seen PASSED

=== 22 passed in 6.30s ===

Full suite: 210 passed, 1 warning in 26.46s
```

## Fajlovi dirani

- `python_backend/tests/test_permission_engine.py` — modifikovan: dodat import
  `check_active_window` i `AppError`; dodana 2 sekcije sa 11 testova (+168 ln).
- `python_backend/app/agent/permission_engine.py` — **netaknut** (0 izmjena).

## Karakterizacija: zapaženo ponašanje

Svi testovi prolaze protiv postojećeg koda — ponašanje `check_active_window` i
S-2 grane je u skladu sa očekivanjima iz briefa:

- `check_active_window` fail-closed (return `None` iz `_get_active_window_process`
  → `ACTIVE_WINDOW_UNKNOWN`) ✓
- Case-insensitive poređenje (`process_name.lower() in (... for a in blocked_apps)`) ✓
- Blokirani imaju prednost nad dozvoljenim (`blocked_apps` provjera prije `allowed_apps`) ✓
- S-2: medium risk + `external_content_seen` + NOT reader → eskalira ✓
- S-2: reader alat (reads_external_content=True) → **ne eskalira sam sebe** ✓
- S-2: computer-mode tool (requires_computer_mode) → eskalira ✓
- S-2: baseline bez `external_content_seen` → normalno ponašanje ✓

## Found issues (brief sekcija — NE popravljati)

- (prazno) — nijedan test nije otkrio neočekivano ponašanje. Postojeći kod se
  ponaša tačno kako brief predviđa. Nema neslaganja između dokumentovane i
  stvarne logike.

## Commit

**Nije komitovan** — čeka Claude pregled (brief: "Ne commitovati — javi kad
završiš, Claude verifikuje").

## Potrebna korisnička potvrda (Claude)

1. `python -m pytest -q` sam → 210 passed (ja potvrdio).
2. `git diff --stat` → samo `test_permission_engine.py` dodirnut; `permission_engine.py`
   netaknut (ja potvrdio).
3. Spot-check: pročitaj 1-2 nova testa da potvrdiš da monkeypatch tačno targetira
   `_get_active_window_process` i da stub-ovi ne pozivaju Win32 API.
4. Gotovo — 210 passed, nula izmjena produkcijskog koda.
