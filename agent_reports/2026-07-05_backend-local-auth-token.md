# Agent report — Backend local auth token (Security PR-1, posljednja otvorena stavka Security Gate 0)

**Datum:** 2026-07-05

## Scope

- Novi: `python_backend/app/core/auth.py`, `python_backend/tests/test_auth.py`.
- Izmjena: `python_backend/app/core/config.py` (`Settings.local_token`, čitanje `RICKY_LOCAL_TOKEN` env varijable), `python_backend/app/main.py` (globalna FastAPI `dependencies=[Depends(require_local_token)]`).
- Izmjena: `electron/services/pythonProcess.cjs` (generisanje tokena po Electron sesiji preko `crypto.randomBytes(32)`, prosljeđivanje kroz `RICKY_LOCAL_TOKEN` env var pri spawn-u Python procesa).
- Izmjena: `electron/services/pythonClient.cjs` (`setLocalToken()`/module-level token, automatsko dodavanje `Authorization: Bearer <token>` headera u `requestJson()`).
- Izmjena: `docs/MIGRATION_PLAN.md` (Security Gate 0 status — token stavka zatvorena), `docs/SECURITY_MODEL.md` ("Status implementacije" ažuriran).

## GitNexus impact

`gitnexus_impact({target: "startPythonBackend", direction: "upstream", repo: "nas_agent"})` prije izmjene → risk LOW, samo `main.cjs` (d=1).

`gitnexus_detect_changes({repo: "nas_agent", scope: "all"})` nakon izmjene → **risk_level: "critical"**, 26 pogođenih procesa, 12 fajlova. Razlog: `requestJson()` u `pythonClient.cjs` je jedina zajednička niskoslojna funkcija kroz koju prolaze svi Electron→Python pozivi (executeTool, sve confirmations/plans funkcije, listEvents, createRealtimeSession, getHealth) — dodavanje jednog uslovnog headera tu se po širini grafa vidi kao "critical" jer dotiče svaki proces koji koristi Python backend. **Ovo je eksplicitno prijavljeno korisniku** u skladu sa CLAUDE.md pravilom za HIGH/CRITICAL rizik, uz objašnjenje da je riječ o širini (breadth), ne o stvarnom kvaru — potvrđeno end-to-end smoke testom (ispod).

## Šta je urađeno

Ovo je bila posljednja neriješena stavka Security Gate 0 vezana za "backend localhost/auth" (Python backend je od FAZE 4 vezan na `127.0.0.1`, ali je do sada prihvatao bilo koji lokalni zahtjev bez ikakve autentifikacije — svaki drugi lokalni proces je mogao pozvati `/tools/execute`).

Implementacija prati `SECURITY_HARDENING_PLAN.md` sekciju 6 ("Local auth token"):

1. **`app/core/config.py`** — `Settings.local_token: str | None`, čita se iz `RICKY_LOCAL_TOKEN` env varijable u `get_settings()`.
2. **`app/core/auth.py`** (novo) — `require_local_token` FastAPI dependency: ako `settings.local_token` nije podešen, propušta sve (fail-open — pokriva testove i ručni `uvicorn` dev rad iz README-a bez Electron-a); ako JESTE podešen, zahtijeva `Authorization: Bearer <token>` koji se mora tačno poklapati, inače `401 UNAUTHORIZED`.
3. **`app/main.py`** — dependency je kačen globalno na FastAPI app nivou (`dependencies=[Depends(require_local_token)]`), pokriva **sve** rute uključujući `/health` (SECURITY_HARDENING_PLAN.md sekcija 18 self-test eksplicitno traži "backend does not accept unauthenticated requests").
4. **`electron/services/pythonProcess.cjs`** — `getOrCreateLocalToken()` generiše `crypto.randomBytes(32).toString("hex")` jednom po Electron sesiji (lijeno, prvi put kad se `startPythonBackend()` pozove), poziva `setLocalToken()` na `pythonClient.cjs` PRIJE spawn-a (da čak i reuse-health-check zahtjev nosi token), i prosljeđuje ga Python child procesu preko `RICKY_LOCAL_TOKEN` env varijable.
5. **`electron/services/pythonClient.cjs`** — `setLocalToken(token)` postavlja module-level varijablu; `requestJson()` automatski dodaje `Authorization: Bearer <token>` header ako je token postavljen. Token se nikad ne loguje (postojeći `console.log` pozivi u `pythonProcess.cjs` ispisuju samo command/args, ne env).

## Zašto je urađeno

Korisnik je eksplicitno tražio nastavak na "backend local auth token" kao posljednju otvorenu Security Gate 0 stavku, nakon rasprave o tome šta je sljedeće za mene i GLM-a.

## Kako je urađeno

Pročitani `pythonClient.cjs`/`config.py`/`main.py` prije izmjene (dva puta ponovljeno čitanje preko `cat` jer je Read tool cache bio zastario u odnosu na stvarni sadržaj fajla — GLM je u međuvremenu paralelno mijenjao iste fajlove za FAZU 11/12). `gitnexus_impact` na `startPythonBackend` prije prve izmjene. Implementacija u redoslijedu: config → auth dependency → main.py wiring → pytest provjera (fail-open ne kvari postojeće testove) → Electron token generacija → Electron header injection → novi testovi → pun pytest → pravi end-to-end smoke test (pokretanje stvarnog backend procesa preko `startPythonBackend()`, provjera da autentifikovan `executeTool` poziv radi, i da sirovi `fetch()` bez/sa pogrešnim tokenom dobija 401) → `gitnexus_detect_changes` → dokumentacija.

## Šta nije dirano

- Legacy PowerShell computer-use alati u `electron/main.cjs` — i dalje bez ikakvog permission/auth sloja (nepromijenjeno, poznat rizik, FAZA 13/14).
- Active window validation, path/network sandbox — i dalje van obima (FAZA 14).
- FAZA 12 (Companion orb, GLM-ov paralelni rad) — nije diran, provjereno da nema preklapanja fajlova.

## Verifikacija

1. `pytest` — **65 passed** (59 prije ove faze + 6 novih auth testova: fail-open bez tokena, blokiranje nedostajućeg/pogrešnog/malformiranog headera, uspjeh sa ispravnim tokenom, zaštita `/tools` rute).
2. `node --check` na oba izmijenjena Electron fajla — OK.
3. **Pravi end-to-end smoke test** (ne samo pytest): pokrenut stvaran Python backend preko `startPythonBackend()` (identična funkcija koju Electron koristi), zatim:
   - `executeTool({tool_name: "echo", ...})` preko `pythonClient.cjs` (token automatski priložen) → uspjeh.
   - Sirovi `fetch("http://127.0.0.1:8765/health")` bez headera → **401 UNAUTHORIZED**.
   - Sirovi `fetch(...)` sa pogrešnim tokenom → **401 UNAUTHORIZED**.
4. `gitnexus_detect_changes` → risk CRITICAL (obrazloženo iznad, širina ne kvar).

## Rizici / ograničenja

- **Fail-open kad token nije konfigurisan** je namjeran kompromis da se ne razbije 59 postojećih testova i README-ov ručni dev put (`cd python_backend && uvicorn app.main:app`) — ali znači da neko ko ručno pokrene backend bez Electron-a i bez `RICKY_LOCAL_TOKEN` env var-a i dalje nema autentifikaciju. Ovo je dokumentovano u kodu i u `SECURITY_MODEL.md`, ne skriveno.
- **Reuse-backend edge slučaj:** ako je backend već pokrenut iz PRETHODNE Electron sesije sa DRUGAČIJIM tokenom (rijetko — više paralelnih Electron instanci), health-check reuse detekcija bi mogla pogrešno zaključiti da postojeći backend nije zdrav (401 na health check sa novim tokenom) i pokušati pokrenuti novi na istom portu, što bi palo jer je port zauzet. Ovo je rubni, dev-only slučaj koji je bio donekle krhak i prije ove izmjene; nije popravljen u ovoj fazi (van obima).
- GitNexus CRITICAL nalaz je zbog širine (chokepoint funkcija), ne zbog kvara — potvrđeno realnim smoke testom, ne samo unit testovima.

## Potreban follow-up

- Security Gate 0 preostaje otvoren za: active window validation enforcement, path/network sandbox, security self-test (sve FAZA 14).
- Kad FAZA 14 stigne, `require_local_token`-ov fail-open slučaj bi mogao biti pooštren (npr. hard-fail ako je `--production` flag prisutan) kao dio "security self-test" acceptance kriterijuma iz `SECURITY_HARDENING_PLAN.md` sekcije 18.

## Potrebna korisnička potvrda

Preporučeno: ručno pokrenuti `npm run dev` i potvrditi da cijela app (voice, tools, confirmations, companion orb od FAZE 12) i dalje radi normalno sa novim auth slojem uključenim — agent je verifikovao preko Node smoke testa, ne preko pune Electron GUI sesije.
