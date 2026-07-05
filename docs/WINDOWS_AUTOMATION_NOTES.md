# Windows automation notes — RileyJarvis Windows Hybrid

## Trenutno stanje (legacy, PowerShell u Electron-u)

Originalni RileyJarvis (macOS-only) je sve "computer-use" alate implementirao preko macOS-specifičnih shell komandi (`osascript`, `screencapture`, `open -a`). Windows port ih je zamijenio `powershell.exe` pozivima direktno u `electron/main.cjs` (vidi `WINDOWS-PORT-NOTES.md` u root-u projekta za pun opis):

| Alat | macOS (original) | Windows (legacy, sada) |
|---|---|---|
| `computer_open_app` | `open -a` | `Start-Process` |
| `computer_type_text` | AppleScript `keystroke` | `SendKeys` (sa escape-om za `+^%~(){}[]`) |
| `computer_press_key` | AppleScript key code | `SendKeys` (`{ENTER}`, `{TAB}`, `{ESC}`, `{DEL}`, strelice) |
| `computer_click` | AppleScript click | `user32.dll` P/Invoke (`SetCursorPos` + `mouse_event`) |
| `computer_scroll` | simulacija strelica | `mouse_event` sa wheel/hwheel signalom |
| `screen_snapshot` | `screencapture` | `System.Drawing` (cijeli virtuelni desktop, multi-monitor) |
| `ui_inspect` | AppleScript + Accessibility | `GetForegroundWindow`/`GetWindowText` + `Get-Process` |

Poznato ograničenje: `computer_open_app` (`Start-Process <name>`) radi samo za app-ove na `PATH` ili sa App Execution Alias-om (npr. `notepad`, `calc`, `mspaint`, `chrome`, `code`). Store-only app-ovi bez aliasa se možda neće otvoriti po imenu.

Ovaj legacy sloj **ostaje aktivan i ne smije se brisati** dok Python zamjena nije implementirana i testirana (FAZA 10, 12, 13), i dok se ne uključi feature flag za deaktivaciju (FAZA 16, `RICKY_USE_LEGACY_POWERSHELL_TOOLS`).

## Planirani Python sloj

### FAZA 10 — screenshot i active window

Predložene biblioteke: `mss`, `Pillow`, `psutil`, `pywinauto`.

`screen_snapshot` output:

```json
{
  "image_path": "data/screenshots/2026-07-04/uuid.png",
  "monitors": [
    { "index": 0, "x": 0, "y": 0, "width": 1920, "height": 1080 }
  ]
}
```

`ui_inspect` output:

```json
{
  "active_window": { "title": "Untitled - Notepad", "process": "notepad.exe", "pid": 1234 },
  "ui_tree_preview": []
}
```

U prvoj verziji `ui_tree_preview` može biti prazan ili minimalan — ne forsirati savršenu UIA inspekciju odmah.

### FAZA 12 — computer-use v1 (koordinate)

Toolovi: `computer_open_app`, `computer_type_text`, `computer_press_key`, `computer_click_coordinates`, `computer_scroll`.
Biblioteke: `pywinauto`, `pyautogui`, `psutil`.

Svi high-risk alati moraju proći permission check (vidi [SECURITY_MODEL.md](./SECURITY_MODEL.md)), logovati active window prije/poslije, i po mogućnosti napraviti screenshot before/after.

Minimalni ručni test: Notepad — otvori app, uključi computer mode, `computer_open_app notepad`, `ui_inspect`, `computer_type_text "Test from Python backend"`, provjeri tekst u Notepad-u, provjeri `tool_runs` log.

### FAZA 13 — computer-use v2 (element targeting)

Cilj: smanjiti oslanjanje na koordinate. Novi toolovi: `computer_find_elements`, `computer_click_element`, `computer_set_text_element`, `computer_get_element_text`, preko `pywinauto`/UIA. Coordinate click ostaje samo kao fallback.

Element target schema:

```json
{
  "app": "notepad.exe",
  "title_contains": "Untitled",
  "control_type": "Edit",
  "name": "Text Editor",
  "automation_id": "optional"
}
```

## Vidi i

- `WINDOWS-PORT-NOTES.md` (root projekta) — pun dnevnik macOS→Windows portovanja i poznatih bagova.
- [SECURITY_MODEL.md](./SECURITY_MODEL.md) — permission pravila za high/critical computer-use alate.
