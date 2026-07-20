# Agent report — QM-0: Zeleni testni baseline

**Datum:** 2026-07-20
**Izvođač:** pi
**Plan:** `docs/PI_TASK_QM0_TEST_BASELINE_FIX.md`
**Preduslov za:** `docs/QT_MIGRATION_PLAN_2026-07-20.md` QM-0 gate ("Python suite je potpuno zelen")

## Scope

Popraviti tri prethodno postojeća test pada tako da puni backend suite (`pytest`) prolazi 100%, bez izmjene funkcionalnosti. Samo test/config tačnost.

## Šta je urađeno

### 1. `tests/test_browser_open.py::test_browser_open_is_listed`
- **Problem:** Test je očekivao `requires_computer_mode=True`, ali commit `c58d6eb` je namjerno promijenio politiku na `False`. Obrazloženje iz commit poruke: "browser_open je naslijedio requires_computer_mode=True iz _def() helpera, pa je 'otvori Brave' puklo sa COMPUTER_MODE_REQUIRED. Skinuto na False — URL validacija + shell=False + medium risk (P2-K eskalacija) i dalje štite, a otvaranje browsera na validiranom URL je benigno kao i web_search."
- **Popravka:** `assert tool["requires_computer_mode"] is True` → `assert tool["requires_computer_mode"] is False` + komentar sa referencom na commit.
- **Negativni testovi** (`test_browser_open_rejects_unsafe_url`, `test_browser_open_rejects_embedded_credentials`) već postoje i ostali su netaknuti.

### 2. `tests/test_phase16_integrations.py::test_web_search_without_api_key_returns_structured_error`
- **Problem:** Test je očekivao HTTP 500 (pretpostavka da `AppError` propagira do FastAPI error handlera). Realnost: `ToolExecutor` hvata `AppError` i pretvara ga u strukturirani odgovor sa HTTP 200 i `ok: false` u body-ju.
- **Popravka:** `assert response.status_code == 200` + `assert body["ok"] is False` + `assert body["error"]["code"] == "MISSING_API_KEY"`.

### 3. `tests/test_phase16_integrations.py::test_image_generate_without_api_key_returns_structured_error`
- **Problem:** Isti kao #2.
- **Popravka:** Ista kao #2.

## Zašto ovako

Testovi su bili neusklađeni sa stvarnim ponašanjem sistema:
- `browser_open` test je zastario (commit c58d6eb je mijenjao politiku, test nije ažuriran)
- API key testovi su pogrešno pretpostavljali da `AppError` propagira do HTTP sloja, ali `ToolExecutor` ga eksplicitno hvata i normalizuje u standardni tool response format (HTTP 200, `ok: false`, `error: {code, message}`)

## Šta nije dirano

- `python_backend/app/agent/tool_catalog/phase11.py` — netaknut
- `python_backend/app/services/openai_image_client.py` — netaknut
- `python_backend/app/tools/images/generate.py` — netaknut
- `python_backend/app/tools/web/search.py` — netaknut
- Svi thumbnail fajlovi (QM-6T) — netaknuti
- Bilo kakva stvarna tool politika ili implementacija — nije mijenjana

## Verifikacija

```bash
cd python_backend && python -m pytest -q
```
**Rezultat: 412 passed, 0 failed** — puni suite je potpuno zelen.

## Rizici/ograničenja

- API key testovi i dalje zavise od fixture-ova koji postavljaju env na prazan string. Ako se promijeni mehanizam učitavanja API ključeva (npr. preko fajla umjesto env), testovi mogu ponovo pasti.
- `test_web_search_requires_query` direktno manipulira `os.environ` (ne kroz monkeypatch), što je manje čisto — ali funkcioniše i nije dirano u ovom zadatku.

## Potreban follow-up

- Dodati `--disable-socket` ili `pytest-socket` da se garantuje da testovi nikad ne zovu mrežu (trenutno se oslanjamo na prazan API ključ, što je indirektna zaštita).

## Potrebna korisnička potvrda

Pokrenuti `python -m pytest -q` i potvrditi `412 passed, 0 failed`.
