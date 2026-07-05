# Agent report — Integracija SECURITY_HARDENING_PLAN.md (dokumentacioni korak)

**Datum:** 2026-07-05

## Scope

- Novi: `docs/SECURITY_HARDENING_PLAN.md`.
- Izmjena: `docs/SECURITY_MODEL.md` (referenca na novi plan kao autoritativan za produkciju).
- Izmjena: `docs/MIGRATION_PLAN.md` (nova sekcija "Security Gates"; FAZA 13/14 status kolona označena BLOCKED).
- Izmjena: `docs/TOOL_CONTRACTS.md` (schema proširena novim poljima: `requires_active_window_match`, `allowed_apps`, `blocked_apps`, `logs_action_receipt`).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Korisnik je (zajedno sa ChatGPT-jem) napisao novi produkcijski sigurnosni plan `SECURITY_HARDENING_PLAN.md` (24 sekcije — security gates, threat model, Electron/Python/tool/document/network hardening, prompt injection zaštita, logging/redaction, encryption, supply-chain, self-test, testing checklist, incident response). Plan je dostavljen kao zalijepljen tekst sa pokvarenim enkodingom (mojibake — UTF-8 dijakritici prikazani kao "Ä", "Å¾" itd.).

Analiza (prije ovog koraka) je potvrdila da nema tvrdih konflikata sa postojećim `SECURITY_MODEL.md`, `TOOL_CONTRACTS.md` i `MIGRATION_PLAN.md` — novi plan je kompatibilan superset. Korisnik je potvrdio analizu (nakon konsultacije sa ChatGPT-jem) i eksplicitno odobrio četiri koraka integracije, uz instrukciju da se enkoding popravi ručnom rekonstrukcijom iz konteksta, a ne bukvalnim kopiranjem mojibake teksta.

Implementirano tačno po dogovoru:

1. **`docs/SECURITY_HARDENING_PLAN.md`** — sačuvan sa ispravnim UTF-8/latinica enkodingom, sadržaj rekonstruisan iz konteksta (sve 24 sekcije, bez izmjene značenja).
2. **`docs/SECURITY_MODEL.md`** — dodata napomena na vrh da je `SECURITY_HARDENING_PLAN.md` autoritativan za produkcijski build, sa pravilom da u slučaju razilaženja važi noviji plan.
3. **`docs/MIGRATION_PLAN.md`** — dodata nova sekcija "Security Gates" (nakon "Backlog / Future Epics", prije "Redoslijed PR-ova") koja mapira Gate 0/1/2 na postojeće brojeve faza bez renumeracije. Eksplicitno navedeno da su FAZA 13 i FAZA 14 (computer-use v1/v2) BLOCKED dok Security Gate 0 nije zatvoren — isto naznačeno i u Status koloni glavne tabele faza. Dodata napomena da je dovršetak FAZE 3 (`core/ipc.cjs` izdvajanje, trenutno odgođeno) praktični preduslov za Security PR-1 (generic IPC zabrana, preload inventar).
4. **`docs/TOOL_CONTRACTS.md`** — tool manifest schema primjer proširen sa `requires_active_window_match`, `allowed_apps`, `blocked_apps`, `logs_action_receipt` (uz kratko objašnjenje da su obavezni za computer-use toolove), i dodata referenca na `SECURITY_HARDENING_PLAN.md` u završnoj napomeni.

## Zašto je urađeno

Korisnik gradi ovaj plan sa ChatGPT-jem kao spoljnim planerom i traži da Claude Code radi repo-utemeljenu analizu i integraciju, umjesto da se plan uvede kao proizvoljan copy-paste. Cilj je da sigurnost bude ugrađena prije širenja computer-use funkcionalnosti (FAZA 13/14), u skladu sa postojećim pravilom repo-a da se ne preskaču faze niti uvodi rizičan kod bez permission sloja.

## Kako je urađeno

`Write` za novi `SECURITY_HARDENING_PLAN.md` (ručna rekonstrukcija iz mojibake izvora, sekcija po sekcija, bez promjene sadržaja/značenja). `Edit` na `SECURITY_MODEL.md`, `MIGRATION_PLAN.md` (dva mjesta: status tabela + nova sekcija), `TOOL_CONTRACTS.md`.

## Šta nije dirano

- Nijedan kod (`electron/`, `src/`) — potvrđeno u planu samom, sekcija "Ne radi odmah" eksplicitno zabranjuje implementaciju kontrola u ovom koraku.
- Numeracija postojećih faza u `MIGRATION_PLAN.md` — nepromijenjena; Security Gates referenciraju postojeće brojeve, ne dodaju nove.
- `docs/DOCUMENT_ENGINE_FUTURE_EPIC.md` — nije mijenjan iako Gate 1 djelimično zavisi od njegove aktivacije; ostaje netaknut dok se epic ne aktivira.

## Verifikacija

Ručna provjera da: (a) `SECURITY_HARDENING_PLAN.md` nema preostalih mojibake karaktera, (b) `MIGRATION_PLAN.md` FAZA 0-19 numeracija nepromijenjena, (c) linkovi između sva četiri dokumenta (`SECURITY_MODEL.md` ↔ `SECURITY_HARDENING_PLAN.md` ↔ `MIGRATION_PLAN.md` ↔ `TOOL_CONTRACTS.md`) konzistentni i rade u oba smjera.

## Rizici / ograničenja

- Security Gate 0 status je trenutno "Nije zatvoren" — ovo je i dalje samo dokumentacija; stvarno zatvaranje gate-a zahtijeva implementaciju kroz FAZA 3 (dovršetak), 4, 5, 6, 10, 11, što je predstojeći rad, ne završen.
- Legacy PowerShell computer-use u `electron/main.cjs` i dalje radi bez permission sloja (poznat, već dokumentovan rizik) — ovaj korak ga formalizuje kao produkcijski BLOCKER, ali ga ne uklanja niti mitigira odmah.
- Enkoding rekonstrukcija je urađena ručno na osnovu konteksta (kako je korisnik i tražio); nije bajt-za-bajt provjerena protiv originalnog ChatGPT izvora, samo semantički vjerna.

## Potreban follow-up

- FAZA 3 dovršetak (`core/ipc.cjs`) treba se uraditi prije ili zajedno sa Security PR-1, po novoj napomeni u "Security Gates" sekciji.
- Kad korisnik odluči da aktivno počne sa Security PR-1..4 implementacijom (van dokumentacije), potrebna je nova runda GitNexus impact analize jer će te izmjene dirati `electron/main.cjs` i (kasnije) Python backend kod.
- Sljedeći aktivan korak po planu je i dalje FAZA 4 (Python backend skeleton, dodijeljena Codex-u) — ovaj sigurnosni dokumentacioni korak ne mijenja taj redoslijed, samo dodaje gate kriterijume koji moraju biti zadovoljeni prije FAZE 13/14.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak. Preporučeno: pregledati da li novododata "Security Gates" sekcija u `MIGRATION_PLAN.md` i dalje odražava ono što je dogovoreno sa ChatGPT-jem, prije nego što se ovaj korak smatra zatvorenim.
