# FAZA 16 — Prebacivanje OpenAI/Exa/image poziva u Python

## Datum

2026-07-05

## Scope

Implementirana je FAZA 16 iz `docs/MIGRATION_PLAN.md`: migracija `web_search` (Exa) i `image_generate` (OpenAI gpt-image) integracija iz Electron main procesa u Python backend.

Nije diran audio pipeline (`src/lib/realtime.ts`). Nije diran FAZA 10 permission engine / FAZA 11 tool registry / FAZA 12 companion orb. Thumbnail alati (`thumbnail_generate`/`thumbnail_edit`/`thumbnail_reference_add`) NISU migrirani — oni ovise o Electron-side JSON db `thumbnailBoard` state-u koji je van scope-a ove faze (i plan to ne traži — "OpenAI/Exa/image" = web_search + image_generate).

## GitNexus impact

Prije izmjene pokrenut je `npx gitnexus impact` (CLI, `--repo nas_agent`) na ključnim simbolima:

- `handleToolsExecute` → risk **LOW**, 0 impaktovanih, 0 procesa.
- `create_default_registry` → risk **LOW**, 2 impaktovana, 1 modul.
- `create_app` → risk **LOW**, 1 impaktovani.

Sve izmjene su aditivne (novi moduli + proširenje wire-ovanja). Nakon izmjene indeks je osvježen (`npx gitnexus analyze`).

## Šta je urađeno

### Backend (Python)

- **`app/services/exa_client.py`** (novi) — `ExaClient` HTTP wrapper za `https://api.exa.ai/search`. `available` property, `search(query, num_results, max_characters, timeout)` metoda. API ključ iz `settings.exa_api_key`. Greške kao strukturirani `AppError` (`EXA_REQUEST_FAILED`, `MISSING_API_KEY`).
- **`app/services/openai_image_client.py`** (novi) — `OpenAIImageClient` HTTP wrapper za `https://api.openai.com/v1/images/generations` (model `gpt-image-2`). `generate(prompt, size, quality, model, timeout)` vraća `{b64_json, url}`. Reuse-uje isti `OPENAI_API_KEY` koji backend već drži za FAZA 6 realtime session.
- **`app/tools/web/search.py`** (novi) — `web_search` handler: validira query, zove `ExaClient.search`, renderuje rezultate kao Markdown research brief artifact (isti format kao legacy Electron `formatSearchMarkdown()`).
- **`app/tools/images/generate.py`** (novi) — `image_generate` handler: validira prompt, zove `OpenAIImageClient.generate`, čuva base64 PNG u `data/images/`, vraća image artifact (data URI ili URL — isto kao legacy).
- **`app/tools/web/__init__.py`**, **`app/tools/images/__init__.py`** — package init.
- **`app/core/config.py`** — dodato `Settings.exa_api_key` (čita `EXA_API_KEY` env var).
- **`app/agent/tool_registry.py`** — `_register_phase11_tools` sada registruje i `web_search` (timeout 30s) i `image_generate` (timeout 90s). `_def` helper proširen sa `timeout_ms` parametrom.
- **`app/main.py`** — `phase11_services` dict sada uključuje `exa_client`, `openai_image_client`, `images_dir`.

### Electron (delegacija)

- **`electron/main.cjs`** — `PHASE11_DELEGATED_TOOLS` set proširen sa `web_search` i `image_generate`. Legacy handleri (`webSearch()`, `generateImage()`) ostaju kao fallback ako backend faila (po MIGRATION_PLAN.md "Keep legacy implementations available").
- Legacy Electron funkcije `webSearch()`/`generateImage()` nisu obrisane — ali se ne pozivaju osim ako Python backend nije nedostupan.

### Testovi

- **`tests/test_phase16_integrations.py`** (novi) — 7 testova:
  - `/tools` lista sadrži `web_search` i `image_generate`
  - tool definicije: low risk, no confirmation, duži timeout (30s/90s)
  - `web_search` bez `EXA_API_KEY` → strukturirani `MISSING_API_KEY` (500)
  - `image_generate` bez `OPENAI_API_KEY` → strukturirani `MISSING_API_KEY` (500)
  - `web_search` sa praznim query → `INVALID_ARGUMENTS`
  - `image_generate` sa praznim prompt → `INVALID_ARGUMENTS`

## Zašto je urađeno

Arhitektonsko pravilo: Electron main proces je samo shell/IPC/process-manager — svi AI/eksterni API pozivi trebaju biti u Python backendu. Ovo zatvara posljednji dio "Electron ima direktnu AI service logiku" — sada su OpenAI (realtime session iz FAZE 6 + image generation ovdje) i Exa (web search) isključivo na backend strani, iza Security PR-1 local auth tokena.

## Kako je urađeno

- **API ključevi na backendu**: `OPENAI_API_KEY` (već korišten u FAZI 6) i `EXA_API_KEY` (novi) se čitaju iz env-a u `get_settings()`. Electron proslijeđuje oba preko `...process.env` pri spawn-u Python procesa (postojeći mehanizam iz `pythonProcess.cjs`). Ključevi se nikad ne loguju, nikad ne napuštaju backend.
- **Strukturirane greške**: `ExaClient`/`OpenAIImageClient` bacaju `AppError` sa specifičnim kodovima (`MISSING_API_KEY`, `EXA_REQUEST_FAILED`, `IMAGE_REQUEST_FAILED`, `IMAGE_RESPONSE_INVALID`). FastAPI exception handler vraća `{ok: false, error: {code, message}}` — UI dobija čistu grešku, ne raw HTTP text.
- **Markdown artifact format**: `_format_search_markdown()` je port legacy `formatSearchMarkdown()` iz Electron-a — isti output, tako da ArtifactPanel prikazuje identičan research brief.
- **Image output kao artifact**: per IMPLEMENTATION_PLAN FAZA 15 pravilo 4, base64 PNG se čuva u `data/images/` i vraća kao `data:image/png;base64,...` artifact content (UI ga prikazuje direktno).
- **Timeout**: `web_search` (mrežni poziv) = 30s, `image_generate` (generacija) = 90s — registrisano u `ToolDefinition.timeout_ms`.

## Šta nije dirano

- Nije diran `src/lib/realtime.ts` (audio pipeline).
- Nije diran FAZA 10 permission engine / cancellation registry.
- Nisu migrirani thumbnail alati (`thumbnail_generate`/`thumbnail_edit`/`thumbnail_reference_add`/`thumbnail_grid`/`thumbnail_select`/`thumbnail_loading_prepare`) — oni ovise o Electron-side JSON db `thumbnailBoard` state-u (references, images, page, selectedId) koji nije deo FAZE 16 scope-a. Migracija thumbnail board-a bi zahtijevala prebacivanje cijelog board state-a u SQLite, što je zaseban posao.
- Nije obrisana legacy Electron `webSearch()`/`generateImage()` funkcija (fallback).
- Nije diran `set_mode`/`artifact_show`/`show_menu`/`mermaid_render` (Electron-side, van scope-a).

## Verifikacija

Pokrenuto:

```text
cd python_backend && python -m pytest -q
npm run typecheck
npm run build
node --check electron/main.cjs
node smoke (backend + REST round-trip web_search sa pravim Exa ključem)
```

Rezultati:

```text
pytest: 72 passed (65 postojećih + 7 novih FAZA 16), 1 warning (FastAPI TestClient deprecation)
typecheck: prošao (tsc --noEmit bez grešaka)
build: prošao (vite/rolldown)
node --check: čist
node smoke:
  - web_search/image_generate registrovani u /tools
  - web_search sa pravim Exa ključem: ok=true, vraća rezultate + markdown artifact
```

## Rizici/ograničenja

- **Testovi ne trefile prave API-je**: fixture postavlja `EXA_API_KEY=""` i `OPENAI_API_KEY=""` — ključevi iz `.env.local` se override-uju na prazan string, tako da testovi uvijek dobijaju `MISSING_API_KEY` umjesto realnog API poziva. Ovo je važno jer `.env.local` sadrži prave ključeve (koji nisu u git-u, ali bi test bez override-a trefio pravi API i trošio kvotu).
- **Legacy fallback**: ako backend faila, `web_search`/`image_generate` padaju na legacy Electron handler koji i dalje drži ključeve u `process.env`. Ovo znači da ključevi nisu *potpuno* izbačeni iz Electron-a — ali je to namjerno (MIGRATION_PLAN.md traži fallback dok se Python verzije ne verifikuju). FAZA 17 (deaktivacija legacy) će ih konačno ukloniti.
- **Thumbnail alati ostaju u Electron-u**: kako je napomenuto, oni ovise o JSON db state-u koji nije migriran. Ako se kasnije odluči migrirati thumbnail board, to bi bila zasebna faza.
- **AppError vs ToolExecutionResponse**: `MISSING_API_KEY` se vraća kao HTTP 500 (ne kao `ok: false` u 200 response-u) jer `ToolExecutor` hvata samo `ValueError`, ne `AppError`. Ovo je ispravno — `MISSING_API_KEY` je server misconfiguration, ne tool execution failure. UI dobija strukturiranu grešku preko FastAPI exception handler-a.

## Sigurnosna napomena

Tokom razvoja otkrio sam da `.env.local` sadrži **prave API ključeve** (OpenAI `sk-proj-...`, Exa `fd0f0eef-...`). Ključevi nisu u git-u (`.gitignore` pokriva `.env.*` osim `.env.example`), ali su dostupni lokalnim procesima. Test fixture ih override-uje na prazan string da se ne trefi pravi API. Preporuka: rotirati ključeve ako je `.env.local` ikad bio commitovan u prošlosti (provjereno — nije).

## Potreban follow-up

- **FAZA 17** (deaktivacija legacy PowerShell toolova) je sljedeća: sad kad su `web_search`/`image_generate` u Pythonu, legacy Electron handleri se mogu disable-ovati default-no (zadržati iza `RICKY_USE_LEGACY_POWERSHELL_TOOLS` flag-a).
- **Thumbnail board migracija**: ako se želi potpuno izbaciti Electron-side AI logika, thumbnail board state treba prebaciti u SQLite (zasebna faza, nije u trenutnom planu).
- **Mock testovi za prave API pozive**: dodati testove sa `httpx.MockTransport` koji testiraju `ExaClient.search`/`OpenAIImageClient.generate` sa mock-ovanim uspješnim odgovorom (trenutni testovi pokrivaju samo error path-ove).

## Potrebna korisnička potvrda

Prije commita treba potvrditi:

1. Da li želite da dodam mock testove za uspješne API pozive (`httpx.MockTransport`) ili su error-path testovi + node smoke dovoljni za ovu fazu?
2. Da li da u ovoj fazi disable-ujem legacy Electron `webSearch()`/`generateImage()` iza `RICKY_USE_LEGACY_ELECTRON_AI` flag-a, ili to ostavim za FAZU 17?
3. Worktree sadrži nepratene `assets/Ricky-agent-3.png`, `assets/Ricky-agent-4-lokalizacija-podesavanje.png` — ostaju van commit-a kao i ranije?
