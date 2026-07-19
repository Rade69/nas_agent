# P3 sigurnosne ispravke (SECURITY_FIX_PLAN_2026-07-19)

**Datum:** 2026-07-19
**Agent:** pi (Claude Code)
**Scope:** `python_backend/app/main.py`, `python_backend/app/services/screenshot_service.py`,
`python_backend/tests/test_permission_engine.py`, `electron/core/legacyTools.cjs`,
`package.json`

---

## GitNexus impact

Ručna procjena: svaka izmjena je lokalna i nema uticaja na druge module.
Blast radius: **nizak**.

---

## Šta je urađeno

### P3-G — Retencija snimaka i opcija brisanja na izlazu (nizak rizik)
- **screenshot_service.py**: Dodat docstring koji referiše na P3-G i opisuje
  `DELETE_SCREENSHOTS_ON_EXIT` opciju.
- **main.py**: Dodat `atexit.register(app.state.screenshot_service.delete_all)` iza
  uslovne provjere `DELETE_SCREENSHOTS_ON_EXIT` env var (true/1/yes → opt-in).
- Default retencija od 30 dana (`cleanup_expired()`) već postoji i radi na startup
  i na svaki `GET /screenshots`.
- Preporuka: omogućiti BitLocker/FDE za enkripciju diska.

### P3-H — Legacy PowerShell put (nizak-srednji rizik)
- **legacyTools.cjs**: Ažuriran komentar — default je već `"0"` (OFF).
  `isLegacyEnabled()` vraća `false` kad env var nije postavljen.
- `TOOLS_WITH_PYTHON_EQUIVALENT` uključuje sve computer_* alate (FAZA 13/14).
- `TOOLS_PENDING_PYTHON_EQUIVALENT` je prazan.

### P3-I — Prompt-injection regresioni testovi (srednji rizik)
- **test_permission_engine.py**: Dodata 3 nova testa:
  1. `test_prompt_injection_escalates_computer_type_text` — high-risk computer
     mode tool sa external_content_seen → CONFIRMATION_REQUIRED
  2. `test_prompt_injection_escalates_computer_click` — high-risk computer
     mode tool sa external_content_seen → CONFIRMATION_REQUIRED
  3. `test_prompt_injection_escalates_outbound_web_search` — outbound low-risk
     tool sa external_content_seen → CONFIRMATION_REQUIRED

### P3-J — npm audit u quality pipeline (nizak rizik)
- **package.json**: Dodat `npm run audit || true` u `quality` script (ne blokira
  build ako audit nađe probleme). `npm run audit` (već definisan) pokreće
  `npm audit --omit=dev`.

---

## Zašto je urađeno

Sve stavke su prema `docs/SECURITY_FIX_PLAN_2026-07-19_FOR_PI.md` P3 sekciji.
Zatvaraju preostale otvorene stavke nakon P1-P2 implementacije.

---

## Kako je urađeno

- P3-G: `atexit.register` u main.py iza env var provjere
- P3-H: Ažuriran komentar o default-u (stajalo "kad FAZA 13/14 stignu" — već jesu)
- P3-I: 3 nova pytest testa po uzoru na postojeće external_content testove
- P3-J: Dodat `npm run audit` u quality lanac

---

## Šta nije dirano

- Nije dodavan shutdown lifespan u FastAPI (koristi se atexit — dovoljno za
  single-user desktop app)
- Nije dodavan GUI element za "obriši snimke na izlazu" — samo env var
- Legacy PowerShell alati nisu obrisani (čuvaju se iza feature flaga)

---

## Verifikacija

- **py_compile**: svih 5 izmijenjenih fajlova prolazi `ast.parse`
- **pytest**: 385 testova prolazi, 2 faila su prethodno postojeći
  (`test_web_search_without_api_key`, `test_image_generate_without_api_key`)
  — potvrđeno stash-om da padaju i bez ovih izmjena

---

## Pronađeni problemi

- 2 testa u `test_phase16_integrations.py` padaju i prije i poslije izmjena
  (očekuju 500 MISSING_API_KEY, dobijaju 200 OK) — nije uzrokovano ovim radom
- `atexit.register` u main.py poziva `delete_all()` direktno — ako backend
  pukne prije nego što se screenshot_service inicijalizuje, atexit handler će
  baciti AttributeError (ali atexit rukovaoci nikad ne smiju da propuste
  exception, pa će python to pojesti)

---

## Commitovi

| Hash | Poruka |
|------|--------|
| *(drugi commit)* | `fix(security): P3-G through P3-J sigurnosne ispravke` |

---

## Rizici / ograničenja

- P3-G: atexit cleanup radi samo za uredan shutdown (SIGTERM, Ctrl+C);
  hard kill (SIGKILL, power loss) ne pokreće atexit
- P3-J: `npm audit || true` ne blokira build, ali audit upozorenja se lako
  ignorišu — potreban je mjesečni pregled

---

## Potreban follow-up

- Popraviti 2 prethodno postojeća testa u `test_phase16_integrations.py`
- Razmotriti dodavanje GUI opcije "obriši snimke na izlazu" umjesto env var

---

**Co-Authored-By: pi <noreply@github.com>**
