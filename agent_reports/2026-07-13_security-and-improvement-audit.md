# Security and improvement audit

## Datum

2026-07-13

## Scope

Read-only sigurnosni i arhitektonski pregled ključnih Electron, Realtime, Python tool, permission, confirmation, cancellation, storage, privacy i packaging tokova. Konačni izvještaj je arhiviran u `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`.

## GitNexus impact

GitNexus indeks je osvježen. Izmjene su samo dokumentacione; nisu mijenjani runtime simboli, API rute ni execution flowovi, pa simbolski pre-change impact nije primjenjiv.

## Šta je urađeno

- Provjerene su stvarne sigurnosne kontrole i njihovi call siteovi.
- Identifikovana su tri CRITICAL puta: model-controlled Computer Mode, `shell=True` u `computer_open_app` i proizvoljna lokalna thumbnail referenca koja može biti poslata cloud servisu.
- Dokumentovani su confirmation replay, ograničeno cancellation ponašanje, UIA privacy/target gapovi, frontend test gap, packaged data lokacija i dodatni hardening nalazi.
- Napravljen je prioritetizovan plan malih PR-ova za solo developera.

## Zašto je urađeno

Korisnik je tražio provjerljiv, konačan Markdown izvještaj nakon detaljnog pregleda aplikacije i samoprovjere prethodno iznesenih zaključaka.

## Kako je urađeno

Direktno su pročitani relevantni moduli, testovi, tool specs, postojeći sigurnosni dokumenti i packaging konfiguracija. Nalazi su provjereni pretragom call siteova i izvršavanjem dostupnih quality provjera.

## Šta nije dirano

- Runtime kod nije mijenjan.
- Postojeće necommitovane izmjene drugih agenata nisu dirane.
- `docs/MIGRATION_PLAN.md` nije mijenjan jer nijedna faza nije promijenila status.
- Nije napravljen commit.

## Verifikacija

- `npx gitnexus analyze --force` — prošao.
- `npm run typecheck` — prošao.
- `npm run build` — prošao; CSP prisutan u built HTML-u.
- `python -m pytest -q` — 251 passed.
- `npm audit --omit=dev` — 0 poznatih produkcijskih ranjivosti.

## Rizici/ograničenja

GitNexus konceptualna FTS pretraga je i nakon reindeksiranja prijavljivala nedostajući FTS indeks, pa je audit oslonjen na direktno čitanje koda i tačne tekstualne pretrage. Packaged data-dir nalaz je jaka Windows deployment inferencija; treba ga potvrditi installer testom kao standardni korisnik.

## Potreban follow-up

Prvo implementirati Security PR A iz konačnog izvještaja: ukloniti model-facing `set_mode`, deaktivirati/popraviti `computer_open_app` i ukloniti `shell=True`.

## Potrebna korisnička potvrda

Korisnik treba odabrati da li se prvo radi Security PR A kao zaseban mali PR.
