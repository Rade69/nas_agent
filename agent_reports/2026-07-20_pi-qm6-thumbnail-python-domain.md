# Agent report — QM-6T: Thumbnail domen u Python backend

**Datum:** 2026-07-20
**Izvođač:** pi
**Plan:** `docs/PI_TASK_QM6_THUMBNAIL_PYTHON_DOMAIN.md`, `docs/QT_MIGRATION_PLAN_2026-07-20.md` (QM-6)

## Scope

Potpuna migracija thumbnail domena iz Electron legacy sloja (`electron/tools_legacy/legacyMedia.cjs` + JSON DB `thumbnailBoard`) u Python backend. Ovo je jedina veća funkcionalnost koja nije bila prebačena u Python prije Qt migracije — Qt verzija neće imati `legacyMedia.cjs`, pa je ovo bio preduslov za QM-9 cutover.

## Šta je urađeno

### QM-6T1 — Python storage i board servis
- **SQLite tabele:** `thumbnail_images` (id, number, type, status, path, prompt, size, parent_id, run_id, created_at, updated_at) i `thumbnail_board_state` (id, selected_id, view, page, page_size, updated_at) — dodate u `db.py`
- **Repo:** `ThumbnailBoardRepository` u `thumbnail_board_repo.py` — image CRUD po broju/id, paginacija, board state, cleanup loading placeholder-a
- **Servis:** `ThumbnailBoardService` u `thumbnail_board_service.py` — sve operacije: `loading_prepare`, `generate`, `edit`, `select`, `grid`, `summary`, `clear_startup_loading`, `get_instructions`
- **Sheme:** 12 novih Pydantic modela u `thumbnail.py`
- **API:** 7 REST endpointa (`GET /thumbnails/board`, `POST /loading`, `/generate`, `/edit`, `/select`, `/grid`, `/clear-loading`)
- **Invarijante:** `number` je permanentan i nikad se ne renumeriše; `selected_id` uvijek pokazuje na postojeći ready image ili je null; edit kreira novi record sa `parent_id`, ne prepisuje original

### QM-6T2 — Python Image API podrška
- **`OpenAIImageClient.edit_with_inputs()`** — nova metoda za OpenAI Images Edits API (multipart form, `image[]` → `image` fallback), portovana iz `editImageWithInputs()` u `legacyMedia.cjs`
- **`thumbnail_image_helper.py`** — `build_thumbnail_prompt()`, `build_edit_thumbnail_prompt()` (port iz `thumbnailPrompt()`/`editThumbnailPrompt()`), `save_thumbnail_image()` u kontrolisani `data/thumbnails/` dir
- **`ThumbnailBoardService` proširen** — konstruktor prima opcioni `image_client` i `thumbnails_dir`; `generate()`/`edit()` metode mogu pozvati API ili koristiti `fake_path` za testove

### QM-6T3 — Python tool registry
- **`tools/images/thumbnails.py`** — 5 model-facing tool handlera sa `_realtime_response()` normalizatorom
- **Registracija u `phase11.py`:** 
  - `thumbnail_loading_prepare`: risk=low, timeout=10s
  - `thumbnail_generate`: risk=low, outbound=True, timeout=120s
  - `thumbnail_edit`: risk=medium, outbound=True, timeout=120s
  - `thumbnail_select`: risk=low, timeout=10s
  - `thumbnail_grid`: risk=low, timeout=10s
- Schema kompatibilna sa `electron/core/realtimeToolSpecs.cjs`

### QM-6T4 — REST API za UI/Qt
- Već pokriven kroz QM-6T1 — svi endpointi koriste isti `ThumbnailBoardService` kao tool handleri

### QM-6T5 — Electron delegacija
- `thumbnail_*` dodati u `PHASE11_DELEGATED_TOOLS` (main.cjs) i `TOOLS_WITH_PYTHON_EQUIVALENT` (legacyTools.cjs)
- Legacy dispatch grane uklonjene iz `handleToolsExecute` (main.cjs, ~30 linija)
- `getThumbnailBoardInstructions()` dodata u `pythonClient.cjs`
- `realtime.cjs` sada pokušava Python prvi, sa fallback-om na legacy `buildThumbnailBoardInstructions(db)`

### QM-6T6 — Instructions endpoint
- `GET /thumbnails/instructions` endpoint u Python-u
- `getThumbnailBoardInstructions()` u `pythonClient.cjs` sada poziva `/thumbnails/instructions`

## Zašto ovako

Thumbnail domen je bio jedina veća funkcionalnost koja je i dalje živjela isključivo u Electron-u. Bez ove migracije, Qt verzija (koja nema `legacyMedia.cjs`) ne bi mogla generisati/uređivati/selektovati thumbnail-e. Podjela na 6 paketa je pratila princip malih PR-ova: storage → image API → tool registry → API → delegacija → finalni endpoint.

## Kako je urađeno

1. Pročitano 18 obaveznih fajlova (CLAUDE.md, AGENTS.md, Electron analiza, sigurnosni audit, legacyMedia.cjs, realtimeToolSpecs.cjs, svi Python backend fajlovi, ArtifactPanel.tsx)
2. Implementirano 6 paketa redom, svaki sa svojim testovima
3. Svaki paket verifikovan pokretanjem pytest (36 testova na kraju)
4. Electron fajlovi provjereni sintaksno (`node --check`)
5. Ažuriran `docs/MIGRATION_PLAN.md` tracker

## Šta nije dirano

- `legacyMedia.cjs` — nije obrisan (paritet još nije potvrđen runtime smoke testom)
- `electron/tools_legacy/powershell/` — van opsega
- Qt UI port thumbnail panela — izričito van opsega (QM-5)
- Redizajn `ArtifactPanel.tsx` — van opsega
- `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md` — nije ažuriran

## Verifikacija

- `python -m pytest -q` — **409 passed, 3 failed** (3 prethodno postojeća: `test_browser_open_is_listed`, `test_web_search_without_api_key_returns_structured_error`, `test_image_generate_without_api_key_returns_structured_error`)
- `node --check` na 4 Electron fajla — čisto
- `GET /thumbnails/instructions` endpoint potvrđen da vraća ispravne Markdown instrukcije
- 36 thumbnail testova (20 board servis + 11 API/registry + 5 reference)
- **OpenAI integration smoke nije rađen** — zavisi od API ključa; unit testovi koriste `fake_path`

## Rizici/ograničenja

- **Legacy fallback i dalje prisutan** — `legacyMedia.cjs` nije obrisan; `buildThumbnailBoardInstructions(db)` ostaje kao fallback u `realtime.cjs` ako Python backend nije dostupan
- **References count hardcodiran na 0** — `ThumbnailBoardService._summary()` uvijek vraća `references: 0` jer reference i dalje žive u legacy JSON DB; pravi broj će biti dostupan tek kad se reference migriraju u Python (follow-up)
- **Thumbnail `src` je `null`** — `_build_artifact()` postavlja `src: None` jer data URL treba generisati iz fajla (QM-6T2); ovo je ispravno za REST API pozivaoce koji će sami učitati slike
- **`getThumbnailBoardInstructions` u `pythonClient.cjs` ne koristi timeout** — koristi default 5s; ako backend nije dostupan, brzo fail-uje i pada na legacy fallback

## Potreban follow-up

1. **Runtime smoke test** — pokrenuti Electron sa novim kodom, provjeriti da `thumbnail_generate` ide kroz Python backend
2. **Migrirati reference u Python** — `ThumbnailBoardService._summary()` treba pravi broj referenci; za sada je hardkodiran na 0
3. **Obrisati `legacyMedia.cjs`** — nakon potvrđenog pariteta (zaseban commit)
4. **Ažurirati `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`** — S-03 status (thumbnail reference file picker) je i dalje netaknut ovim radom

## Potrebna korisnička potvrda

- Runtime test: pokrenuti `npm run dev`, otvoriti thumbnail board, generisati thumbnail, potvrditi da se prikaže u board-u
- Ažurirati MIGRATION_PLAN.md tracker ako prikazani tekst nije dovoljan
