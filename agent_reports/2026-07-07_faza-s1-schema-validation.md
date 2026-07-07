# Agent Report — FAZA S-1: Runtime schema validacija argumenata alata

**Datum:** 2026-07-07
**Agent:** Claude Code
**Scope:** Sigurnosni backlog, FAZA S-1 iz `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md` (stavka S2). Prva implementaciona faza sigurnosnog plana izvedenog iz Fable-5/Codex konsultacije.

---

## GitNexus impact

`gitnexus_impact` na `ToolExecutor.execute` (upstream): **risk = LOW**, 1 direktni pozivalac (`execute_tool` u `app/api/tools.py`), 1 proces (`execute_tool`), 1 modul (Agent). Napomena: isti `ToolExecutor` instanca koristi i agent runtime (`LocalDesktopAssistant`), pa validacija automatski pokriva i `POST /tools/execute` i model-driven tool pozive — nema zaobilaznog puta. Prijavljeno korisniku prije izmjene.

---

## Šta je urađeno

1. **Novi modul `app/agent/arg_validation.py`** — `validate_tool_arguments(input_schema, arguments) -> str | None`. Koristi `jsonschema.Draft202012Validator`. Vraća `None` ako su argumenti validni, ili čitljivu poruku o prvoj grešci. **Fail-closed:** `check_schema()` prvo validira samu schemu; svaki izuzetak tokom validacije se tretira kao greška (nikad se ne "proguta" u prolaz).
2. **`app/agent/tool_executor.py`** — poziv validacije umetnut u `execute()` odmah nakon provjere `enabled`, prije cancellation/permission (dokumentovani "koraci 1-3"). Na neuspjeh vraća postojeći `INVALID_ARGUMENTS` error response; handler se NE poziva.
3. **`pyproject.toml`** — `jsonschema` deklarisan eksplicitno (bio tranzitivno prisutan, v4.26.0).
4. **Testovi `tests/test_arg_validation.py`** — 10 testova: validni prolaze; missing required / extra field (`additionalProperties:false`) / pogrešan tip / enum van opsega / broj van min-max odbijeni; neispravna schema fail-closed; executor-level test da handler NIJE pozvan pri nevažećim argumentima + da se poziva pri validnim.
5. **`tests/test_action_log.py`** — ažuriran jedan postojeći assert: `echo` sa `{}` sad odbija schema validacija (poruka "'text' is a required property") prije handlerove ValueError; kod greške ostaje `INVALID_ARGUMENTS`.

## Zašto

`input_schema` je do sada bio samo oglašen modelu (`prompt_builder.py` ga šalje kao OpenAI `parameters`), a nikad enforce-ovan na backendu. Model — ili injektovana instrukcija, ili maliciozan/malformiran poziv — mogao je proslijediti viška polja, pogrešne tipove ili enum van opsega, a handler bi svejedno radio (oslanjajući se na ad-hoc `.get()`/ValueError). Ovo zatvara cijelu klasu tih napada i pretvara deklarisana ograničenja u stvarnu backend kontrolu.

## Kako

Validacija na najranijoj tački (prije cancellation record-a i permission gate-a), tako da nevažeći poziv nikad ne pokrene ni cancellation ni OS handler. Jedan izvor validacije za sve alatke (i API i agent runtime dijele isti `ToolExecutor`).

## Šta NIJE dirano
- Nijedna tool definicija/schema (postojeće schema su već bile dobre — samo se sad enforce-uju).
- Permission engine, active-window, confirmation logika — netaknuti.
- Nijedan drugi sloj (Electron, glasovni pipeline).

## Verifikacija
- `python -m pytest -q` → **189 passed, 1 warning** (warning je pre-postojeći starlette/httpx deprecation, nevezan).
- Novi test `test_malformed_schema_fails_closed` je tokom razvoja uhvatio stvaran bug u prvoj verziji validatora (neispravna schema nije bacala `SchemaError` pri konstrukciji nego tek pri iteraciji) — popravljeno da fail-closed radi ispravno.

## Rizici / ograničenja
- **Ponašajna promjena:** argumenti koji su ranije "prolazili" a krše schemu sad se odbijaju. Provjereno da nijedan postojeći test/tok legitimno ne šalje viška polja (dvije schema imaju `additionalProperties: True` — `records fields`, `artifact_show` — i one i dalje prolaze). Ako neki UI/agent tok šalje nedeklarisana polja, sad će dobiti `INVALID_ARGUMENTS` — to je namjera, ali treba pratiti.
- Validacija pokriva JSON Schema podskup koji `jsonschema` podržava (sve što naše schema koriste: type/properties/required/additionalProperties/enum/min/max/items).

## Potreban follow-up
- Sljedeće faze iz `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md`: **S-2 (prompt injection tretman)** i **S-9 (red-team test set)** — preporučeni sljedeći, oba 🔴.
- `jsonschema` će biti hash-pinovan u FAZI S-5 (supply chain).

## Potrebna korisnička potvrda
- Da li commitovati FAZU S-1 (kod + testovi + plan doc + ovaj report) kao zaseban commit prije nego što krenemo na S-2? (Preporuka: da — mala, čista, testirana promjena.)
