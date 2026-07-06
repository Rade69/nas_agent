# Agent report — Security Gate 0: log redaction, path sandbox, security self-test MVP

**Datum:** 2026-07-06

## Scope

Zatvaranje preostalih stavki Security Gate 0 (`docs/SECURITY_HARDENING_PLAN.md` sekcija 2) koje su blokirale FAZA 13/14 (computer-use). Namjerno **isključen** iz obima: active window enforcement (vidi "Šta nije dirano").

Novi/izmijenjeni fajlovi:
- `python_backend/app/core/logging.py` (izmijenjen) — `SecretRedactionFilter`
- `python_backend/app/core/path_sandbox.py` (novo)
- `python_backend/app/core/security_self_test.py` (novo)
- `python_backend/app/api/security.py` (novo) — `GET /security/self-test`
- `python_backend/app/main.py` (izmijenjen) — wiring
- `electron/core/secureWebPreferences.cjs` (novo)
- `electron/core/window.cjs`, `electron/core/companionWindow.cjs` (izmijenjeni) — koriste zajedničku funkciju
- `electron/core/securitySelfTest.cjs` (novo)
- `electron/services/pythonClient.cjs` (izmijenjen) — `getSecuritySelfTest()`
- `electron/main.cjs` (izmijenjen) — self-test poziv u `app.whenReady()`, fail-closed u produkciji
- `scripts/smoke-test.cjs` (izmijenjen) — novi korak 3/7
- `package.json` (izmijenjen) — `check` skripta uključuje nove `.cjs` fajlove
- 24 nova testa: `python_backend/tests/test_security_self_test.py` (3), `test_path_sandbox.py` (11), plus postojeći test file-ovi netaknuti

## GitNexus impact

Prije izmjene: `gitnexus_impact` na `createWindow`, `createCompanionWindow` (oba LOW risk, jedini pozivalac `main.cjs`, samo interni webPreferences objekat mijenjan, ne potpis) i `configure_logging` (LOW risk, jedini pozivalac `create_app`).

Nakon izmjene: `gitnexus_detect_changes` → risk **HIGH**, ali za razliku od prethodnih lažnih uzbuna ove sesije (širina preko `App`/root simbola), ovaj put je HIGH **stvaran i očekivan** — dotaknuti su pravi ulazni tokovi (`createWindow`, `createCompanionWindow`, `create_app`, Electron `app.whenReady()` startup lanac) jer self-test namjerno sjedi na startu aplikacije. Pregledani svi prijavljeni "affected_processes" — svi vode direktno na kod koji sam stvarno izmijenio (companion window kreiranje, click/toggle handleri koji pozivaju `createCompanionWindow`), ne na nepovezane funkcije koje dijele isti roditeljski simbol.

## Šta je urađeno

**1. Log redaction** (`app/core/logging.py`): `SecretRedactionFilter` zamjenjuje stvarne vrijednosti (`OPENAI_API_KEY`, `EXA_API_KEY`, `RICKY_LOCAL_TOKEN`) sa `[REDACTED]` u svakom log zapisu. `configure_logging(secrets=[...])` sad prima listu tajni iz `Settings` i kači filter na root logger; svaki poziv prvo uklanja filtere iz prethodnog poziva (bitno za testove gdje se `create_app()` zove više puta u istom procesu — pravi proces to radi samo jednom).

**Stvaran bug nađen i ispravljen tokom rada**: prvobitna implementacija je provjeravala `if secrets:` na listi OBLIKA `[None, None, None]` — takva lista je istinita u Pythonu (neprazna), pa se filter dodavao čak i kad su sve tri tajne zapravo `None`, ostavljajući `is_redaction_enabled()` da lažno vrati `True`. Uhvaćeno pravim testom (ne pretpostavkom), ispravljeno filtriranjem falsy vrijednosti PRIJE provjere da li ima šta da se doda.

**2. Path sandbox** (`app/core/path_sandbox.py`): `resolve_within_roots()` (canonicalize + resolve symlinks + blokira `../` traversal + blokira UNC/network putanje, provjera protiv liste dozvoljenih root-ova), `ensure_extension_allowed()` (blokira `.exe/.bat/.cmd/.ps1/.vbs/.js/.msi/.scr/.reg` osim sa eksplicitnim `allow_execution=True` override-om), `ensure_file_size_allowed()`. Nijedan postojeći tool ovo još ne koristi (nijedan Python tool ne prima proizvoljnu putanju od korisnika/modela) — ovo je infrastruktura za prvi budući tool koji hoće (Document Engine ili FAZA 13 `computer_open_app`).

**3. Security self-test MVP** — podijeljen na dvije polovine koje se kombinuju:
   - Backend (`app/core/security_self_test.py` + `GET /security/self-test`): `backend_host_is_loopback` (settings.host == 127.0.0.1), `backend_auth_token_configured` (RICKY_LOCAL_TOKEN postoji), `no_cors_wildcard` (nema CORSMiddleware sa `allow_origins=["*"]` — trenutno nema CORS middleware-a uopšte, pa ovo prolazi po defaultu, ali sad je eksplicitno provjereno umjesto pretpostavljeno), `critical_tools_require_confirmation` (svaki risk=critical tool u registry-ju mora imati `requires_confirmation=True` deklarisano — striktnija provjera od runtime defense-in-depth koji već postoji u `permission_engine.py`), `log_redaction_enabled`.
   - Electron (`electron/core/securitySelfTest.cjs`): `electron_web_preferences` (contextIsolation/nodeIntegration/**sandbox**/**webSecurity**/**allowRunningInsecureContent** — zadnja tri su NOVO eksplicitno postavljena, ranije se oslanjalo na Electron 42 default), `preload_surface` (preload.cjs ne referencira "OPENAI" i nema generic invoke passthrough pattern), `no_devtools_in_production` (samo u packaged buildu — static scan da niko ne poziva `openDevTools()` bezuslovno).
   - `electron/main.cjs` poziva kombinovani self-test odmah nakon što backend krene, prije kreiranja prozora. U packaged (produkcijskom) buildu, bilo koji pao check → `dialog.showErrorBox("Security configuration failed. Production mode blocked.")` + `app.quit()` PRIJE nego što se ijedan prozor otvori. U dev buildu samo `console.warn`, ne blokira iteraciju.

**Namjerno NE uraditi sada — active window enforcement.** SECURITY_HARDENING_PLAN.md §9 vezuje ovo eksplicitno za `computer_type_text`/`computer_click`/`computer_press_key`/`computer_scroll`/`paste_clipboard` — nijedan od njih još ne postoji u Python-u (to je posao FAZE 13/14). Pisanje provjere za toolove koji ne postoje bi bila neiskorišten kod bez pravog pozivaoca za testiranje — ista logika kojom FAZA 10 (permission engine) nije unaprijed pisala active-window logiku dok FAZA 11 nije dodala stvarne toolove. `MIGRATION_PLAN.md` sad eksplicitno kaže da je ovo prvi korak same FAZE 13.

## Zašto je urađeno

Gate 0 je jedina prepreka za FAZA 13/14 (computer-use) i za production installer (FAZA 19). Umjesto da pravim active window enforcement bez stvarnog toola koji ga koristi (preuranjena apstrakcija), zatvorio sam preostale dvije stvarno-nezavisne stavke (self-test, path sandbox) plus redakciju, čime FAZA 13/14 mogu odmah krenuti, a active window provjera se prirodno radi kao prvi korak te faze.

## Kako je urađeno

1. Pročitan `SECURITY_HARDENING_PLAN.md` (sekcije 2, 8, 9, 10, 18) da se tačno zna šta se provjerava.
2. Provjereno stvarno stanje koda PRIJE pisanja bilo čega: `electron/core/window.cjs`/`companionWindow.cjs` (otkriveno: `sandbox`/`webSecurity` NISU eksplicitno postavljeni, oslanjaju se na Electron default), `preload.cjs` (već ispravan — allowlisted IPC, provjereno), `app/core/logging.py` (nema redakcije uopšte), `pythonProcess.cjs` (host/token već ispravni), `vite.config.ts`/`.env*` (nema `VITE_OPENAI*`, OpenAI ključ ne dopire do renderera — potvrđeno, ne pretpostavljeno).
3. `gitnexus_impact` na `createWindow`/`createCompanionWindow`/`configure_logging` prije izmjene (svi LOW).
4. Implementacija redom: shared `secureWebPreferences.cjs` → refaktorisan `window.cjs`/`companionWindow.cjs` → log redaction → path sandbox → backend self-test endpoint → Electron self-test orkestracija → wiring u `main.cjs` → prošireni smoke test.
5. **Stvarna verifikacija, ne samo pytest**: pokrenut pravi `node scripts/smoke-test.cjs` end-to-end (real Python backend, real HTTP pozivi) — svih 7 koraka prošlo uključujući novi security self-test korak. Dodatno, ručno pokvaren `secureWebPreferences` output (`sandbox: false`) preko require-cache monkeypatch-a da se potvrdi da self-test STVARNO detektuje kvar, ne samo prolazi na happy path-u — potvrđeno da `electron_web_preferences` check ispravno javlja `mismatch: sandbox, webSecurity`. Isto za `preload_surface` regex logiku (testirano na namjerno lošem sample stringu).
6. `npm run check` (dodao nove `.cjs` fajlove u tu skriptu), `npm run typecheck`, `python -m pytest` — svi zeleni.
7. `npx gitnexus analyze` + `detect_changes` nakon izmjena.

## Šta nije dirano

- Active window enforcement u `permission_engine.py` — namjerno odloženo do FAZE 13 (objašnjeno iznad).
- Legacy PowerShell `computer_*` alati u `electron/main.cjs` — i dalje rade bez permission sloja i bez auth tokena (nepromijenjeno, čeka FAZU 13/14).
- `ToolExecutor`/`permission_engine.py` logika — netaknuta, self-test je čita (`critical_tools_require_confirmation`), ne mijenja.
- Nijedan postojeći tool ne koristi novi `path_sandbox.py` — infrastruktura bez trenutnog pozivaoca, namjerno (vidi gore).

## Verifikacija

1. `python -m pytest python_backend/tests -q` — **105 passed** (94 prije + 11 path sandbox testova; self-test testovi su dio ranijih 94 jer su pisani prije path sandbox testova u istoj sesiji).
2. `npm run typecheck` — čisto.
3. `npm run check` — čisto (uključuje sve nove `.cjs` fajlove).
4. `node scripts/smoke-test.cjs` — **SVE PROŠLO ✓**, stvaran end-to-end test protiv pravog Python backend-a, 7/7 koraka uključujući security self-test.
5. Ručna negativna provjera (require-cache monkeypatch) — potvrđeno da self-test STVARNO detektuje pokvarenu konfiguraciju, ne samo prolazi.
6. `gitnexus_impact` prije izmjene (LOW na sve dirane simbole) + `gitnexus_detect_changes` poslije (HIGH, objašnjeno kao stvaran i očekivan nalaz, ne artefakt).

## Rizici / ograničenja

- **Companion/main prozor nije vizuelno testiran u pravom Electron GUI-ju** unutar ovog sandbox okruženja (poznat `ELECTRON_RUN_AS_NODE` ograničenje iz prethodnih izvještaja ove sesije). Refaktor `window.cjs`/`companionWindow.cjs` je mehanički (isti preload path, iste `contextIsolation`/`nodeIntegration` vrijednosti, samo dodani `sandbox`/`webSecurity`/`allowRunningInsecureContent`) i `node --check` potvrđuje sintaksnu ispravnost, ali stvarno vizuelno pokretanje prozora nije provjereno uživo.
- `no_devtools_in_production` i `no_cors_wildcard` provjere su static/structural (grep-style scan koda, ne runtime introspekcija) — dovoljno za MVP scope, ali teorijski se mogu zaobići suptilnijim kodom koji ne odgovara regex pattern-u. Dokumentovano kao poznato ograničenje, ne skriveno.
- `critical_tools_require_confirmation` je stroža provjera od onoga što `permission_engine.py` runtime već garantuje (defense-in-depth: `risk == "critical"` uvijek forsira confirmation bez obzira na deklarisani flag) — self-test check postoji da uhvati tool definicije koje se oslanjaju na tu mrežu bez eksplicitne deklaracije, ne zato što bi runtime bio nesiguran bez njega.
- Path sandbox nema trenutnog pozivaoca — vrijednost će se pokazati tek kad prvi tool počne primati putanje.

## Potreban follow-up

- FAZA 13 prvi korak: active window enforcement u `permission_engine.py`, vezano za prvi stvarni `computer_*` Python tool.
- Kad Document Engine epic ili FAZA 13 `computer_open_app` počnu primati putanje, ožičiti ih kroz `path_sandbox.resolve_within_roots()`.
- Preporučeno: kad korisnik prvi put pokrene pravi packaged build, ručno potvrditi da self-test zaista blokira pri namjerno pokvarenoj konfiguraciji (npr. privremeno postaviti `sandbox: false` pa vratiti) — automatska verifikacija u ovoj sesiji je pokrila logiku, ne stvaran packaged Electron proces.

## Potrebna korisnička potvrda

Nema blokirajuće. Preporučeno: potvrditi da FAZA 13 (computer-use v1) treba da počne sa active window enforcement kao svojim prvim korakom, kako je sad zapisano u `MIGRATION_PLAN.md`, prije nego što se dodijeli drugom agentu.
