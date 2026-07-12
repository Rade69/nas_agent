# Agent report — Security Gate 1: dev-mode auth fail-closed + S-2 outbound eskalacija

**Datum:** 2026-07-12
**Scope:** `python_backend/app/core/{auth,config}.py`, `python_backend/app/schemas/tool.py`,
`python_backend/app/agent/permission_engine.py`, `python_backend/app/agent/tool_catalog/phase11.py`,
`python_backend/tests/conftest.py` (novo), 13 postojećih test fajlova, `docs/{PROJECT_OVERVIEW,MIGRATION_PLAN,SECURITY_MODEL}.md`.

**Povod:** Korisnik je eksplicitno izabrao ovo kao sljedeći prioritet nakon pregleda `docs/MIGRATION_PLAN.md` trackera — dvije stavke iz FABLE-5 eksternog pregleda (2026-07-12) koje su u `PROJECT_OVERVIEW.md` bile dokumentovane kao poznate, nepopravljene praznine.

## GitNexus impact

`mcp__gitnexus__detect_changes(repo: "nas_agent", scope: "all")` prije commita — risk level "low", `affected_processes: []`. Dotaknuti simboli tačno odgovaraju obimu izmjene (auth/config/permission_engine/tool schema + test fixture-i).

## Šta je urađeno

### 1. Dev-mode auth fail-open → uvijek fail-closed

- `app/core/config.py`: nova `_resolve_local_token(data_dir)` — ako `RICKY_LOCAL_TOKEN` env nije postavljen (dev `uvicorn` bez Electron-a), generiše `secrets.token_urlsafe(32)` i upisuje ga u gitignored `data/dev_local_token.txt` (već pokriveno postojećim `data/` pravilom u `.gitignore`, provjereno). `get_settings()` sad uvijek poziva ovu funkciju umjesto da ostavi `local_token=None`.
- `app/core/auth.py`: `require_local_token()` više nema `if not expected: return` fail-open granu — uvijek zahtijeva ispravan `Bearer` header.
- **Pravi obim je bio veći nego procijenjeno ("jeftin fix").** Skoro cijeli backend test suite (245 od 245 tadašnjih testova) implicitno je zavisio od fail-open ponašanja preko dijeljene `app.main.app` singleton instance i preko 13 `create_app()` fixture-a koji nikad nisu slali `Authorization` header. Popravljeno:
  - Novi `tests/conftest.py` — jedan `dependency_overrides` bypass za singleton `app.main.app` (pogađa ~4 fajla koji ga direktno importuju).
  - 11 fajlova (`test_agent_runtime`, `test_confirmations`, `test_events`, `test_phase11_tools`, `test_phase13_computer_tools`, `test_phase14_element_targeting`, `test_phase16_integrations`, `test_plans`, `test_screenshots`, `test_security_redteam`, `test_text_rewrite`) dobili su eksplicitan `app.dependency_overrides[require_local_token] = lambda: None` u svom `create_app()` fixture-u — ovi testovi provjeravaju poslovnu logiku, ne auth, pa dobijaju svjestan, dokumentovan bypass umjesto da uče o tokenima.
  - `test_auth.py` i `test_security_self_test.py` **namjerno nisu dobili bypass** — oni testiraju stvarnu auth logiku i sad su prepisani da odražavaju novo ponašanje: `test_no_env_token_still_fails_closed` (401 bez env tokena), `test_no_env_token_auto_generates_and_persists_one` (regresioni test — token fajl postoji, sadržaj se poklapa sa `app.state.settings.local_token`, ispravan Bearer header prolazi), `test_self_test_passes_auth_check_even_without_env_token` (self-test `backend_auth_token_configured` sad prolazi i bez env tokena), plus jedan unit-level test (`test_check_logic_reports_missing_token_and_redaction_for_bare_settings`) koji direktno poziva `run_backend_self_test()` sa "praznim" `Settings` objektom da provjera-logika ostane testirana i dalje, iako više nije dostiživa kroz normalan `create_app()` put.

### 2. S-2 eskalacija: rupa za "odlazne" low-risk alate

- `app/schemas/tool.py`: novo `outbound: bool = False` polje na `ToolDefinition`.
- `app/agent/permission_engine.py`: `check_permission()` sad ima drugu, nezavisnu eskalacionu granu — `external_content_seen and tool.outbound → requires_confirmation = True`, nezavisno od risk nivoa i nezavisno od `reads_external_content` izuzeća (alat može biti i reader i outbound istovremeno).
- `app/agent/tool_catalog/phase11.py`: `_def()` helper proširen sa `outbound` parametrom; `web_search` i `image_generate` sad označeni `outbound=True`.
- Novi testovi: 3 unit testa u `test_permission_engine.py` (outbound low-risk eskalira, outbound+reader kombinacija eskalira, plain non-outbound low-risk NE eskalira — regresiona zaštita), end-to-end red-team test u `test_security_redteam.py` (read → outbound low-risk chain se blokira, isti obrazac kao postojeći `test_injection_chain_read_then_act_is_blocked`), i 2 nove asercije u `test_phase16_integrations.py` (`outbound: true` u `/tools` odgovoru za oba stvarna alata).

## Zašto ovako

- `data_dir`-based token fajl umjesto env var ili stdout ispisa — developer koji ručno pokreće `uvicorn` bez Electron-a može pročitati fajl (`python_backend/data/dev_local_token.txt`) za curl/frontend testiranje, bez da se token ikad loguje.
- Eksplicitan `dependency_overrides` bypass po test fajlu (umjesto globalnog monkeypatch-a `create_app`) — globalni pristup bi tiho isključio auth i za `test_auth.py`/`test_security_self_test.py`, poništavajući baš ono što ti testovi treba da dokažu. Mehanički rad na 11 fajlova je sporiji, ali svaki fajl eksplicitno i vidljivo bira bypass, ne nasljeđuje ga slučajno.
- `outbound` kao zaseban bool umjesto proširenja postojećeg `reads_external_content` — jedan alat (`web_search`) je oba istovremeno (čita nepouzdane rezultate NAZAD, šalje potencijalno zatrovan upit VAN), pa spajanje u jedno polje ne bi moglo izraziti tu kombinaciju.

## Šta nije dirano

- `electron/services/pythonProcess.cjs` — Electron-pokrenut put i dalje generiše i prosljeđuje `RICKY_LOCAL_TOKEN` isto kao prije, nedotaknut ovom izmjenom (fix je isključivo za dev-bez-Electron granu).
- Legacy PowerShell computer-use rezidualni gap (medium-risk alati bez `LEGACY_FAIL_CLOSED_TOOLS`) — ostaje van obima, dokumentovano u `PROJECT_OVERVIEW.md` sekcija 4.7.
- `python_backend/README.md` — već zastario na više mjesta (npr. "FAZA 4 intentionally does not connect this backend to Electron"), nije ažuriran u ovom prolazu, van obima.
- `docs/MIGRATION_PLAN.md` Gate 0 red i dalje sadrži zastarjelu tvrdnju o legacy PowerShell computer-use "bez auth tokena" — poznato, van obima ovog fix-a (isti tip greške kao ranija PROJECT_OVERVIEW.md ispravka, ali nije bio dio korisnikovog izabranog prioriteta ovog puta).

## Verifikacija

- `python -m pytest -q` (cijeli `python_backend` suite) — 251 passed (245 prije + 6 novih: 2 u test_auth.py, 3 u test_permission_engine.py, 1 end-to-end u test_security_redteam.py; plus izmijenjeni test_security_self_test.py zadržao isti broj testova uz jedan novi).
- Frontend nije dotaknut ovim fix-om (backend-only) — `npm run typecheck`/`build` nisu ponovo pokretani jer nema izmjena u `src/`/`electron/`.

## Rizici/ograničenja

- `secrets.token_urlsafe(32)` se generiše iznova pri SVAKOM `create_app()` pozivu kad env token nedostaje (uklj. svaki test) — namjerno, matches Electron-pokrenutog ponašanja (novi token po sesiji), ali znači da stari `dev_local_token.txt` sadržaj postaje neispravan čim se backend restartuje bez Electron-a; developer mora ponovo pročitati fajl poslije svakog restart-a.
- `outbound` polje je ručno dodano samo na `web_search`/`image_generate` — svaki budući alat koji poziva eksterni servis mora eksplicitno postaviti `outbound=True`; nema automatske detekcije (npr. statička analiza za mrežne pozive unutar handler-a) da spriječi da se ovo zaboravi kod novog alata.

## Potreban follow-up

Nema hitnog — oba nalaza iz FABLE-5 pregleda (2026-07-12) su sad zatvorena. Preostali Security Gate 1 gapovi (document privacy modes, rate limiting, CI security checks, dependency scanning) i dalje nisu pokriveni — vidi `docs/MIGRATION_PLAN.md` "Security Gates" tabelu.

## Potrebna korisnička potvrda

Nije potrebna runtime provjera korisnika — ovo je backend-only sigurnosna izmjena, potpuno pokrivena test suite-om (251/251 prolazi).
