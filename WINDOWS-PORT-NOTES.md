# Windows port — šta je urađeno

Ovaj fajl dokumentuje sve izmjene napravljene da [RileyJarvis](https://github.com/rileybrown/rileyjarvis)
(originalno macOS-only Electron AI companion) radi na Windows-u, i sve
bagove koji su usput popravljeni. Vodi se kao referenca za dalji rad —
i za tebe i za kolege kojima podijeliš projekat.

## 1. Computer-use alati — macOS AppleScript → Windows PowerShell

Originalni `electron/main.cjs` je sve "computer-use" alate implementirao
preko macOS-specifičnih shell komandi (`osascript`, `screencapture`,
`open -a`), koje na Windows-u ne postoje. Svaki je prepravljen da radi
preko `powershell.exe` (već ugrađen u Windows, bez dodatnih instalacija):

| Alat | macOS (original) | Windows (sada) |
|---|---|---|
| `computer_open_app` | `open -a` | `Start-Process` |
| `computer_type_text` | AppleScript `keystroke` | `SendKeys` (sa ispravnim escape-om za `+^%~(){}[]`) |
| `computer_press_key` | AppleScript key code | `SendKeys` (`{ENTER}`, `{TAB}`, `{ESC}`, `{DEL}`, strelice) |
| `computer_click` | AppleScript click | `user32.dll` P/Invoke (`SetCursorPos` + `mouse_event`) |
| `computer_scroll` | simulacija strelica | `mouse_event` sa pravim wheel/hwheel signalom |
| `screen_snapshot` | `screencapture` | `System.Drawing` (hvata cijeli virtuelni desktop, multi-monitor) |
| `ui_inspect` | AppleScript + Accessibility | `GetForegroundWindow`/`GetWindowText` + `Get-Process` |

Sve PowerShell pozive pokreće nova `runPowerShell()` helper funkcija u
`electron/main.cjs`, preko `powershell.exe -ExecutionPolicy Bypass -Command ...`
skopirano na taj jedan poziv — ne mijenja sistemsku PowerShell politiku.

## 2. Bagovi otkriveni i popravljeni pri pokretanju

- **`npm run dev` nije radio na Windows-u.** Skripta je koristila Unix
  sintaksu za env varijablu (`VITE_DEV_SERVER_URL=... electron .`), koju
  `cmd.exe` ne razumije. Dodat `cross-env` paket (devDependency), skripta u
  `package.json` sad koristi `cross-env VITE_DEV_SERVER_URL=... electron .`.
- **Prozor se otvarao van vidljivog ekrana.** Pri prvom pokretanju, Electron
  prozor je znao da se pojavi na nevidljivoj poziciji (najvjerovatnije zbog
  kombinacije dva monitora sa različitim DPI skaliranjem — 125% i 100%).
  Popravljeno dodavanjem `win.center()` odmah nakon kreiranja prozora u
  `createWindow()` — sad se uvijek centrira na vidljivom ekranu.
- **Dodato opciono logovanje renderer konzole** (`RICKY_DEBUG_CONSOLE=1`
  env varijabla) — prosljeđuje `console-message` i mrežne greške iz
  browser dijela direktno u terminal. Mnogo pouzdanije za dijagnostiku od
  screenshot-ovanja i nagađanja koordinata klika.

## 3. UI dodaci

- **Dugme za zatvaranje (X).** Prozor je frameless (`frame: false`), pa
  nema standardni Windows X u naslovnoj traci. Dodato prilagođeno X dugme
  gore desno (`window-close-button` u `styles.css`), povezano preko novog
  `app:quit` IPC handler-a (`preload.cjs` → `main.cjs`).
- **Ispravljeno preklapanje sa "Hide" dugmetom** — desni padding u
  `.artifact-header` povećan sa 28px na 52px da X dugme i "Hide" dugme
  artifact panela imaju razmak.

## 4. Pokretanje i dijeljenje

- **`Pokreni-Ricky.bat`** — pokreće `npm run dev` duplim klikom, bez ručnog
  otvaranja terminala.
- **Desktop prečica** — `create-shortcut.ps1` + `Napravi-Precicu-Desktop.bat`
  prave "Ricky" prečicu na Desktopu (sa Electron ikonicom) koja gađa tačnu
  putanju foldera, gdje god da se on nalazi. Sigurno za ponovno pokretanje
  nakon premještanja foldera.
- **Priprema za dijeljenje sa kolegama** — `.env.local` (tvoji ključevi) i
  `node_modules` (instalira se lokalno) se nikad ne dijele. Kolega dobija
  zip, pokrene `npm install`, kopira `.env.example` u `.env.local` i upiše
  svoj OpenAI/Exa ključ.

## Poznata ograničenja / za dalje

- `computer_open_app` (`Start-Process <name>`) radi samo za app-ove koji
  su na `PATH` ili imaju App Execution Alias (npr. `notepad`, `calc`,
  `mspaint`, `chrome`, `code`). Store-only app-ovi bez aliasa se možda
  neće otvoriti po imenu.
- Ovo je i dalje dev-mode pokretanje (`npm run dev`), ne pravi instalabilni
  `.exe`. Za to bi trebalo `electron-builder` — poseban korak ako ikad
  zatreba prava distribucija bez foldera/terminala.
