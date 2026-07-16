# Agent Report — Plans Panel P2 (agent predlaže planove)

- Datum: 2026-07-16
- Agent: pi
- Faza: P2 — create_plan tool + prompt

## Šta je urađeno

### 1. create_plan Python tool (app/tools/plans.py)
- Handler poziva PlanService.create() sa title, summary, steps
- Plan se kreira u 'proposed' statusu → pojavljuje se u Predloženi tab
- Steps: niz {title: "..."} objekata ili običnih stringova
- Vraća plan_id, title, status, steps_count, message

### 2. Registracija
- phase13.py: create_plan (risk=low, no confirmation, timeout 10s)
- realtimeToolSpecs.cjs: dodata funkcija sa model instrukcijama
- PHASE11_DELEGATED_TOOLS: dodat "create_plan"

### 3. System prompt — # Plans sekcija
- Agent predlaže plan za 3+ koraka, eksterne aplikacije, browsere, fajlove, email, instalaciju, high-risk alate
- Plan ide u Predloženi — korisnik odobrava
- NE izvršavati akcione korake dok plan nije approved
- Poslije odobrenja: korak po korak, ažurirati status

## Fajlovi
- Novi: python_backend/app/tools/plans.py
- Izmijenjeni: phase13.py, realtimeToolSpecs.cjs, main.cjs, realtime.cjs

## Provjere
- node --check OK, tsc čist, build OK
- Python import OK

## Dopuna — završni P2 hardening (Codex)

- create_plan više ne zahtijeva computer mode; alat je namjerno low-risk i bez confirmation-a.
- create_plan handler sada dobija PlanService kroz registry services, pa test/app instanca i produkcijska instanca koriste isti storage kontekst.
- Schema za steps je usklađena između Python tool catalog-a i Realtime tool spec-a: prihvata string korake i `{title: "..."}` objekte.
- Dodani regression testovi:
  - create_plan je registrovan u `/tools` sa očekivanim safety flagovima;
  - `/tools/execute` kreira `proposed` plan i plan se vidi kroz `/plans`.
- Verifikacija završne dopune:
  - `python -m pytest -q tests\test_plans.py --basetemp=.tmp-tests\pytest-plans-p2-hardening` → 9 passed
  - `npm run typecheck` → passed
  - `npm run check` → passed
