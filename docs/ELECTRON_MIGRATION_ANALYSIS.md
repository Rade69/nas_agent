# Electron Migration Analysis — RileyJarvis Windows Hybrid

**Datum:** 2026-07-26  
**Autor:** Claude Code  
**Svrha:** Detaljna analiza preostalog koda u `electron/` nakon završetka FAZA 0–19 migracionog plana — šta je migrirano, šta je ostalo, šta je svjesno zadržano, i koji su konkretni koraci za finalno čišćenje.

---

## 1. Pregled (Executive Summary)

Migracioni plan (FAZA 0–19) je završen — **sve numerisane faze su ✅ urađeno**. Python backend posjeduje agent runtime, tool registry, permission/risk engine, SQLite storage, sve AI integracije, i sve computer-use alate. Electron shell je sveden na IPC most i app lifecycle menadžera.

**Međutim**, `electron/` direktorijum i dalje sadrži ~4.190 linija koda, od čega:

| Kategorija | Linija | % |
|---|---|---|
| **Legacy tool fallback (mrtvi/dead code, nepozivan)** | ~730 (legacyMedia.cjs) | 17% |
| **Legacy PowerShell toolovi (neaktivni, LEGACY_FLAG=0)** | ~201 | 5% |
| **Legacy JSON DB (parcijalno neaktivan)** | ~92 | 2% |
| **Realtime tool specifikacije (potrebne, data-only)** | ~498 | 12% |
| **Companion orb (aktivan, treba da ostane)** | ~309 | 7% |
| **Python process menadžer (aktivan, treba da ostane)** | ~288 | 7% |
| **Python IPC klijent (aktivan, treba da ostane)** | ~274 | 7% |
| **Window management (aktivan, treba da ostane)** | ~176 | 4% |
| **Security self-test (aktivan, treba da ostane)** | ~157 | 4% |
| **IPC handleri (thin passthrough, treba da ostanu)** | ~316 | 8% |
| **main.cjs — preostala logika** | ~949 | 23% |
| **Ostalo (preload, env, ipc, secureWebPreferences)** | ~146 | 3% |
| **Ukupno** | **~4.190** | **100%** |

**Ključni nalaz:** ~75% koda u `electron/` je **ili aktivan i neophodan** (app shell, IPC, companion, Python menadžer) **ili namjerno zadržan legacy fallback koji se ne poziva** (LEGACY_FLAG=0). Oko 25% (uglavnom `main.cjs` + `legacyMedia.cjs` + `legacyDb.cjs`) je mrtav ili dupliran kod koji se može sigurno ukloniti.

---

## 2. Detaljna analiza modula

### 2.1 `electron/main.cjs` (949 linija) — nivo: ⚠️ ZNAČAJAN TEHNIČKI DUG

| Sekcija | Linije | Status | Preporuka |
|---|---|---|---|
| **Imports** — legacyMedia, PowerShell, pythonClient, core moduli | 1–60 | Većina potrebna, legacyMedia/PowerShell samo za legacy fallback | Očistiti nepotrebne importe |
| **`handleToolsExecute()`** — glavni tool dispatcher | 170–320 | Djelimično aktivan: PHASE11 delegacija se poziva; legacy fallback handleri su **mrtav kod** (LEGACY_FLAG=0) | **Premjestiti u `electron/ipc_handlers/tools.cjs`** |
| **`PHASE11_DELEGATED_TOOLS`** — Set delegiranih toolova | 1 linija | Aktivan, koristi se u handleToolsExecute | Premjestiti u `legacyTools.cjs` |
| **`LEGACY_FAIL_CLOSED_TOOLS`** — Set fail-closed toolova | 1 linija | Aktivan, sigurnosno kritičan | Premjestiti u `legacyTools.cjs` |
| **`adaptPythonToolResponse()`** — adapter odgovora | ~30 linija | Aktivan, koristi ga handleToolsExecute | Premjestiti u `pythonClient.cjs` |
| **`prepareWindowData()`** — startup data prep | 1 linija | Poziva `ensureData()` + `clearStartupLoadingThumbnails()` | Inline-ovati u `app.whenReady()` |
| **`clearStartupLoadingThumbnails()`** — legacy JSON DB cleanup | ~12 linija | **Mrtav kod** | Ukloniti |
| **`requireComputerMode()`** — mode guard | ~12 linija | Aktivan, ali legacy handleri su mrtvi (LEGACY_FLAG=0) | Postaje mrtav kad se legacy handleri uklone |
| **`requiresConfirmation()`** — legacy confirmation guard | ~5 linija | **Mrtav kod** — FAZA 10 permission engine | Ukloniti |
| **`recordsArtifact()`** — legacy helper | ~8 linija | **Mrtav kod** | Ukloniti |
| **`normalizeMermaidDiagram()` + `fallbackMermaidDiagram()`** | ~40 linija | **Mrtav kod** | Ukloniti |
| **`triggerKillSwitch()` + `registerKillSwitch()`** | ~40 linija | **Aktivan** — sigurnosno kritičan | Premjestiti u `electron/core/killSwitch.cjs` |
| **`confirmations:retry-result` inline handler** | ~12 linija | Aktivan | Premjestiti u `confirmations.cjs` |
| **`set_mode:ui-toggle` inline handler** | ~10 linija | Aktivan — UI toggle (P3-L) | Premjestiti u `app.cjs` |
| **`app.whenReady()`** | ~90 linija | Aktivan — app lifecycle | **Dobro gdje je** |
| **`app.on('before-quit')`** | ~5 linija | Aktivan | Dobro gdje je |
| **IPC handler registracija** | ~50 linija | Aktivan | Dobro gdje je |

**Zaključak:** `main.cjs` se može smanjiti sa ~949 na ~300–350 linija jednostavnim premještanjem handlera i uklanjanjem mrtvog koda.

### 2.2 `electron/tools_legacy/legacyMedia.cjs` (730 linija) — nivo: 🔴 MRTV KOD

| Sekcija | Linije | Status | Preporuka |
|---|---|---|---|
| **`webSearch()`** — legacy Exa web search | ~50 | **Mrtav kod** (LEGACY_FLAG=0, Python ima `web_search`) | Ukloniti |
| **`generateImage()`** — legacy OpenAI image gen | ~40 | **Mrtav kod** (LEGACY_FLAG=0, Python ima `image_generate`) | Ukloniti |
| **Thumbnail board funkcije** (~30 funkcija, sve thumbnail_*) | ~600 | **Djelimično aktivan** — `buildThumbnailBoardInstructions()` se poziva iz `realtime.cjs`; `commitThumbnailReference()` iz `thumbnails.cjs`. Ostalo je mrtav kod. | **Skinuti na minimum** (vidi Korak 6) |
| **Pomoćne funkcije** (`formatSearchMarkdown`, `cleanMarkdownText`, `hostname`, `buildMenuMarkdown`) | ~40 | **Mrtav kod** | Ukloniti |

**Ključni problem:** Thumbnail board (generisanje/uređivanje slika za YouTube thumbnailove) je **jedina veća funkcionalnost koja nije migrirana u Python**. Koristi OpenAI Image API direktno iz Electrona, čuva stanje u legacy JSON DB, i nema Python ekvivalent. Ovo je **svjesno odloženo** — thumbnail board je izolovan feature čija migracija ne donosi sigurnosnu dobit.

### 2.3 `electron/tools_legacy/powershell/` (201 linija, 8 fajlova) — nivo: 🟡 NEACTIVAN ALI ZADRŽAN

| Fajl | Linije | Status | Preporuka |
|---|---|---|---|
| `runPowerShell.cjs` | 47 | Legacy shared helper | Ukloniti |
| `computerClick.cjs` | 17 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `computerOpenApp.cjs` | 11 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `computerPressKey.cjs` | 38 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `computerScroll.cjs` | 20 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `computerTypeText.cjs` | 19 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `screenSnapshot.cjs` | 26 | Legacy, LEGACY_FLAG=0 | Ukloniti |
| `uiInspect.cjs` | 23 | Legacy, LEGACY_FLAG=0 | Ukloniti |

**Status:** `LEGACY_FLAG` je `0` (FAZA 17). Python ima ekvivalente za sve. MIGRATION_PLAN.md kaže "Ne brisati legacy PowerShell toolove dok Python zamjena nije testirana" — Python zamjena je **testirana i aktivna** od FAZE 13/14/16. Sigurno je ukloniti.

### 2.4 `electron/core/legacyDb.cjs` (92 linije) — nivo: 🟡 DJELIMIČNO AKTIVAN

| Funkcija | Status | Preporuka |
|---|---|---|
| `ensureData()` | Aktivan — poziva ga `prepareWindowData()` | Premjestiti u `pythonClient.cjs` ili `window.cjs` |
| `readDb()` | Aktivan — poziva ga `realtime.cjs` za thumbnail board | Zadržati dok thumbnail board ne migrira |
| `writeDb()`, `updateDb()` | **Mrtav kod** (osim thumbnail board) | Zadržati dok thumbnail board ne migrira |
| `asObject()`, `defaultDb()`, `normalizeDb()` | Aktivan | Zadržati dok thumbnail board ne migrira |

**Zavisnost:** `realtime.cjs` čita JSON DB da bi dobio thumbnail board stanje i ugradio ga u `buildThumbnailBoardInstructions()`. Ovo je jedini razlog zašto JSON DB i dalje postoji.

### 2.5 `electron/core/companionWindow.cjs` (309 linija) — nivo: ✅ AKTIVAN, OSTAVITI

Companion orb je **čisto Electron/desktop feature** — nema razloga za migraciju u Python. Jedina zavisnost je `getSettings()` (Python backend) za lokalizovane meni labele, što je ispravan obrazac.

### 2.6 `electron/core/realtimeToolSpecs.cjs` (498 linija) — nivo: ✅ AKTIVAN, OSTAVITI

Tool specifikacije za OpenAI Realtime API. **Moraju ostati u Electronu** jer se šalju direktno u Realtime sesiju iz renderera. Python ih ne vidi — ovo je data-only fajl.

### 2.7 `electron/ipc_handlers/` (8 fajlova, ~316 linija) — nivo: ✅ AKTIVAN, OSTAVITI

Svi IPC handleri su **thin passthrough** (primaju IPC poziv, prosljeđuju ga Python backend-u preko `pythonClient.cjs`). Ovo je ispravan obrazac — nema poslovne logike.

### 2.8 `electron/services/pythonClient.cjs` (274 linije) — nivo: ✅ AKTIVAN, OSTAVITI

HTTP klijent za Python backend. Sadrži `requestJson()`, `setLocalToken()`, i sve API wrapper funkcije. Ovo je **jedina komunikacija** između Electrona i Pythona — kritičan, dobro dizajniran modul.

### 2.9 `electron/services/pythonProcess.cjs` (288 linija) — nivo: ✅ AKTIVAN, OSTAVITI

Python backend proces menadžer. Startuje/zaustavlja Python backend, generiše lokalni auth token, čeka na `/health`. **Neophodan za hibridnu arhitekturu.**

---

## 3. Šta je migrirano u Python (pregled po fazama)

| FAZA | Šta je migrirano | Python fajl | Status |
|---|---|---|---|
| 4 | Python skeleton (FastAPI, /health, /tools) | `app/main.py`, `app/api/health.py` | ✅ |
| 6 | Realtime session minting (API ključ na backendu) | `app/api/realtime.py` | ✅ |
| 7 | SQLite storage (settings, confirmations, plans, tool_runs, activity) | `app/core/`, `app/repositories/` | ✅ |
| 9 | Confirmations + Plans REST API | `app/api/confirmations.py`, `app/api/plans.py` | ✅ |
| 10 | Permission/risk engine + cancellation state mašina | `app/agent/permission_engine.py`, `app/agent/cancellation.py` | ✅ |
| 11 | Tool registry + notes/records/artifacts/screenshot/ui_inspect | `app/agent/tool_registry.py`, `app/agent/tool_catalog/phase11.py` | ✅ |
| 13 | Computer-use v1 (koordinate: click, type, press_key, scroll, open_app) | `app/agent/tool_catalog/phase13.py` | ✅ |
| 14 | Computer-use v2 (element targeting: find_elements, click_element, set_text_element, get_element_text) | `app/agent/tool_catalog/phase14.py` | ✅ |
| 15 | Agent runtime (LocalDesktopAssistant, conversation_state, model_client, prompt_builder) | `app/agent/runtime.py`, `app/agent/conversation_state.py`, `app/agent/model_client.py`, `app/agent/prompt_builder.py` | ✅ |
| 16 | OpenAI/Exa/image integracije (web_search, image_generate) | `app/tools/web/search.py`, `app/services/exa_client.py`, `app/tools/images/generate.py` | ✅ |

---

## 4. Šta NIJE migrirano — i zašto

| Funkcionalnost | Ostaje u | Razlog |
|---|---|---|
| **Companion orb** (prozor, tray, drag, context menu) | `electron/core/companionWindow.cjs` | Čisto desktop feature — Electron BrowserWindow upravljanje, nema smisla u Pythonu. |
| **Window management** (createWindow, setWindowMode, mini window) | `electron/core/window.cjs` | Čisto Electron — BrowserWindow, display/computer mode toggle, DWM bug workaround. |
| **Kill-switch hotkey** (Ctrl+Alt+K, globalShortcut) | `electron/main.cjs` (predloženo: `core/killSwitch.cjs`) | globalShortcut je Electron API — mora ostati u main procesu. |
| **Realtime tool specifikacije** | `electron/core/realtimeToolSpecs.cjs` | Šalju se direktno OpenAI Realtime API-ju iz renderera — Python ih ne vidi. |
| **Realtime instructions builder** (buildRickyInstructions, thumbnail board instrukcije) | `electron/ipc_handlers/realtime.cjs` | Zavisi od `db` (JSON DB) i `toolSpecs` — dok thumbnail board ne migrira, mora ostati ovdje. |
| **IPC passthrough handleri** | `electron/ipc_handlers/*.cjs` | Tanak sloj koji samo prosljeđuje IPC → Python. Ovo je **ispravna arhitektura**. |
| **Python process menadžer** | `electron/services/pythonProcess.cjs` | Startuje/zaustavlja Python child process — mora biti u Electron main procesu. |
| **Thumbnail board** (generisanje/uređivanje/izbor slika) | `electron/tools_legacy/legacyMedia.cjs` + `electron/core/legacyDb.cjs` | **Svjesno odloženo.** Thumbnail board je izolovan feature. Migracija ne donosi sigurnosnu dobit. |
| **Security self-test** | `electron/core/securitySelfTest.cjs` | Kombinuje Electron + backend provjere — mora ostati hibridno. |
| **Legacy JSON DB** (notes, records, thumbnailBoard) | `electron/core/legacyDb.cjs` | Samo za thumbnail board — notes/records su već u SQLite preko Python backend-a. |

---

## 5. Preostali tehnički dug — prioritetizovano

Prioriteti su označeni P0 (hitno, sigurnosno ili arhitektonski kritično) do P3 (kozmetičko, niski rizik).

### P0 — Sigurnosno kritično

| Stavka | Detalj | Zavisnost |
|---|---|---|
| **Nema JS/TS testova za frontend** | `npm run test` pokreće samo `pytest`. Nema Vitest/Jest konfiguracije. Dva stvarna buga (confirmation bridge, retry provjera) su ranije nađena ručno, ne testovima. | — |
| **Security Gate 1 nije zatvoren** | Rate limiting, CI security checks, document privacy model nedostaju. | FAZA 9 (confirmations), FAZA 10 (permission engine) |
| **Security Gate 2 nije zatvoren** | Code signing, signed updates, encrypted secrets, pentest checklist. | FAZA 19 (packaging) |

### P1 — Arhitektonski dug

| Stavka | Detalj | Procjena |
|---|---|---|
| **Premjestiti `handleToolsExecute` u `electron/ipc_handlers/tools.cjs`** | Čist refactor — isjeći ~150 linija iz `main.cjs`, premjestiti u zaseban handler modul. Isti obrazac kao confirmations/plans/events handleri. | ~30 min |
| **Premjestiti kill-switch u `electron/core/killSwitch.cjs`** | Izdvojiti `triggerKillSwitch()` + `registerKillSwitch()` + `KILL_SWITCH_ACCELERATORS` u zaseban modul. | ~15 min |
| **Premjestiti `PHASE11_DELEGATED_TOOLS` + `LEGACY_FAIL_CLOSED_TOOLS` u `legacyTools.cjs`** | Konsolidovati sve tool setove na jednom mjestu. | ~10 min |
| **Premjestiti `adaptPythonToolResponse()` u `pythonClient.cjs`** | Logički pripada HTTP klijentskom sloju, ne main.cjs. | ~10 min |
| **Premjestiti inline IPC handler-e u odgovarajuće `ipc_handlers/` fajlove** | `confirmations:retry-result` → `confirmations.cjs`, `set_mode:ui-toggle` → `app.cjs`, `companion:stop` → `companion.cjs` | ~15 min |
| **Ukloniti mrtve legacy handler-e iz `main.cjs`** | `recordsArtifact()`, `normalizeMermaidDiagram()`, `fallbackMermaidDiagram()`, `requiresConfirmation()`, `requireComputerMode()` — niko ih ne poziva. | ~10 min |

### P2 — Legacy cleanup

| Stavka | Detalj | Procjena |
|---|---|---|
| **Ukloniti legacy PowerShell toolove** | 8 fajlova (~201 linija) — `electron/tools_legacy/powershell/*.cjs`. Python ima ekvivalente za sve. LEGACY_FLAG je 0. | ~20 min |
| **Skinuti `legacyMedia.cjs` na minimum** | Zadržati samo `buildThumbnailBoardInstructions()`, `commitThumbnailReference()`, `thumbnailBoardSummary()`, `thumbnailBoardArtifact()`, `resolveReferencePaths()` + zavisnosti. Ukloniti `webSearch()`, `generateImage()`, `buildMenuMarkdown()`, sve thumbnail generate/edit funkcije koje pozivaju OpenAI API direktno. | ~45 min |
| **Ukloniti duplirani `dataDir` konstante** | `main.cjs`, `legacyDb.cjs`, `legacyMedia.cjs`, `thumbnails.cjs` — svi imaju svoju kopiju `path.join(process.cwd(), 'data')`. Konsolidovati u jedan modul. | ~15 min |

### P3 — Dugoročno (niski prioritet)

| Stavka | Detalj | Procjena |
|---|---|---|
| **Migrirati thumbnail board u Python** | Zahtijeva: (1) Python endpoint za image generation, (2) SQLite `thumbnails` tabelu, (3) React thumbnail panel koji čita iz Python-a umjesto JSON DB. | ~2-3 dana |
| **Zamijeniti polling push notifikacijama (SSE)** | `setInterval` na 3s za events/confirmations → `GET /events/stream`. | ~1 dan |
| **CSS refactor** | `src/styles/` ima 14 fajlova. Neki su legacy (02-legacy-shell, 03-artifacts, 04-voice) i mogli bi se konsolidovati. | ~1 dan |
| **App.tsx refactor** | 735 linija, mnogo handler funkcija. Razdvojiti u custom hooks (`useVoiceSession`, `useDictation`, `useConfirmations`, `usePlans`). | ~1-2 dana |

---

## 6. Plan čišćenja (konkretni koraci)

### Korak 1: Premjestiti `handleToolsExecute` iz `main.cjs` → `ipc_handlers/tools.cjs`

```text
Cilj: Smanjiti main.cjs za ~150 linija. Čist refactor — nema promjene ponašanja.

Koraci:
1. Kreirati `electron/ipc_handlers/tools.cjs`
2. Premjestiti: handleToolsExecute, PHASE11_DELEGATED_TOOLS, LEGACY_FAIL_CLOSED_TOOLS,
   adaptPythonToolResponse, PYTHON_TOOL_EXECUTE_TIMEOUT_MS, requireComputerMode,
   requiresConfirmation, recordsArtifact, normalizeMermaidDiagram, fallbackMermaidDiagram
3. U main.cjs: require('./ipc_handlers/tools.cjs') i registrovati handler
4. Pokrenuti smoke test: npm run dev + provjera da svi toolovi rade

Rizik: Nizak — isti obrazac kao confirmations/plans/events handleri.
Test: npm run quality (typecheck + build + pytest)
```

### Korak 2: Premjestiti kill-switch → `core/killSwitch.cjs`

```text
Cilj: Izdvojiti globalnu hotkey logiku u zaseban modul.

Koraci:
1. Kreirati `electron/core/killSwitch.cjs`
2. Premjestiti: KILL_SWITCH_ACCELERATORS, triggerKillSwitch, registerKillSwitch
3. Export-ovati: registerKillSwitch (poziva se iz app.whenReady), unregisterKillSwitch (iz before-quit),
   triggerKillSwitch (za companion:stop IPC handler)
4. U main.cjs: require + poziv registerKillSwitch

Rizik: Nizak. Samo premještanje koda.
```

### Korak 3: Premjestiti inline IPC handler-e

```text
Cilj: Konsolidovati sve IPC handler-e u odgovarajuće module.

- confirmations:retry-result → electron/ipc_handlers/confirmations.cjs
- set_mode:ui-toggle → electron/ipc_handlers/app.cjs (ili tools.cjs)
- companion:stop → electron/ipc_handlers/companion.cjs

Svaki: izvaditi inline handler funkciju iz registerIpcHandlers bloka,
premjestiti u odgovarajući modul, export-ovati, import-ovati u main.cjs.
```

### Korak 4: Ukloniti mrtve helper funkcije iz `main.cjs`

```text
- requiresConfirmation() — mrtav kod (FAZA 10 permission engine)
- requireComputerMode() — postaje mrtav kad se legacy handleri uklone
- recordsArtifact() — mrtav kod (legacy records, nikad se ne poziva)
- normalizeMermaidDiagram() + fallbackMermaidDiagram() — mrtav kod (LEGACY_FLAG=0)
- clearStartupLoadingThumbnails() — može se inline-ovati ili ukloniti
```

### Korak 5: Ukloniti legacy PowerShell toolove

```text
- Izbrisati: electron/tools_legacy/powershell/*.cjs (8 fajlova)
- Izbrisati: importe iz main.cjs (computerOpenApp, computerTypeText, itd.)
- Ukloniti: legacy handler sekcije iz handleToolsExecute (computer_open_app, computer_type_text, itd.)
- Ažurirati: legacyTools.cjs — ukloniti TOOLS_PENDING_PYTHON_EQUIVALENT Set

Preduvjet: Korak 1 (tools.cjs) je završen — lakše je ukloniti legacy handler-e iz zasebnog fajla.
```

### Korak 6: Skinuti `legacyMedia.cjs` na minimum

```text
Zadržati samo funkcije koje su i dalje potrebne:
- buildThumbnailBoardInstructions() — poziva se iz realtime.cjs
- commitThumbnailReference() — poziva se iz thumbnails.cjs
- thumbnailBoardSummary(), thumbnailBoardArtifact() — koriste se u buildThumbnailBoardInstructions
- resolveReferencePaths() — poziva se iz thumbnailGenerate/thumbnailEdit
- thumbnailByNumberOrSelected(), replaceLoadingThumbnails(), removeLoadingThumbnailRun()
- thumbnailNumber(), assignThumbnailNumber(), pageForArgs()
- sortedThumbnailImages(), paginatedThumbnailImages(), thumbnailPageMeta()
- imageDataUrl(), mimeForPath(), imageErrorArtifact()

Ukloniti:
- webSearch(), formatSearchMarkdown(), cleanMarkdownText(), hostname()
- buildMenuMarkdown()
- generateImage(), imageErrorArtifact() (duplikat)
- thumbnailLoadingPrepare(), thumbnailGenerate(), thumbnailEdit()
- createThumbnailImage(), editImageWithInputs(), saveImageResponse()
- thumbnailRecord(), thumbnailPrompt(), editThumbnailPrompt()
- thumbnailSelect() (ako se ne poziva nigdje drugdje)
```

### Korak 7: Finalno smanjenje `main.cjs`

```text
Nakon koraka 1-6, main.cjs bi trebao biti ~200-300 linija:

- Imports: ~30 linija (samo potrebni moduli)
- IPC handler registracija: ~50 linija
- app.whenReady(): ~90 linija
- app.on('before-quit'): ~5 linija
- app.on('window-all-closed'): ~3 linije
- app.on('activate'): ~5 linija
- prepareWindowData(): ~5 linija
- Ukupno: ~200-250 linija (sa praznim redovima i komentarima)
```

---

## 7. Arhitektonska pravila — provjera usklađenosti

Pravilo iz `AGENTS.md`: **"Do not add new business logic to `electron/main.cjs`."**

| Pravilo | Status | Dokaz |
|---|---|---|
| Nema nove agent/computer-use/storage/AI logike u main.cjs | ✅ | Sva nova logika je u Pythonu. main.cjs sadrži samo legacy fallback + IPC wiring. |
| Nema proizvoljnog shell execution tool-a | ✅ | `runPowerShell()` postoji samo u legacy fallbacku, LEGACY_FLAG=0. |
| Legacy PowerShell toolovi nisu obrisani dok Python zamjena nije testirana | ✅ | Python zamjena je testirana i aktivna (FAZE 13/14/16), ali legacy fajlovi još nisu obrisani — slijedi Korak 5. |
| API ključevi samo na Python backend strani | ✅ | FAZA 6: OpenAI ključ je samo u Python backendu, Electron prima samo kratkoživući Realtime token. |
| Svaki tool poziv prolazi kroz permission/risk sloj | ✅ | FAZA 10 + FAZA 11: svi Python-registrovani toolovi prolaze kroz `permission_engine.py`. |
| Svaki tool poziv se loguje | ✅ | FAZA 7: `tool_runs` tabela u SQLite. |

---

## 8. Zavisnost dijagram

```text
electron/main.cjs
  ├── electron/core/env.cjs              (obavezan, startup)
  ├── electron/core/window.cjs            (obavezan, window creation)
  ├── electron/core/ipc.cjs               (obavezan, IPC wiring)
  ├── electron/core/securitySelfTest.cjs  (obavezan, security)
  ├── electron/core/legacyTools.cjs       (obavezan, feature flag)
  ├── electron/core/companionWindow.cjs   (obavezan, orb)
  ├── electron/services/pythonProcess.cjs (obavezan, backend manager)
  ├── electron/services/pythonClient.cjs  (obavezan, HTTP klijent)
  ├── electron/ipc_handlers/*.cjs         (obavezni, IPC passthrough)
  ├── electron/tools_legacy/legacyMedia.cjs (opcioni, samo thumbnail)
  └── electron/tools_legacy/powershell/*.cjs (MRTV, LEGACY_FLAG=0)
```

---

## 9. Zaključak

Migracija Electron → Python je **suštinski završena**. Sve ključne funkcionalnosti (agent runtime, tool registry, permission/risk engine, storage, AI integracije, computer-use) su u Python backendu. Electron shell je sveden na IPC most, app lifecycle menadžera, i desktop-specifične feature-e (companion orb, window management, kill-switch).

Preostali rad je **čišćenje, ne nova migracija**:

1. **Premjestiti `handleToolsExecute`** u zaseban IPC handler modul (P1, ~30 min)
2. **Premjestiti kill-switch** u zaseban modul (P1, ~15 min)
3. **Premjestiti inline IPC handler-e** (P1, ~15 min)
4. **Ukloniti mrtve helper funkcije** (P1, ~10 min)
5. **Ukloniti legacy PowerShell toolove** (P2, ~20 min)
6. **Skinuti `legacyMedia.cjs` na minimum** (P2, ~45 min)
7. **Migrirati thumbnail board u Python** (P3, ~2-3 dana — opciono)

**Ukupna procjena za P1+P2: ~2-3 sata.**