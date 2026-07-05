# Agent report — Agent workflow setup (agent_reports + CLAUDE.md/AGENTS.md, FAZA 2)

**Datum:** 2026-07-04

## Scope

- Novi: `agent_reports/2026-07-04_baseline-and-docs.md` (backfill izvještaj za FAZU 0+1), `agent_reports/2026-07-04_agent-workflow-setup.md` (ovaj fajl).
- Novi: `CLAUDE.md`, `AGENTS.md`.
- Izmjena: `docs/MIGRATION_PLAN.md` (tracker tabela, status FAZE 2, sitna markdownlint ispravka separator reda tabele).

## GitNexus impact

Nije relevantno — samo dokumentacioni/procesni fajlovi, nema izmjene koda ni ponašanja aplikacije.

## Šta je urađeno

- Korisnik je uputio na `C:\Users\38765\Desktop\FieldFix IT\agent_reports` kao referencu za format i workflow koji već koristi na drugom projektu.
- Pročitani primjeri (`2026-06-29_agent-workflow-claude-md.md`, `2026-07-01_code-traceability-comments.md`) da se razumije tačan obrazac: agent_reports fajl po zadatku (Datum, Scope, GitNexus impact, Šta je urađeno, Zašto, Kako, Šta nije dirano, Verifikacija, Rizici, Potreban follow-up, Potrebna korisnička potvrda) i konvencija `Context: agent_reports/...` komentara u kodu — samo na funkcionalno značajnim mjestima (ulazne tačke bitnog toka ili neobično rješenje), ne u svakoj funkciji.
- Provjereno da su trenutni `CLAUDE.md`/`AGENTS.md` na FieldFix IT samo GitNexus auto-blok — objašnjeno git istorijom (`git log -- CLAUDE.md AGENTS.md`): commit "ukloni AI instrukcije iz javnog repo-a" je namjerno uklonio ručni sadržaj prije javnog objavljivanja repo-a. Znači, sadržaj workflow-a je uzet iz `agent_reports` opisa, ne iz trenutnog stanja tih fajlova.
- Napisan `agent_reports/2026-07-04_baseline-and-docs.md` kao backfill izvještaj za već urađenu FAZU 0 i FAZU 1 (koje su urađene prije nego što je ova konvencija uspostavljena u ovom repo-u).
- Napisan `CLAUDE.md` za `Naš-agent`: jezik (srpski/bosanski), arhitektonsko pravilo, GitNexus disciplina (uslovna — "ako je indeksiran"/"ako nije"), obavezna procedura nakon zadatka (5 koraka: git status, agent report, `Context:` komentar link, GitNexus refresh, ažuriranje tracker tabele), memorija (nema MCP memory servera, repo docs + Claude Code auto-memory).
- Napisan `AGENTS.md`: kraći, cross-referencira `CLAUDE.md` da se izbjegne dupliranje (isti pattern kao na FieldFix IT — "AGENTS.md dopunjen sa cross-referencom ka CLAUDE.md da se ne duplira jezik/git/memory/procedura").
- Ažurirana `docs/MIGRATION_PLAN.md` tracker tabela — FAZA 2 označena kao urađena.

## Zašto je urađeno

Korisnik eksplicitno traži da se isti radni obrazac (agent_reports + link u kodu ka odluci) koji koristi na FieldFix IT projektu primijeni i ovdje, prije nego što se nastavi sa FAZOM 3 (razbijanje `electron/main.cjs`) — kako bi svaka buduća netrivijalna odluka bila dokumentovana i vidljiva u kodu, ne samo u chat istoriji.

## Kako je urađeno

`Read` na FieldFix IT `agent_reports/*.md` i `CLAUDE.md`/`AGENTS.md` (samo čitanje, ništa mijenjano na FieldFix IT projektu). `git log` provjera istorije tih fajlova. `Write` za nove fajlove u `Naš-agent`, `Edit` za tracker tabelu u `MIGRATION_PLAN.md`.

## Šta nije dirano

- FieldFix IT projekat — samo čitan, ništa izmijenjeno.
- `electron/main.cjs`, `src/` kod u `Naš-agent` — i dalje netaknuti (FAZA 3 tek dolazi, tada će prve `Context:` reference u kodu biti dodate).
- GitNexus indeksiranje ovog repo-a — nije provjereno niti pokretano u ovom koraku.

## Verifikacija

- Ručna provjera da su sva tri nova/izmijenjena markdown fajla čitljiva i unutar sebe konzistentno linkuju jedno na drugo (`CLAUDE.md` ↔ `AGENTS.md` ↔ `docs/MIGRATION_PLAN.md` ↔ `agent_reports/`).
- IDE markdownlint upozorenje (MD060, stil tabele) u `MIGRATION_PLAN.md` primijećeno preko hook diagnostike i ispravljeno (separator red tabele usklađen sa "compact" stilom).

## Rizici / ograničenja

- Konvencija `Context: agent_reports/...` komentara još nema nijedan primjer u ovom repo-u (kod se još nije mijenjao) — prva prava primjena će biti u FAZI 3, kad se `electron/main.cjs` počne razbijati u module.
- Ako se GitNexus kasnije podesi za ovaj repo, `CLAUDE.md` bi trebalo dopuniti GitNexus-specifičnim resursima/alatima (po uzoru na FieldFix IT `CLAUDE.md` gitnexus blok), pošto trenutna verzija samo uslovno pominje GitNexus bez konkretnih resource putanja.

## Potreban follow-up

FAZA 3: razbiti `electron/main.cjs` u module bez promjene ponašanja. Prva prilika da se primijeni `Context:` komentar konvencija — npr. iznad IPC setup-a ili PowerShell runner-a, ako se pokaže da je to netrivijalna odluka vrijedna objašnjenja.

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — ovo su samo dokumentacioni/procesni fajlovi. Korisnik treba samo da potvrdi da je ovaj CLAUDE.md/AGENTS.md format ono što je htio prije nego što se pređe na FAZU 3.
