# Agent Report — C2 (Chrome/Edge discovery + browser_tab_open)

- Datum: 2026-07-16
- Agent: pi
- Faza: C2 — browser discovery, browser_tab_open, guided install/pair za Tier 1

## Šta je urađeno

### 1. Browser discovery (`chromium_discovery.py`)
- **7 Chromium browsera**: Chrome, Edge, Brave, Vivaldi, Opera, Opera GX, Chromium
- Detekcija preko Windows registry `App Paths` ključeva (HKCU + HKLM)
- Fallback: poznate putanje (`%LOCALAPPDATA%`, `%PROGRAMFILES%`) + `shutil.which()`
- Detekcija postojećih profilnih direktorijuma
- Ne čita history/cookies/sadržaj — samo postojanje foldera
- **Aliasi**: `brejv→brave`, `edž→edge`, `hrom→chrome`, `opera gx→opera_gx`
- `GET /browser-bridge/browsers` — API endpoint

### 2. `browser_tab_open` — novi medium-risk alat
- Otvara URL kao novi tab u povezanom browser profilu
- Parametri: `browser`, `profile_id`, `url` (obavezan), `activate` (default true)
- URL validacija: apsolutni HTTP(S), bez embedded credentials
- Koristi `chrome.tabs.create` preko ekstenzije
- Routing: `_resolve_profile()` za odabir pravog profila
- Registrovan u:
  - `phase13.py` (risk=medium, no confirmation)
  - `realtimeToolSpecs.cjs`
  - `PHASE11_DELEGATED_TOOLS` u `electron/main.cjs`

### 3. Ekstenzija — `open_tab` komanda
- `handleOpenTab(requestId, {url, activate})` — poziva `chrome.tabs.create()`
- Vraća `tab_opened` sa tab_id, title, url
- Deduplikacija preko `requestId`

### 4. Broker — `open_tab` metoda
- `broker.open_tab(url, activate, browser, profile_id)` 
- Rutira na pravi profil, šalje `open_tab` ekstenziji
- Vraća strukturirani rezultat sa browser/profil informacijama

### 5. Testovi — 6 novih (ukupno 56)
- `test_browser_tab_open_is_listed` — provjera definicije
- `test_browser_tab_open_rejects_unsafe_url` — `file://` odbijen
- `test_browser_tab_open_rejects_embedded_credentials` — `user:pass@` odbijen
- `test_browser_tab_open_succeeds_with_mock` — mockovani poziv brokeru
- `test_browser_discovery_returns_known_browsers` — Tier 1 browseri prisutni
- `test_browser_normalize_aliases` — svi aliasi rade

## Fajlovi

### Novi
- `python_backend/app/services/chromium_discovery.py` — browser discovery servis

### Izmijenjeni
- `python_backend/app/api/browser_bridge.py` — `GET /browser-bridge/browsers`
- `python_backend/app/services/browser_extension_broker.py` — `open_tab()` metoda
- `python_backend/app/tools/system/browser_tabs.py` — `_handle_browser_tab_open` handler
- `python_backend/app/agent/tool_catalog/phase13.py` — `browser_tab_open` registracija
- `electron/core/realtimeToolSpecs.cjs` — `browser_tab_open` spec
- `electron/main.cjs` — `browser_tab_open` u PHASE11_DELEGATED_TOOLS
- `browser_extension/service-worker.js` — `handleOpenTab` handler
- `python_backend/tests/test_browser_tabs.py` — 6 novih testova

## Provjere
- `pytest tests/test_browser_tabs.py -q` → 56/56 PASSED
- TypeScript: čist
- Nema nove business logike u `electron/main.cjs`
