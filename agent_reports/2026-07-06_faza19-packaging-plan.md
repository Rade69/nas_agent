# FAZA 19 — Packaging plan (draft)

## Datum

2026-07-06

## Scope

Implementiran je FAZA 19 draft iz `docs/MIGRATION_PLAN.md`: PyInstaller sidecar spec, electron-builder konfiguracija, i packaged-mode grananje u `pythonProcess.cjs`.

Ovo je **draft/prep dio** — stvarni packaged build (`npx electron-builder --win`) zahtijeva:
1. PyInstaller build na Windows mašini (`pyinstaller ricky_backend.spec`)
2. `electron-builder --win --dir` za test unpacked build-a
3. Verifikaciju da securitySelfTest prolazi u packaged modu

**Nije implementirano**: stvarni `.exe` installer, code signing (Security Gate 2).

## Šta je urađeno

### `python_backend/ricky_backend.spec` (novi)

- PyInstaller `--onedir` spec za `app.main:app`
- Svi `hiddenimports` (app.agent.*, app.api.*, app.core.*, app.schemas.*, app.services.*, app.storage.repositories.*, app.tools.*, uvicorn.*)
- Excludes: tkinter, matplotlib, numpy, pandas, tests — smanjuje sidecar veličinu
- `console=False` — GUI app bez konzolnog prozora
- `COLLECT` za `--onedir` output

### `electron-builder.yml` (novi)

- `appId: com.rileyjarvis.ricky`, `productName: Ricky`
- `files`: `dist/**/*`, `electron/**/*`, `package.json`
- `extraFiles`: `python_backend/dist/ricky_backend/` → `resources/ricky_backend/`
- `asar: true` (extraFiles ide mimo asar-a, nije potreban `asarUnpack`)
- `win.target: nsis` (x64, oneClick: false, allowToChangeInstallationDirectory)
- Nema automatskog update-a (Security Gate 2)
- `.env.*` automatski isključen (nije u `files`/`extraFiles`)

### `electron/services/pythonProcess.cjs`

- **Uklonjen placeholder**: `enabled = !isPackaged` (gasio backend u packaged build-u) → `enabled = true`
- **Dodato grananje**: `if (options.isPackaged)` → `startPackagedBackend()` koja:
  - Traži `process.resourcesPath/ricky_backend/ricky_backend.exe`
  - Kreira `data/` folder u sidecar direktoriju
  - Proslijeđuje `RICKY_HOST`, `RICKY_PORT`, `RICKY_DATA_DIR`, `RICKY_LOCAL_TOKEN` i sve postojeće env varijable (OPENAI_API_KEY, EXA_API_KEY)
  - Standardni spawn/health-check/error-handling tok (isti kao dev putanja)
- **Dev ostaje nepromijenjen**: `python -m uvicorn app.main:app ...` kao do sada

### `python_backend/app/core/config.py`

- `get_settings()` sada čita `RICKY_HOST` i `RICKY_PORT` env varijable (za sidecar .exe koji nema CLI argumenata)

### `.gitignore`

- Dodati: `python_backend/build/`, `python_backend/dist/ricky_backend/`, `*.spec.bak`

### `docs/PACKAGING_PLAN.md` — potpuno prepisan

- Arhitektura (folder struktura)
- Build koraci (frontend → sidecar → electron-builder)
- Tabele: šta ulazi / šta NE ulazi u paket
- Sigurnosne provjere (securitySelfTest, API ključevi, legacy flag)
- Testiranje packagovanog build-a
- Dev vs Packaged tabela (python runtime, start komanda, data folder)

## Verifikacija

```text
pytest: 105 passed (91 + 14 Claude-ovih security/path_sandbox testova — bez regresije)
typecheck: prošao
build: prošao
node --check electron/services/pythonProcess.cjs: clean
smoke (dev mode): startPythonBackend({isPackaged:false}) → status: running, health: true
```

## Rizici/ograničenja

- **Nije testirano na stvarnom PyInstaller build-u**: sidecar .spec je napisan po dokumentaciji (hiddenimports kompletni, excludes za smanjenje), ali stvarni `pyinstaller ricky_backend.spec` na Windows mašini može otkriti missing imports. Preporuka: pokrenuti `pyinstaller --clean ricky_backend.spec` i testirati `ricky_backend.exe` standalone.
- **electron-builder nije instaliran**: `npm install --save-dev electron-builder` treba pokrenuti prije prvog build-a. Nije dodato u `package.json` `devDependencies` (ostavljeno korisniku da odluči verziju).
- **Sidecar path**: `process.resourcesPath` je Electron-ova varijabla za putanju do `resources/` foldera. U unpacked build-u (`--dir`) ovo pokazuje na `release/win-unpacked/resources/`. Ako sidecar nije tu, `startPackagedBackend` baca error sa jasnom porukom.
- **Legacy flag**: `RICKY_USE_LEGACY_POWERSHELL_TOOLS` ostaje `default=1` — ne mijenja se u ovoj fazi (FAZA 13/14 nije urađena).
- **API ključevi**: `.env.local` ne ulazi u paket. Korisnik mora postaviti env varijable sistemski ili kreirati `.env` pored `.exe`-a. Backend fail-closed (vraća `MISSING_API_KEY`).

## Potreban follow-up

- **PyInstaller build + test**: `cd python_backend && pyinstaller --clean ricky_backend.spec && dist/ricky_backend/ricky_backend.exe`
- **electron-builder instalacija + testni build**: `npm i -D electron-builder && npx electron-builder --win --dir`
- **Security Gate 2**: code signing, signed updates, encrypted secrets
- **CI pipeline**: dodati PyInstaller + electron-builder korake u GitHub Actions

## Potrebna korisnička potvrda

1. Da li da dodam `electron-builder` u `devDependencies` sada ili korisnik sam instalira?
2. Da li da dodam `npm run package` skriptu (`electron-builder --win --dir`) u `package.json`?
3. Da li želiš da probam stvarni `pyinstaller` build na ovoj mašini (zahtijeva PyInstaller instalaciju)?
