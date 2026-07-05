# FAZA 4 - Python backend skeleton

## Datum

2026-07-05

## Scope

Implementirana je samo FAZA 4 iz `docs/MIGRATION_PLAN.md`: minimalni Python FastAPI backend pod `python_backend/` sa endpointima `/health`, `/tools` i `/tools/execute`, dummy `echo` toolom i backend testovima.

Nije povezivan Electron sa Python backendom. Nije mijenjan `src/lib/realtime.ts`. Nije dodavan novi IPC kanal. Nije implementirana FAZA 5 ili kasnije faze.

## GitNexus impact

GitNexus repo `nas_agent` je dostupan, ali je indeks prijavljen kao 1 commit iza HEAD-a. PokuÅ¡aj osvjeÅ¾avanja indeksa je prekinut korisniÄkim interruptom prije izmjena.

Nisu mijenjani postojeÄ‡i funkcionalni simboli aplikacije. Dodati su novi Python moduli pod `python_backend/`, a `.gitignore` je dopunjen Python cache/build ignore pravilima. Blast radius je nizak: postojeÄ‡i Electron/React runtime i legacy PowerShell toolovi nisu povezani sa novim backendom u ovoj fazi.

## Å ta je uraÄ‘eno

- Dodan `python_backend/pyproject.toml` sa FastAPI/Pydantic/Uvicorn/pytest/httpx dependency setom.
- Dodan `python_backend/app/main.py` i FastAPI app factory.
- Dodani endpointi:
  - `GET /health`
  - `GET /tools`
  - `POST /tools/execute`
- Dodan minimalni tool registry i executor.
- Dodan dummy `echo` tool po contract smjeru.
- Dodane Pydantic Å¡eme za health, tool definition, execute request/response i error response.
- Dodani testovi za health, tool listing, echo execution i unknown tool error.
- Dopunjen `.gitignore` za Python venv/cache/egg-info artefakte.

## ZaÅ¡to je uraÄ‘eno

FAZA 4 treba da uvede prazan, ali funkcionalan Python backend koji se joÅ¡ ne spaja na Electron. Ovo pravi osnovu za kasnije faze bez rizika po postojeÄ‡i voice-first UI i legacy Windows toolove.

## Kako je uraÄ‘eno

Backend je modularno podijeljen na:

- `app/api/` za FastAPI route module
- `app/agent/` za tool registry i executor
- `app/core/` za config/logging/error hookove
- `app/schemas/` za Pydantic contract Å¡eme
- `tests/` za pytest testove

`echo` tool je low-risk dummy tool i samo vraÄ‡a `{"text": <input>}`.

## Å ta nije dirano

- Nije diran `electron/main.cjs` za ovu fazu.
- Nije diran renderer/UI.
- Nije diran `src/lib/realtime.ts`.
- Nije dodan Python process manager.
- Nisu migrirani realni toolovi.
- Nije dodan permission/risk layer iz kasnijih faza.
- Nisu dirane postojeÄ‡e dokumentacione izmjene koje su veÄ‡ bile u worktree-u.

## Verifikacija

Pokrenuto iz `python_backend/`:

```text
python -m pip install -e .
python -m pytest
```

Rezultat:

```text
4 passed, 1 warning
```

Warning dolazi iz FastAPI/Starlette `TestClient` dependency lanca za Python 3.14/httpx i ne ruÅ¡i FAZU 4 acceptance criteria.

## Rizici/ograniÄenja

- Dependency install je uraÄ‘en u globalni Python 3.14 environment, ne u `.venv`, jer venv nije postojao.
- GitNexus indeks nije osvjeÅ¾en jer je korisnik prekinuo `npx gitnexus analyze`.
- Backend za sada nema local auth token, storage, permission layer ni Electron process management; to pripada kasnijim fazama/security gateovima.

## Potreban follow-up

- FAZA 5 treba dodati Electron-side Python process management.
- Prije commita poÅ¾eljno je ponovo pokrenuti GitNexus detect/refresh ako korisnik dozvoli.
- Po potrebi kreirati `.venv` i prebaciti dependency install iz globalnog Python-a u lokalni virtualenv.

## Potrebna korisniÄka potvrda

Prije commita treba potvrditi kako tretirati postojeÄ‡i dirty worktree koji sadrÅ¾i brojne dokumentacione izmjene i promjene koje nisu dio FAZE 4.