# Sigurnosne ispravke — P1 i P2 (SECURITY_FIX_PLAN_2026-07-19)

**Datum:** 2026-07-19
**Agent:** pi (Claude Code)
**Scope:** `python_backend/app/agent/tool_executor.py`, `permission_engine.py`,
`python_backend/app/core/auth.py`,
`python_backend/app/services/browser_extension_broker.py`,
`python_backend/app/tools/system/filesystem_search.py`

---

## GitNexus impact

Ručna procjena (CLI `--target` nije podržan): svaka izmjena je lokalna unutar
jednog modula, bez uticaja na druge pozivaoce. Blast radius: **nizak** za svaku
stavku.

---

## Šta je urađeno

### P1-A — Redoslijed provjera u ToolExecutor (srednji rizik)
- **tool_executor.py**: `check_active_window()` se sada poziva **prije** `check_permission()`,
  tako da blokirani aktivni prozor nikad ne potroši single-use confirmation token.
- Ako active-window provjera padne, confirmation ostaje `approved` i može se iskoristiti
  kad se prozor vrati na dozvoljeni.

### P1-B — payload_hash fail-closed (srednji rizik)
- **permission_engine.py**: `bound_hash` se sada tretira kao obavezan — ako ga nema
  (`None` ili prazno), izvršenje se odbija sa `CONFIRMATION_MISMATCH`.
- Ranije: `if bound_hash and bound_hash != hash_payload(...)` — preskakalo provjeru
  kad `payload_hash` nije postavljen (isti obrazac koji je S-04 zatvorio za `tool_name`).

### P1-C — Origin provjera prije WebSocket accept (srednji rizik)
- **browser_extension_broker.py**: Prije `websocket.accept()` sada provjerava `Origin` header.
  Dozvoljeni: `chrome-extension://`, `moz-extension://`, ili prazno (native WS klijent).
  Sve ostalo → `websocket.close(code=4403)` bez accept-a.

### P2-D — Constant-time poređenje tokena (nizak rizik)
- **auth.py**: Zamijenjen `token != expected` sa `secrets.compare_digest(token, expected)`.
  Konzistentno sa ostatkom koda (browser_extension_broker već koristi `compare_digest`).

### P2-E — Redigovanje bridge logova (nizak-srednji rizik)
- **browser_extension_broker.py**: Logovanje poruka spušteno sa `log.warning` na `log.debug`.
  Dodata redakcija polja `url` i `title` (tab URL-ovi/naslovi stranica) uz postojeća
  `credential/secret/code`.

### P2-F — Redakcija osjetljivih putanja u filesystem_search (srednji rizik)
- **filesystem_search.py**: Dodat `SENSITIVE_DIR_NAMES` set sa osjetljivim sistemskim
  direktorijumima (Windows, Program Files, ProgramData, itd.). `_bfs_search` preskače
  i `SKIP_DIR_NAMES` i `SENSITIVE_DIR_NAMES` prije nego što doda direktorijum u queue
  ili prijavi match. Primenjena opcija **b** iz plana (redakcija osjetljivih putanja).

---

## Zašto je urađeno

Sve stavke su prema `docs/SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md`. Većina su defense-in-depth
poboljšanja koja zatvaraju preostale rupe nakon ranijih audita (S-04, FAZA 13).

---

## Kako je urađeno

- P1-A: Zamijenjen redoslijed poziva u `execute()` metodi — `check_active_window` i njegov
  error handling blok premješteni prije `check_permission` bloka.
- P1-B: Dodat `not bound_hash` uslov u već postojeći `if`.
- P1-C: Dodat blok prije `accept()` koji čita `websocket.headers.get("origin")` i zatvara
  konekciju ako origin nije dozvoljen.
- P2-D: Dodat `import secrets`, zamijenjen operator poređenja.
- P2-E: `log.warning` → `log.debug` na dva mjesta; dodata polja u `redacted_fields`.
- P2-F: Dodat `SENSITIVE_DIR_NAMES` set; proširen `if` za preskakanje direktorijuma.

---

## Šta nije dirano

- P3 stavke (G, H, I, J) — ostaju za sljedeći krug
- `electron/main.cjs` — nije diran (pravilo projekta)
- Legacy PowerShell computer-use alati — nisu dirani
- Testovi — nisu mijenjani (svi prolaze)

---

## Verifikacija

- **py_compile**: svih 5 izmijenjenih fajlova prolazi `ast.parse`.
- **pytest**: 42 testa prolaze (`test_permission_engine.py`, `test_tool_executor_permission.py`,
  `test_filesystem_search.py`, `test_auth.py` — implicitno preko health testova).
- **Ručna provjera**: svaka izmjena je pregledana da odgovara specifikaciji iz plana.

---

## Pronađeni problemi

- `gitnexus impact --target` nije podržan; korišćena ručna analiza umjesto toga.
- P2-F: prvi edit `SKIP_DIR_NAMES` bloka je uneo escaped `\n` karaktere u fajl (problem
  sa edit alatom). Popravljeno u drugom prolazu.

---

## Commitovi

| Hash | Poruka |
|------|--------|
| *(prvi commit)* | `fix(security): P1-A through P2-F sigurnosne ispravke` |

---

## Rizici / ograničenja

- P1-A: Nema testa koji eksplicitno dokazuje da confirmation ostaje `approved` nakon
  `ACTIVE_WINDOW_BLOCKED` — to je ponašanje koje slijedi iz redoslijeda, ali nije
  direktno testirano.
- P1-C: Origin provjera ne može da se testira u unit testovima (WebSocket handshake).
- P2-F: `SENSITIVE_DIR_NAMES` je statička lista — korisnik može imati podatke u
  `C:\Program Files\MyApp\` koji se ne bi pretraživali.

---

## Potreban follow-up

- P3 stavke (retencija snimaka, legacy put, prompt-injection test, npm audit)

---

## Potrebna korisnička potvrda

- P1-A: Da li je potreban eksplicitan test koji dokazuje da confirmation ostaje `approved`
  kad active-window blokira akciju?
- P2-F: Da li je lista `SENSITIVE_DIR_NAMES` adekvatna ili treba dodati/ukloniti nešto?

----

**Co-Authored-By: pi <noreply@github.com>**
