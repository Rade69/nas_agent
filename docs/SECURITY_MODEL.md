# Security model — RileyJarvis Windows Hybrid

> **Produkcijski sigurnosni plan:** [SECURITY_HARDENING_PLAN.md](./SECURITY_HARDENING_PLAN.md) je autoritativan za produkcijski build (Security Gates 0/1/2, threat model, tool executor provjere, document privacy model, self-test, itd.). Ako se ovaj dokument i `SECURITY_HARDENING_PLAN.md` razilaze, važi `SECURITY_HARDENING_PLAN.md`. Ovaj fajl ostaje kao sažetak risk levela i permission pravila koje `TOOL_CONTRACTS.md` referencira.

## Risk levels

```text
low
medium
high
critical
```

## Risk primjeri

```text
low:
  - read notes
  - create artifact
  - list tools
  - health check
  - screenshot without OCR or external upload

medium:
  - open app
  - search web
  - read file from allowed workspace
  - inspect active window

high:
  - type text
  - click
  - press key
  - edit file
  - paste clipboard
  - interact with browser

critical:
  - delete files
  - run shell command
  - install package
  - send email/message
  - execute arbitrary PowerShell/Python
  - access secrets
```

## Permission pravila

1. `critical` tools are disabled by default.
2. `high` tools require computer mode and explicit confirmation.
3. `medium` tools may require confirmation depending on context.
4. `low` tools can run without confirmation.
5. No model-facing arbitrary shell command tool.
6. File tools are restricted to allowed folders.
7. Sensitive values must be redacted from logs.
8. Every tool call must be logged.
9. Computer-use tools must capture active window before and after execution.
10. `computer_type_text`, `computer_click`, `computer_press_key`, `computer_scroll` must not execute if active app is not allowed or if computer mode is disabled.

## Allowlist primjer (FAZA 11)

```json
{
  "allowed_apps": [
    "notepad.exe",
    "calc.exe",
    "chrome.exe",
    "code.exe"
  ],
  "blocked_apps": [
    "powershell.exe",
    "cmd.exe",
    "regedit.exe"
  ]
}
```

## Status implementacije

Permission/risk engine je implementiran u FAZI 10 (`python_backend/app/agent/permission_engine.py` — risk/computer_mode/confirmation_id provjere; `python_backend/app/agent/cancellation.py` — execution_id/cancellation_token state mašina, vidi `agent_reports/2026-07-05_faza10-permission-cancellation-engine.md` i `SECURITY_HARDENING_PLAN.md` sekcija 25). `ToolExecutor` sad primjenjuje ova pravila na svaki Python-registrovan tool.

**Ažurirano (FAZA 11):** 13 low/medium-risk toolova (notes/records/artifacts/screen_snapshot/ui_inspect) je migrirano u Python i sad prolazi kroz ovaj sloj — vidi `agent_reports/2026-07-05_faza11-tool-registry-local-tools.md`. `ui_inspect` čita aktivni prozor (proces + naslov preko `ctypes`/`psutil`), ali **ovo je samo čitanje, ne enforcement** — `requires_active_window_match`/`allowed_apps`/`blocked_apps` polja postoje u `ToolDefinition` (`TOOL_CONTRACTS.md`), ali `permission_engine.py` ih još ne provjerava pri izvršenju. Path/network sandbox takođe nije implementiran.

**Ažurirano (backend local auth token, Security PR-1):** Python backend sad zahtijeva `Authorization: Bearer <token>` na svakom requestu (`python_backend/app/core/auth.py`). Electron generiše kratkoživući token po sesiji (`electron/services/pythonProcess.cjs`, `crypto.randomBytes(32)`), prosljeđuje ga Python procesu preko `RICKY_LOCAL_TOKEN` env varijable, i `pythonClient.cjs` ga automatski prilaže na svaki zahtjev. Token se ne loguje niti perzistira na disk. Verifikovano end-to-end: sirovi zahtjev bez ili sa pogrešnim tokenom dobija `401 UNAUTHORIZED`. **Ograničenje:** ako backend nema konfigurisan token (npr. pokrenut direktno preko `uvicorn` bez Electron-a, kao u testovima ili ručnom dev radu po README-u), provjera se ponaša fail-open (dozvoljava sve) — stvarni Electron-pokrenuti put uvijek postavlja token, pa je to jedini put koji mora biti siguran.

**Ograničenje koje ostaje:** legacy PowerShell computer-use alati (`computer_open_app`, `computer_type_text`, `computer_click`, `computer_scroll` — i dalje implementirani direktno u `electron/main.cjs`) **rade bez permission sloja i bez auth tokena u potpunosti** — to ostaje poznat, privremen rizik dok se ne migriraju u Python (FAZA 13/14, i dalje BLOCKED iza Security Gate 0). Active window enforcement i path/network sandbox (koraci 10-12 iz tool executor provjere, `SECURITY_HARDENING_PLAN.md` sekcija 8) su planirani za FAZU 14.

Vidi [TOOL_CONTRACTS.md](./TOOL_CONTRACTS.md) za polja `risk` i `requires_confirmation` u tool definiciji.
