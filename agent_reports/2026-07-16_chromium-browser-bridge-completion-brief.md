# Chromium Browser Bridge completion brief

## Datum

2026-07-16

## Scope

Detaljan delegacijski brif za završetak stvarnog end-to-end rada Browser Bridgea sa više Chromium browsera i profila.

## GitNexus impact

- Repo indeks prijavljuje 6772 simbola i 172 toka, ali je staleness/FTS ostao degradiran i nakon incremental reindexa.
- Direktni konteksti potvrđuju da `BrowserExtensionBroker` koristi `app/main.py`, status API, browser tool i testovi.
- `get_bridge_status` ide kroz `get_pairing_display/ensure_secret`.
- `SettingsPanel` trenutno nema browser bridge pozive.
- `_handle_browser_tabs` ide kroz globalni `get_broker` bez stabilnog profila.
- Izmjena root sekcije migration trackera: LOW, bez pozivalaca ili pogođenih procesa.

## Šta je urađeno

- Napravljen `docs/PI_CHROMIUM_BROWSER_BRIDGE_COMPLETION_BRIEF.md`.
- Definisani su browser support matrix, multi-connection registry, per-profile identitet, jednokratni pairing, Settings UX, discovery, tool routing, otvaranje nove kartice, sigurnost, faze C0–C4 i live E2E kriteriji.
- Tracker je označio completion paket kao planiran, ne implementiran.

## Zašto je urađeno

Postojeća 41 testa koriste mock extension klijent. Na stvarnom računaru Ricky ekstenzija nije instalirana, port 9119 nema aktivnu vezu, Settings nema pairing tok, backend prikazuje samo fragment secreta, a broker podržava jednu vezu. Zbog toga agent ne može vidjeti stvarne tabove.

## Kako je urađeno

Brif razdvaja consumer-safe vođenu instalaciju od uparivanja, zamjenjuje globalni secret jednokratnim tokenom i per-profile credentialom, te zahtijeva routing prema browser/profile identitetu i stvarni smoke matrix.

## Šta nije dirano

- Nije implementiran runtime fix.
- Nisu instalirane ekstenzije niti mijenjani browser profili.
- Nisu mijenjani broker, Settings, Electron ni tool runtime simboli.
- Nisu dirane nepovezane worktree izmjene.

## Verifikacija

- Pročitani su manifest/options/service-worker, broker, status API i GitNexus konteksti ključnih simbola.
- Lokalna provjera je pokazala da Ricky ekstenzija nije među instaliranim Brave ekstenzijama i nema aktivne veze na 9119.
- Dokumenti su provjereni sa `git diff --check` nakon izmjene.

## Rizici/ograničenja

Browser store objava i korisnička instalacija zavise od politika svakog vendora. Silent install nije prihvatljiv consumer default. Tier 2 forkovi ne mogu se smatrati live verifikovanim bez stvarnog compatibility testa.

## Potreban follow-up

Delegirati C0 pi agentu: Settings pairing jednog Brave profila i obavezni pravi list/count/activate smoke test prije multi-browser proširenja.

## Potrebna korisnička potvrda

Za produkciju će biti potrebna odluka o objavi ekstenzije u Chrome Web Storeu i Edge Add-onsu; development može početi sa jasno označenim `Load unpacked` tokom.
