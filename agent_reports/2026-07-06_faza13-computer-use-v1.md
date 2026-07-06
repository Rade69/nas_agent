# FAZA 13 — Computer-use Python v1 (koordinate)

## Datum

2026-07-06

## Scope

Implementirana je FAZA 13 iz `docs/MIGRATION_PLAN.md`: Python zamjena za legacy PowerShell computer-use alate (koordinate), plus active window enforcement u permission engine-u.

## Šta je urađeno

### `python_backend/app/tools/system/computer.py` (novi)

5 handlera koji 1:1 zamjenjuju legacy PowerShell alate iz `electron/tools_legacy/powershell/`:

- **`computer_open_app`** — `os.startfile()` sa `subprocess.Popen` fallback-om
- **`computer_type_text`** — `SendInput` + `KEYEVENTF_UNICODE` za svaki karakter, CR/LF → Enter
- **`computer_press_key`** — `SendInput` sa virtual-key kodovima za enter/tab/escape/delete/space/strelice, repeat 1-20
- **`computer_click`** — `SetCursorPos` + `mouse_event` (LEFTDOWN/LEFTUP)
- **`computer_scroll`** — `mouse_event` (WHEEL/HWHEEL), up/down/left/right, amount 1-20

Sve preko **čistog ctypes + Win32 API** — nula eksternih biblioteka.

### `permission_engine.py` — `check_active_window()` (novo)

- `_get_active_window_process()` — čita foreground window process name preko `user32.GetForegroundWindow()` + `GetWindowThreadProcessId` + `psutil`
- `check_active_window(tool)` — provjerava `requires_active_window_match`, `allowed_apps`, `blocked_apps`
- Case-insensitive matching
- Fail-closed: ako se ne može odrediti aktivni prozor → `ACTIVE_WINDOW_UNKNOWN`
- `blocked_apps` ima prioritet nad `allowed_apps`

### `tool_executor.py` — wire `check_active_window`

- Poziva se nakon `check_permission()`, prije `tool.handler()`
- Short-circuit: prvi error prekida lanac

### `tool_registry.py` — `_register_phase13_tools()`

- 5 toolova registrovano sa `requires_computer_mode=True`
- `computer_click` i `computer_type_text` → `risk="high"`
- `computer_open_app`, `computer_press_key`, `computer_scroll` → `risk="medium"`
- `_def` helper proširen sa `requires_active_window_match`, `allowed_apps`, `blocked_apps`

### `electron/core/legacyTools.cjs`

- 5 computer_* toolova premješteno iz `TOOLS_PENDING_PYTHON_EQUIVALENT` u `TOOLS_WITH_PYTHON_EQUIVALENT`
- `TOOLS_PENDING_PYTHON_EQUIVALENT` sad prazan

### `electron/main.cjs`

- 5 computer_* alata dodato u `PHASE11_DELEGATED_TOOLS`

### Testovi: `tests/test_phase13_computer_tools.py` (49 testova)

- 5 tool registration /tools listing
- 5 computer mode enforcement (svi fail bez computer_mode)
- 10 argument validation (missing required args, unsupported keys/directions)
- 4 `computer_open_app` handler tests (missing/empty appName, startfile, Popen fallback)
- 4 `computer_type_text` handler tests (missing/empty text, Unicode send count, newline → enter)
- 5 `computer_press_key` handler tests (missing/unsupported key, valid key, repeat, clamp)
- 3 `computer_click` handler tests (missing x/y, click sets position + fires mouse_event)
- 7 `computer_scroll` handler tests (missing/bad direction, 4 directions, amount clamp, min 1)
- 7 active window enforcement tests (no flag, no lists, non-Windows, blocked, not-allowed, allowed, case-insensitive)
- 2 regression tests (echo, note_add)

## Verifikacija

```text
pytest: 49/49 passed (novi testovi)
full suite: 172/172 passed (bez regresije)
typecheck: prošao
build: prošao
node --check: main.cjs + legacyTools.cjs clean
smoke: prošao
```

## Rizici/ograničenja

- **`computer_type_text` je sporiji od PowerShell `SendKeys`**: šalje jedan po jedan Unicode karakter preko `SendInput` (2 eventa po karakteru). PowerShell-ov `SendKeys` je batch operacija. Za MVP prihvatljivo; buduća optimizacija može grupisati INPUT strukture u jedan `SendInput` poziv.
- **Nema `Ctrl`/`Alt`/`Shift` modifiera**: `computer_press_key` podržava samo osnovne special keys. Modifier kombinacije (Ctrl+C, Alt+F4) nisu implementirane — treba poseban tool ili proširenje za FAZA 14+.
- **`computer_open_app` ne garantuje da se app otvorio**: vraća `ok` ako `startfile`/`Popen` ne baci exception; ne provjerava da li je proces zapravo startovan.