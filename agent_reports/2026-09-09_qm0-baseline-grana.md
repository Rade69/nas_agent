# QM-0 — baseline i postavka grane (Qt Desktop Migration)

## Datum

2026-09-09

## Scope

QM-0 iz `docs/QT_MIGRATION_PLAN_2026-07-20.md` — zaključati polaznu tačku Qt Desktop migracije: nova grana, pokretljiv `desktop/` skelet, baseline, formalni zapis obaveznih arhitektonskih odluka u tracker.

## GitNexus impact

GitNexus MCP alati nisu dostupni u ovom okruženju (nema `gitnexus_*` toolova), pa je urađena ručna analiza. Blast radius je ~nula: QM-0 dodaje samo novi `desktop/` skelet (dva nova fajla) i proširuje `docs/MIGRATION_PLAN.md` — ne dira postojeći `python_backend/`, `electron/`, `src/` niti bilo koji postojeći simbol. Nema HIGH/CRITICAL rizika.

## Šta je urađeno

1. **Grana `qt-desktop-migration`** kreirana iz `hybrid-python-backend` (HEAD `880e6b0`), ne iz `master` — čuva cijelu `python_backend/` osnovu (105+ .py fajlova, 412 testova) bez ponovnog prenošenja.
2. **`desktop/` skelet** — `desktop/__init__.py` (paketni docstring) + `desktop/main.py` (composition root: `create_app()` + `main()`, prazan PySide6 `QMainWindow` "Ricky" 400×300). File-header docstring po CLAUDE.md konvenciji.
3. **Obavezne odluke §2.1–2.3 zapisane u `docs/MIGRATION_PLAN.md`** kao nova sekcija (QM-0 baseline + QM faze status tabela): dva procesa za v1 (Opcija A), PySide6 Widgets, WebSocket glas.
4. **Baseline snimljen:** Python 3.14.1, PySide6 6.11.1, PyInstaller 6.20.0 + Nuitka dostupni, backend `pytest` = 412 passed. Spike polazne tačke potvrđene: `spikes/voice_websocket_spike.py`, `spikes/pyside6_orb_spike.py`.

## Zašto je urađeno

Qt migracija ne smije krenuti bez pouzdane polazne tačke i zelenog testnog signala. Grana forkovana iz `hybrid-python-backend` (a ne `master`) jer tamo živi cijela stvarna baza; odluka o dva procesa (Opcija A) morala je biti zapisana u tracker jer je to jedini izvor istine za status, a sprječava da kasnije faze (QM-2/QM-3) grade na neraspetljenoj asyncio+Qt koegzistenciji.

## Kako je urađeno

`git checkout -b qt-desktop-migration` iz čistog working tree-a (prethodno nekomitovano stanje riješeno u `880e6b0`). Skelet napisan minimalno: `create_app()` razdvojen od `main()` radi testabilnosti (offscreen provjera bez ulaska u event loop). Tracker sekcija umetnuta uz postojeći QM-6T blok, prije Security Gates.

## Šta nije dirano

- `python_backend/` — netaknut (0 izmjena).
- `electron/`, `src/` — netaknuti (brisanje tek nakon QM-9 cutover potvrde, invarijanta §4.8).
- `docs/QT_MIGRATION_PLAN_2026-07-20.md` — nije mijenjan (odluke su već bile tamo; ovdje samo preslikane u tracker).
- QM-1 i dalje faze — nisu dirane.

## Verifikacija

- `git branch --show-current` → `qt-desktop-migration`; `git log --oneline -3` potvrđuje fork iz `880e6b0`.
- `desktop/` skelet se pokreće: `QT_QPA_PLATFORM=offscreen python -c "from desktop.main import create_app; ..."` → "SKELET OK — title: Ricky | size: 400 x 300".
- Backend baseline: `python -m pytest -q` → **412 passed** (104.55s), jedino postojeće Starlette `httpx2` deprecation warning.

## Rizici/ograničenja

- Skelet je provjeren samo offscreen (headless okruženje) — pravi prozor na desktopu nije vizuelno potvrđen od strane agenta.
- Grana još nije push-ana u trenutku pisanja (push ide u istom commitu, po korisničkoj instrukciji).
- Baseline broj testova (412) razlikuje se od broja 236 u izvornom planu — to je stvarno trenutno stanje (projekat je narastao od pisanja plana), ne odstupanje od plana.

## Potreban follow-up

- QM-1 — Process bridge (`desktop/core/process_bridge.py`): spawn backend-a preko `sys.executable --backend` (frozen-safe od dana jedan), Windows Job Object za garantovano gašenje djeteta, health check prije prozora, Bearer token preko env (nikad komandna linija).
- Eventualni `git push -u origin qt-desktop-migration` (ovaj commit).

## Potrebna korisnička potvrda

- Da li da grana `qt-desktop-migration` ostane isključivo lokalna ili da se push-uje na remote (odluka je već data: push).
- QM-1 je po planu moj posao (§5.1, sigurnosno osjetljiv) — potvrda da se kreće na QM-1 nakon ovoga.
