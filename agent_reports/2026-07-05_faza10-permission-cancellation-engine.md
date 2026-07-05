# Agent report — FAZA 10: Permission/risk engine + execution_id/cancellation_token state mašina

**Datum:** 2026-07-05

## Scope

- Novi: `python_backend/app/core/payload_hash.py`, `python_backend/app/agent/cancellation.py`, `python_backend/app/agent/permission_engine.py`.
- Novi testovi: `python_backend/tests/test_permission_engine.py`, `test_cancellation.py`, `test_tool_executor_permission.py`.
- Izmjena: `python_backend/app/storage/db.py` (migracija: `confirmations.tool_name`/`payload_hash`/`expires_at`), `app/schemas/confirmation.py`, `app/storage/repositories/confirmation_repo.py`, `app/services/confirmation_service.py`, `app/api/confirmations.py` (binding polja), `app/schemas/tool.py` (`ToolState`, `ToolExecutionContext.confirmation_id`, `ToolExecutionResponse.execution_id`/`tool_state`), `app/agent/tool_executor.py` (rewired), `app/api/tools.py` (novi cancel endpoint), `app/main.py` (cancellation registry na `app.state`).
- Izmjena: `docs/MIGRATION_PLAN.md` (FAZA 10 ✅, Security Gate 0/1 ažurirani), `docs/SECURITY_MODEL.md` ("Status implementacije" ažuriran).

## GitNexus impact

`gitnexus_impact({target: "ToolExecutor", direction: "upstream", repo: "nas_agent"})` prije izmjene → risk LOW, samo `app/api/tools.py` (d=1) i `app/main.py` (d=2), oba planirano izmijenjena.

`gitnexus_detect_changes({repo: "nas_agent", scope: "all"})` nakon izmjene → **risk_level: "high"**, 14 pogođenih procesa (uglavnom confirmation lifecycle procesi — `list_pending_confirmations`, `approve_confirmation`, `reject_confirmation`, `cancel_confirmation`, `create_confirmation`, `list_confirmations` — i `execute_tool` proces). Ovo je očekivano i legitimno visok rizik: FAZA 10 po definiciji proširuje dijeljene sheme (`ToolExecutionResponse`, `ConfirmationResponse`) i `confirmation_service`/`confirmation_repo` koje svi ti procesi koriste. Nijedan od navedenih procesa nije stvarno pokvaren — cijeli test suite (46 testova, uključujući sve confirmation lifecycle testove) prolazi nakon izmjene. **Ovo je eksplicitno prijavljeno korisniku u skladu sa CLAUDE.md pravilom za HIGH/CRITICAL rizik**, uz obrazloženje zašto je obim rizika opravdan.

## Šta je urađeno

FAZA 10 je sigurnosno-kritičan gate iz `docs/MIGRATION_PLAN.md`, proširen 2026-07-05 analizom (Gemini/ChatGPT) koja je dodala zahtjev za `execution_id`/`cancellation_token` state mašinu (`SECURITY_HARDENING_PLAN.md` sekcija 25). Prije izmjene pročitana je cijela postojeća FAZA 9 infrastruktura (`ConfirmationService`/`ConfirmationRepository`/`app/api/confirmations.py`) da se novi sloj nadoveže na nju, ne duplira je — FAZA 9 izvještaji su eksplicitno ostavili komentar "permission/risk layer that *issues* these confirmations is FAZA 10", što je tačno ovaj rad.

**Confirmation binding (SECURITY_HARDENING_PLAN.md sekcija 25.3 — "confirmation_id mora biti vezan za tool name, payload hash..., expiration time"):**

1. `confirmations` tabela dobija `tool_name`, `payload_hash`, `expires_at` kolone — dodane i u `CREATE TABLE IF NOT EXISTS` (novi DB-ovi) i u postojeći `MIGRATIONS` niz (`_ensure_column` — mehanizam koji je GLM/pi već uveo za FAZA 9 `plan_id`/`summary` kolone, ponovo iskorišten bez izmjene).
2. `ConfirmationCreateRequest` dobija `tool_name: str | None` i `ttl_seconds: int = 300`; `ConfirmationService.propose()` računa `payload_hash` (sha256 nad sortiranim JSON-om, `app/core/payload_hash.py`) i `expires_at` (now + ttl) server-side, ne vjeruje klijentu.
3. `ConfirmationService.is_expired()` — provjerava `expires_at` protiv trenutnog vremena.

**Permission engine (`app/agent/permission_engine.py`):** implementira korake 4-9 iz `SECURITY_HARDENING_PLAN.md` sekcija 8 "Tool executor provjere" (koraci 1-3 već postoje u `ToolExecutor`; koraci 10-12 — active window, path sandbox, network — eksplicitno NISU implementirani, Python backend nema kapacitet za njih još, ostavljen kod-komentar da se ne prave lažni utisak da su pokriveni):

- `requires_computer_mode` → `context.computer_mode` mora biti `true`, inače `COMPUTER_MODE_REQUIRED`.
- `requires_confirmation` (ili `risk == "critical"` — defense-in-depth i ako tool definicija zaboravi eksplicitno postaviti zastavicu) → zahtijeva `context.confirmation_id`; provjerava da confirmation postoji, da je `status == "approved"`, da nije istekla, i da se `tool_name`/`payload_hash` poklapaju sa stvarnim pozivom (`CONFIRMATION_REQUIRED`/`CONFIRMATION_NOT_FOUND`/`CONFIRMATION_NOT_APPROVED`/`CONFIRMATION_EXPIRED`/`CONFIRMATION_MISMATCH`).

**Cancellation state mašina (`app/agent/cancellation.py`):** in-memory `CancellationRegistry` (namjerno neperzistentna — runtime handshake, ne trajni zapis; trajni audit je i dalje `tool_runs` action log). Stanja iz sekcije 25.2: `planned → preflight → running/commit_started → completed / cancel_requested / cancelled_before_commit / cannot_cancel_commit_started / failed`.

**`ToolExecutor` rewired:** generiše `execution_id`, prolazi kroz permission engine PRIJE poziva handler-a (`preflight`), provjerava da li je cancel zatražen prije nego što uđe u "commit" fazu (poziv `tool.handler()`) — ako jeste, vraća `cancelled_before_commit` bez izvršavanja. Ako je cancel zatražen TOKOM commit faze (trenutni sinhroni handleri se ne mogu prekinuti na pola), vraća `cannot_cancel_commit_started` sa stvarnim rezultatom, ne lažni "cancelled". Novi `POST /tools/executions/{execution_id}/cancel` endpoint dozvoljava konkurentnom zahtjevu da postavi cancel zastavicu (FastAPI sync route-ovi rade u threadpool-u, pa je konkurentnost stvarno moguća).

**Šta ostaje kao scaffold za buduće faze, ne implementirano sada:** segmentirano typing/preflight-commit za stvarne dugotrajne OS toolove (`computer_type_text` i sl.) — nema takvog toola u Python registry-ju još (FAZA 13/14, i dalje blokirano Security Gate-om 0). Cancellation mašina je napravljena tako da takvi budući toolovi mogu periodično zvati `cancellations.is_cancel_requested(execution_id)` između segmenata.

## Zašto je urađeno

FAZA 10 je eksplicitno sigurnosno-kritičan gate, i sad uključuje i cancellation zahtjev dodat istog dana nakon Gemini/ChatGPT analize. Cilj: da nijedan tool sa `requires_confirmation`/`requires_computer_mode`/`risk=critical` ne može biti izvršen bez validne, ne-replay-ovane potvrde, i da postoji stvaran (ne kozmetički) mehanizam za "stop" da prekine tool prije nego što dirne OS.

## Kako je urađeno

Redoslijed: migracija baze → hash utility → schema polja (confirmation + tool) → cancellation registry → permission engine → rewire `ToolExecutor` → wiring u `main.py`/`api/tools.py` → testovi → `pytest` (46 passed) → `gitnexus_detect_changes` → dokumentacija. Impact analiza (`gitnexus_impact` na `ToolExecutor`) urađena prije prve izmjene tog fajla.

## Šta nije dirano

- `electron/main.cjs`, legacy PowerShell toolovi — netaknuti. Permission engine trenutno štiti **samo Python-registrovane toolove** (za sada samo dummy `echo`). Legacy computer-use i dalje radi bez ovog sloja — nepromijenjeno stanje, eksplicitno navedeno u `SECURITY_MODEL.md`.
- Active window validation, path sandbox, network target provjera (koraci 10-12 tool executor checklist-e) — namjerno van obima, FAZA 11 posao, Python backend nema kapacitet za njih.
- Segmentirano izvršavanje dugotrajnih OS akcija — nema takvog toola još da bi se testiralo; scaffold postoji, implementacija dolazi sa FAZA 13/14.
- FAZA 9 kod (confirmations/plans UI, Electron IPC) — nije mijenjan, samo dopunjena shema/servis koje FAZA 9 već koristi (backward-compatible dodaci, ne izmjena postojećeg ponašanja).

## Verifikacija

1. `python -m pytest` u `python_backend/` → **46 passed** (bilo 11 prije FAZE 10; +20 novih testova iz ove faze, +15 iz FAZA 8/9 koje sam zatekao).
2. `gitnexus_impact` prije izmjene `ToolExecutor` → LOW.
3. `gitnexus_detect_changes` poslije → **HIGH** (14 procesa) — pregledano ručno, sve pogođene stavke očekivane (dijeljena shema/servis), nijedan test ne pada.

## Rizici / ograničenja

- **GitNexus risk_level: HIGH** — eksplicitno prijavljeno korisniku. Razlog: proširenje dijeljenih shema (`ToolExecutionResponse`, `ConfirmationResponse`) i `confirmation_service.py`/`confirmation_repo.py` (koje FAZA 9 confirmation lifecycle već koristi) ima širok "blast radius" po grafu, ali su sve izmjene aditivne (nova opciona polja, novi parametri sa default vrijednostima) — potvrđeno da ništa postojeće nije pokvareno kroz pun test suite.
- Permission engine ne štiti legacy PowerShell computer-use — Security Gate 0 i dalje NIJE zatvoren (4/5 stavki), ostaje FAZA 11 (i backend local auth token iz Security PR-1).
- Cancellation je prava konkurentnost samo ako FastAPI zaista servira `/tools/execute` i `/tools/executions/{id}/cancel` na različitim thread-ovima paralelno (Uvicorn threadpool za sync route-ove) — ovo NIJE testirano sa stvarnim paralelnim HTTP zahtjevima u ovoj sesiji (samo jedinični test koji simulira cancel-prije-commit direktnim pozivom `registry.request_cancel()` unutar iste niti). Preporučen budući test: pravi concurrent HTTP test kad postoji stvaran dugotrajan tool.
- `critical` risk defense-in-depth pravilo (uvijek zahtijeva confirmation čak i ako `requires_confirmation=False`) je moja dodatna interpretacija `SECURITY_HARDENING_PLAN.md` principa "human gate for risky actions" — nije doslovno navedeno kao ovaj tačan mehanizam u planu, vrijedi da korisnik potvrdi da je ovo željeno ponašanje.

## Potreban follow-up

- FAZA 11 (tool registry + bezbjedni lokalni toolovi) treba: (a) migrirati barem jedan stvaran tool kroz ovaj permission engine da se vidi u praksi, (b) dodati active window validation, (c) path/network sandbox.
- Kad FAZA 13/14 uvede stvaran dugotrajan OS tool, implementirati segmentiranu preflight/commit petlju koja periodično provjerava `cancellations.is_cancel_requested()` — scaffold je spreman, implementacija nije.
- Backend local auth token (Security PR-1) ostaje otvoren, nezavisno od ove faze.

## Potrebna korisnička potvrda

- Potvrditi da je "critical risk uvijek zahtijeva confirmation" prihvatljivo dodatno pravilo (nije bilo eksplicitno traženo, ali proizilazi iz principa u `SECURITY_HARDENING_PLAN.md`).
- GitNexus HIGH risk nalaz — pregledan i obrazložen iznad; javiti ako se želi dodatna nezavisna provjera prije nastavka na FAZU 11.
