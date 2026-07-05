# Agent report — Podjela rada Claude Code vs Codex po fazama

**Datum:** 2026-07-05

## Scope

- Izmjena: `docs/MIGRATION_PLAN.md` (dodana kolona "Agent" u Status faza tabelu).

## GitNexus impact

Nije relevantno — dokumentacioni fajl, bez izmjene koda.

## Šta je urađeno

Korisnik je tražio kratku (ne token-tešku) procjenu koje faze da delegira Codex-u, a koje da zadrži za Claude Code, bez pisanja punih detaljnih Codex prompt-ova (Codex treba sam pročitati `docs/MIGRATION_PLAN.md` i njegov "Master prompt"). Dodijeljena je preporuka po principu:

- **Codex**: mehaničke, izolovane, već precizno specificirane faze (novi fajlovi, jasan spec u planu/dokumentima) — FAZA 4, 5, 7, 8, 9, 11, 12, 16, 17, 18, 19 (draft).
- **Claude Code**: faze koje diraju već-radeću funkcionalnost, sigurnosno-kritične slojeve, ili su arhitektonski centralne — FAZA 0-3 (već rađeno), FAZA 6 (Realtime session security — dira live voice-auth), FAZA 10 (permission system — sigurnosni gate), FAZA 13 (computer-use v1 — 1:1 zamjena PowerShell alata koje sam upravo izvukao u FAZI 3, treba provjera ponašanja), FAZA 14 (computer-use v2 — eksplorativno, UIA), FAZA 15 (agent runtime — arhitektonski centralno), FAZA 19 verifikacija (build/packaging provjera).

## Zašto je urađeno

Korisnik radi sa oba agenta paralelno i želi izbjeći nepotrebno trošenje tokena na duge eksplicitne Codex instrukcije — Codex treba sam čitati plan. Podjela je zapisana u `MIGRATION_PLAN.md` da bude trajna referenca, ne samo u chat istoriji.

## Kako je urađeno

`Edit` na `docs/MIGRATION_PLAN.md` — dodana kolona "Agent" u postojeću Status faza tabelu, plus kratko objašnjenje principa iznad tabele.

## Šta nije dirano

- Nijedan Codex prompt nije pisan u punom obliku — korisnik dobija samo kratku instrukciju da uputi Codex na `docs/MIGRATION_PLAN.md` Master prompt sekciju.
- Kod — bez izmjena.

## Verifikacija

Ručna provjera da su sve faze 0-19 dobile vrijednost u novoj koloni, bez rupa.

## Rizici / ograničenja

- Ovo je preporuka, ne fiksno pravilo — korisnik može dodijeliti fazu drugom agentu ako se pokaže praktičnije (npr. ako je Codex slobodan a Claude Code zauzet, ili obrnuto).
- Podjela pretpostavlja da Codex radi iz istog repo-a i ima pristup `docs/MIGRATION_PLAN.md` — ako Codex radi iz drugog konteksta (npr. bez pristupa repo-u), instrukciju treba prilagoditi.

## Potreban follow-up

Nema neposrednog. Sljedeći aktivan korak je i dalje FAZA 4 (dodijeljena Codex-u).

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
