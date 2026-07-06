# Packaging plan — RileyJarvis Windows Hybrid

> **Posljednje ažuriranje:** FAZA 19 / 2026-07-06
> **Povezano:** `docs/MIGRATION_PLAN.md`, `electron-builder.yml`, `python_backend/ricky_backend.spec`

---

## Cilj

Napraviti instalabilnu Windows aplikaciju gdje korisnik ne mora instalirati Python — sve je u jednom `.exe` installeru.

---

## Arhitektura

```text
Ricky/
  Ricky.exe                          (Electron main)
  resources/
    app.asar                         (Electron app bundle)
    ricky_backend/                   (PyInstaller --onedir sidecar)
      ricky_backend.exe              (FastAPI backend)
      _internal/                     (Python interpreter + libs)
      data/                          (runtime SQLite/screenshots/images)
```

Electron u produkciji startuje sidecar:

```text
resources/ricky_backend/ricky_backend.exe
  env: RICKY_HOST=127.0.0.1
  env: RICKY_PORT=8765
  env: RICKY_DATA_DIR=<sidecar>/data/
  env: RICKY_LOCAL_TOKEN=<generisan po sesiji>
  env: OPENAI_API_KEY=<iz env varijable ako postoji>
  env: EXA_API_KEY=<iz env varijable ako postoji>
```

---

## Build koraci

### 1. Frontend

```bash
npm run build
```

### 2. Backend sidecar

```bash
cd python_backend
pip install pyinstaller
pyinstaller --clean --noconfirm ricky_backend.spec
# Output: python_backend/dist/ricky_backend/ricky_backend.exe
```

### 3. Electron package

```bash
npm install --save-dev electron-builder

# Brzi test (unpacked folder):
npx electron-builder --win --dir

# Puni installer:
npx electron-builder --win
# Output: release/Ricky Setup x.x.x.exe
```

---

## Šta ulazi u paket

| Fajlovi | Kroz | Napomena |
|---------|------|----------|
| `dist/**/*` | `files` | Vite build output (React UI) |
| `electron/**/*` | `files` | Electron main proces, preload, core moduli |
| `package.json` | `files` | Electron metadata |
| `python_backend/dist/ricky_backend/` | `extraFiles` | PyInstaller sidecar (.exe + Python runtime) |
| `assets/Ricky-agent.png` | `files` | Ikonica aplikacije |

## Šta NE ulazi u paket

| Fajlovi | Razlog |
|---------|--------|
| `.env.local` | `.gitignore` + nije u `files`/`extraFiles` — API ključevi nisu hardkodirani |
| `.env.*` (osim `.env.example`) | `.gitignore` |
| `python_backend/app/` (source) | Samo .exe sidecar ide — source ostaje u git-u |
| `python_backend/tests/` | Nije u sidecar-u (excludes u .spec) |
| `python_backend/data/` | Runtime folder, kreira se pri prvom pokretanju |
| `node_modules/` | `.gitignore` |
| `*.log`, `*.sqlite`, `*.db` | `.gitignore` |

---

## Sigurnosne provjere u packaged build-u

### Security Gate 0 self-test

`electron/core/securitySelfTest.cjs` se poziva prije kreiranja prozora u packaged build-u. Ako bilo koja provjera faila, aplikacija se gasi (`fail-closed`).

Provjere:
- **Electron webPreferences**: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`
- **Preload surface**: nema `OPENAI` stringova, nema `ipcRenderer.invoke(channel)` passthrough
- **Backend self-test**: `GET /security/self-test` — provjerava host binding (`127.0.0.1`), auth token, CORS, critical-tool confirmation gating

### API ključevi

- `.env.local` fizički ne može ući u paket (nije u `files`/`extraFiles`, pokriven `.gitignore`-om)
- Korisnik mora postaviti `OPENAI_API_KEY` i `EXA_API_KEY` kao env varijable (sistemske ili `.env` pored `.exe`-a)
- Backend će pokrenuti, ali `web_search`/`image_generate`/`realtime` će vratiti `MISSING_API_KEY` ako ključevi nisu postavljeni — fail-closed

### Legacy PowerShell flag

`RICKY_USE_LEGACY_POWERSHELL_TOOLS` ostaje `default=1` — ne mijenja se u ovoj fazi. Legacy computer_* alati su dostupni dok FAZA 13/14 ne dodaju Python zamjene.

---

## Testiranje packagovanog build-a

```bash
# 1. Napravi unpacked build (brzo, bez instalacije)
npx electron-builder --win --dir
# Output: release/win-unpacked/

# 2. Pokreni
./release/win-unpacked/Ricky.exe

# 3. Provjeri:
#    - Backend se automatski pokreće (ricky_backend.exe proces u Task Manager-u)
#    - /health odgovara (pogledaj u log)
#    - Prozor se prikazuje
#    - Backend se gasi kad se app zatvori
```

---

## Dev vs Packaged — razlika u pokretanju

| Aspekt | Dev (`npm run dev`) | Packaged (`Ricky Setup.exe`) |
|--------|--------------------|-------------------------------|
| Python runtime | Lokalni Python + `uvicorn` | Bundlovani `ricky_backend.exe` (PyInstaller) |
| Backend start komanda | `python -m uvicorn app.main:app ...` | `ricky_backend.exe` (bez argumenata, env varijable) |
| Data folder | `<repo>/data/` | `<sidecar>/data/` |
| Automatsko pokretanje | Uvijek (`enabled = true`) | Uvijek (`enabled = true`) |
| Backend source | `python_backend/app/` (čita se direktno) | Nema source — sve u `.exe` |

---

## Status

**FAZA 19: implementirano** (vidi `agent_reports/2026-07-06_faza19-packaging-plan.md`).
- `python_backend/ricky_backend.spec` ✅
- `electron-builder.yml` ✅
- `electron/services/pythonProcess.cjs` — packaged grananje ✅
- `python_backend/app/core/config.py` — `RICKY_HOST`/`RICKY_PORT` env override ✅
- `.gitignore` — `python_backend/build/`, `python_backend/dist/ricky_backend/` ✅

**Preostalo**:
- Stvarni `pyinstaller` build + testiranje na Windows mašini
- `electron-builder --win` build + testiranje
- Code signing (Security Gate 2)
