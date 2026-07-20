# PI Task: QM-0 — Zeleni testni baseline

## Cilj
Popraviti tri pre-postojeća test pada tako da puni backend suite (`pytest`)
prolazi 100%, bez izmjene funkcionalnosti — samo test/config tačnost.
Preduslov je za `docs/QT_MIGRATION_PLAN_2026-07-20.md` QM-0 gate ("Python
suite je potpuno zelen"), ali nezavisan je od Qt shell-a i ne čeka ga.

## Pozadina
Ovi padovi su već dokumentovani u `docs/ELECTRON_MIGRATION_PLAN_REVISED_2026-07-19.md`
§2.4 i potvrđeni ponovnim pokretanjem 2026-07-20 (409/412 prošlo, ova tri pala,
nepovezano sa QM-6 thumbnail radom).

## Padovi za popravku

### 1. `tests/test_browser_open.py::test_browser_open_is_listed`
Test očekuje `requires_computer_mode=True`, ali commit `c58d6eb`
("open_path alat + browser_open bez Computer Mode") je **namjerno** promijenio
politiku na `False`. Test i implementacija su neusklađeni — implementacija je
namjerna odluka, test je zastario.

**Popravka:** uskladiti test sa usvojenom politikom (`False`), ne obrnuto.
Pročitati commit `c58d6eb` poruku prije izmjene da se potvrdi razlog odluke.
Dodati negativan test: potvrditi da `browser_open` i dalje odbija
nebezbjedne URL-ove/credential payload (već postoji
`test_browser_open_rejects_unsafe_url` — provjeriti da ostaje netaknut).

### 2 i 3. `tests/test_phase16_integrations.py`
- `test_web_search_without_api_key_returns_structured_error`
- `test_image_generate_without_api_key_returns_structured_error`

Oba testa očekuju da odsustvo API ključa vrati strukturiranu grešku, ali
dobijaju uspješan HTTP odgovor — test **nije hermetički izolovan** od
`.env.local`, process env cache-a, ili globalnog settings singletona.

**Popravka:** izolovati fixture tako da test garantovano vidi prazan
`OPENAI_API_KEY`/`EXA_API_KEY`, bez obzira na lokalni `.env.local` ili
prethodno keširan settings state. Ne smije pozvati stvaran API poziv.

## Zabranjeno
- ne mijenjati stvarnu tool politiku (npr. vraćati `requires_computer_mode`
  na `True`) — implementacija je namjerna, test se prilagođava njoj
- ne dirati `python_backend/app/agent/tool_catalog/phase11.py` osim ako
  test izolacija to zaista zahtijeva (provjeriti prvo je li problem čisto
  u fixture-ima)
- ne dirati thumbnail fajlove (upravo commitovano, QM-6 zatvoreno)

## Test
```bash
cd python_backend && python -m pytest -q
```
Očekivano: **412 passed, 0 failed** (trenutno 409 passed, 3 failed).

Dodatno, potvrditi da testovi ne zovu mrežu bez eksplicitnog markera —
pokrenuti sa `--disable-socket` ako je dostupno, ili ručno provjeriti da
fixture za prazan API ključ zaista blokira izlazni poziv.

## Agent report
`agent_reports/YYYY-MM-DD_qm0-test-baseline-fix.md` — standardni format
(šta/zašto/kako/šta nije dirano/verifikacija).
