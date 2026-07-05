# AGENTS.md — RileyJarvis Windows Hybrid

Ovaj fajl važi za sve agente (Codex, Claude Code, ili druge) koji rade u ovom repo-u. Za jezik, git identitet, agent_reports proceduru i memorijski model — vidi [CLAUDE.md](./CLAUDE.md), ne duplirati ovdje.

## Project name

RileyJarvis Windows Hybrid ("Naš-agent") — Windows port RileyJarvis Electron AI companion-a, u migraciji ka Electron (UI shell) + Python (backend brain) arhitekturi. Pun plan: [docs/MIGRATION_PLAN.md](./docs/MIGRATION_PLAN.md).

## Architecture rule

- Electron/React je UI shell.
- Python backend (kad postoji) je vlasnik agent runtime-a, toolova, storage-a, automation-a i AI integracija.
- **Do not add new business logic to `electron/main.cjs`.** Ovo pravilo je apsolutno i ne mijenja se po fazi.

## Do not do

- Ne dodavati novu agent/computer-use/storage/AI logiku u `electron/main.cjs`.
- Ne dodavati proizvoljni shell execution tool izložen modelu.
- Ne brisati legacy PowerShell computer-use toolove dok Python zamjena nije testirana.
- Ne commitovati tajne, `.env.local`, `node_modules`, logove, lokalne baze.

## Before editing

- Pregledati modul i njegove pozivaoce (call sites).
- Ako je GitNexus dostupan za ovaj repo, pokrenuti impact analysis prije izmjene simbola.
- Ako GitNexus nije dostupan, ručno prijaviti blast radius korisniku.

## Before commit

- Pokrenuti relevantne testove/lint/typecheck.
- Pokrenuti `gitnexus_detect_changes` ako je GitNexus dostupan.
- Napisati `agent_reports/` izvještaj i po potrebi ažurirati `docs/MIGRATION_PLAN.md` tracker (vidi [CLAUDE.md](./CLAUDE.md) za tačan format).
- Sažeti izmijenjene module i promjene ponašanja korisniku.

## Prefer small PRs

Raditi fazu po fazu iz [docs/MIGRATION_PLAN.md](./docs/MIGRATION_PLAN.md), jedna faza = jedan mali skup promjena. Ne raditi veliki rewrite u jednom koraku.
