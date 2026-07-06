# FAZA 18 — Test suite i quality gate

## Datum

2026-07-06

## Scope

Implementirana je FAZA 18 iz `docs/MIGRATION_PLAN.md`: organizovani quality gate pipeline, Electron smoke skripta, dokumentacija testova, edge-case testovi za schemas i events endpoint.

Nije dirana Python backend logika. Nije diran audio pipeline. Nije implementirana FAZA 19 (packaging).

## Šta je urađeno

### `package.json` — npm skriptovi

Dodati novi skriptovi:

| Skripta | Opis |
|---------|------|
| `npm run check` | `node --check` za Electron `.cjs` fajlove (main, preload, pythonClient, env, ipc, legacyTools) — syntax validacija bez Electron runtime-a |
| `npm run test` | `python -m pytest -q` — shortcut za brzo pokretanje backend testova |
| `npm run smoke` | `node scripts/smoke-test.cjs` — end-to-end smoke (pokreće backend, provjerava health/tools/echo/note_add/events, gasi backend) |
| `npm run quality` | **Kompletan pipeline**: `typecheck → check → build → test → smoke` |

### `scripts/smoke-test.cjs` (novi)

- Pokreće Python backend proces (`startPythonBackend`)
- 6 koraka verifikacije:
  1. Backend start + `/health` čekanje (max 30 pokušaja × 600ms)
  2. `GET /tools` — provjerava `echo`, `note_add`, `web_search`, `screen_snapshot`
  3. `POST /tools/execute` — `echo` tool (smoke test argument)
  4. `POST /tools/execute` — `note_add` (FAZA 11 integracija)
  5. `GET /events` — provjerava `backend.ready` event + `next_cursor`
  6. `stopPythonBackend` → provjerava da backend više ne odgovara (do 5 pokušaja po 1s, provjerava `getHealth().ok === false`)
- Vraća exit code 0 (sve prošlo) ili 1 (najmanje 1 greška)
- Formatizirani output sa ✓/✗, brojačem grešaka, rezimeom

### `docs/TESTING.md` (novi)

- Brzi start (`npm run quality`)
- Tabela svih test fajlova (16 fajlova, 91 test) sa opisom i fazom
- Uputstvo za pokretanje pojedinačnih testova
- Quality gate pipeline opis (5 koraka, `&&` chain)
- Pre-commit checklist (7 koraka)
- CI pipeline prijedlog (GitHub Actions — backend pytest + frontend typecheck/build)
- Poznati problemi (FastAPI deprecation warning, CRLF phantom, smoke test zahtijeva instaliran Python)

### Edge-case testovi (novi)

`python_backend/tests/test_schemas.py` (8 testova):
- `ConfirmationCreateRequest` validacija (prazan action_name, nepoznat risk level)
- `PlanCreateRequest` validacija (prazan title)
- `PlanStepCreateRequest` validacija
- `PlanUpdateRequest` partial fields
- `ToolExecutionContext` default vrijednosti
- `ToolExecutionRequest` default arguments + confirmation_id

`python_backend/tests/test_events.py` (5 testova):
- `backend.ready` prisutan nakon `create_app()`
- Cursor u dalekoj budućnosti → prazna lista
- Prazan `since` parametar
- Nevalidan `since` format → 200 ili 422 (ne smije 500 crash)
- Paginacija sa cursor-om (artifact.created + cursor konzistentnost)

## Verifikacija

```text
pytest: 91 passed (78 postojećih + 13 novih), 1 warning
npm run typecheck: prošao
npm run build: prošao
npm run check: prošao (svih 6 .cjs fajlova bez syntax greške)
npm run smoke: SVE PROŠLO ✓ (19/19)
npm run quality: sve prolazi (typecheck → check → build → test → smoke)
```

## Rizici/ograničenja

- `npm run check` ne provjerava `companionWindow.cjs` i `window.cjs` — zavise od Electron native modula (`BrowserWindow`, `screen`, `nativeImage`). Syntax greške u tim fajlovima se ne bi otkrile do Electron runtime-a. Preporuka: koristiti `electron-mock` u CI pipeline-u ili dodati zasebne unit testove.
- `npm run smoke` zahtijeva instaliran Python backend (`uvicorn`, `fastapi`, `pydantic`, `httpx`, `pillow`, `psutil`). Ako neko od dependency-ja fali, smoke test faila na `startPythonBackend`, što je ispravno — ne može se testirati nešto što nije instalirano.
- `npm run quality` pokreće `smoke` na kraju — ako je ovo preagresivno za CI (vrijeme izvršavanja 10-15s samo za smoke), može se podijeliti na `quality` (bez smoke) i `quality-full` (sa smoke).

## Potreban follow-up

- **CI pipeline**: implementirati GitHub Actions workflow iz `docs/TESTING.md` prijedloga.
- **Frontend testovi**: dodati `vitest` unit testove za React komponente (RickyFace, VoiceTopBar, CompanionOrb).
- **Electron mock testovi**: dodati `electron-mock` za companionWindow/window module da se mogu `node --check` validirati u CI-ju.
- **Coverage report**: dodati `pytest-cov` za backend i `c8` za frontend.

## Potrebna korisnička potvrda

1. Da li je prihvatljivo da `npm run check` ne provjerava sve `.cjs` fajlove (samo one bez Electron native deps)?
2. Da li da `npm run quality` uključuje smoke test ili da smoke bude zaseban korak (`quality` bez smoke, `quality-full` sa smoke)?
3. Worktree sadrži `assets/*.png` i phantom CRLF fajlove — ostaju van commit-a.
