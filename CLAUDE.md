# CLAUDE.md — RileyJarvis Windows Hybrid ("Naš-agent")

Ovaj fajl vodi Claude Code (i svaki drugi agent koji radi u ovom repo-u) kroz pravila rada specifična za ovaj projekat. Za pun arhitektonski plan vidi [docs/MIGRATION_PLAN.md](./docs/MIGRATION_PLAN.md) i [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Šta je ovaj projekat

Windows port aplikacije RileyJarvis (originalno macOS-only Electron AI companion), u procesu postepene migracije iz Electron/Node/PowerShell prototipa u hibridnu arhitekturu:

```text
React UI -> Electron (tanak shell/IPC) -> Python backend (agent, tools, storage, automation) -> SQLite
```

Trenutno stanje (2026-07-04): kopija baseline-a iz `RileyJarvis-Windows` repo-a, FAZA 0 i FAZA 1 iz plana su urađene (git baseline + docs). Python backend još ne postoji — sve computer-use funkcionalnosti su i dalje u `electron/main.cjs` preko PowerShell-a.

## Jezik

Komunikacija sa korisnikom i sadržaj dokumenata/izvještaja: srpski/bosanski, latinica. **I interni razgovor sa sobom (thinking / razmišljanja) se piše na srpskom** — korisnik uči uz agenta, pa i proces razmišljanja treba biti na istom jeziku. Kod, imena simbola i commit poruke mogu ostati na engleskom gdje je to konvencija (npr. postojeći JS/TS kod).

## Arhitektonsko pravilo (ne pregovara se)

- React/Electron renderer = UI sloj.
- `electron/main.cjs` (i njegovi budući moduli) = samo app shell, IPC, Python process manager. **Nikad** nova poslovna/agent/computer-use/storage/AI logika direktno u `electron/main.cjs`.
- Python backend (kad se doda, FAZA 4+) = agent runtime, tool registry, automation, storage, AI integracije.
- Detalji: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md), [docs/SECURITY_MODEL.md](./docs/SECURITY_MODEL.md), [docs/TOOL_CONTRACTS.md](./docs/TOOL_CONTRACTS.md).

## Rad po fazama

- Radi se isključivo faza po faza iz [docs/MIGRATION_PLAN.md](./docs/MIGRATION_PLAN.md) — ne preskakati faze, ne raditi veliki rewrite u jednom koraku.
- Prije izmjene postojeće funkcije/klase/metode: pročitati kontekst i pozivaoce (call sites).
- Ako je GitNexus indeksiran za ovaj repo: `gitnexus_impact` prije izmjene simbola, `gitnexus_detect_changes` prije commita, stati i prijaviti korisniku ako je rizik HIGH/CRITICAL, koristiti `gitnexus_rename` umjesto find-and-replace za preimenovanje.
- Ako GitNexus nije indeksiran (trenutno stanje — nije potvrđeno da je ovaj repo indeksiran): ručno pronaći module koji se mijenjaju, pronaći import/call reference, eksplicitno objasniti blast radius korisniku prije izmjene.
- Ne brisati legacy PowerShell toolove dok Python zamjena nije implementirana i testirana.
- Nikad ne izlagati proizvoljni shell execution tool modelu.
- Nikad ne commitovati `.env.local`, API ključeve, `node_modules`, logove sa tajnama, `data/*.sqlite`.

## Obavezna procedura nakon završenog zadatka

1. **Git status / diff provjera** — pogledati šta je stvarno izmijenjeno prije commita (ako se commit traži).
2. **Agent report** — napisati `agent_reports/YYYY-MM-DD_kratak-slug.md` sa sekcijama: Datum, Scope, GitNexus impact, Šta je urađeno, Zašto je urađeno, Kako je urađeno, Šta nije dirano, Verifikacija, Rizici/ograničenja, Potreban follow-up, Potrebna korisnička potvrda. (Isti obrazac kao na FieldFix IT projektu — vidi `agent_reports/2026-07-04_baseline-and-docs.md` u ovom repo-u za primjer.)
3. **Link odluke u kod** — ako je izmjena uvela netrivijalnu odluku ili neobično rješenje u **funkcionalno značajnom** dijelu koda (ulazna tačka bitnog toka, non-obvious workaround), dodati kratak komentar iznad tog mjesta:

   ```text
   // Context: agent_reports/2026-07-04_primjer.md
   ```

   Ne dodavati ovaj komentar u svaku funkciju ili trivijalnu izmjenu — samo tamo gdje bi budući čitalac koda realno pitao "zašto je ovo ovako".
4. **GitNexus refresh** — ako je GitNexus podešen za repo, pokrenuti `gitnexus_detect_changes` / `npx gitnexus analyze` da indeks ostane svjež.
5. **Ažurirati `docs/MIGRATION_PLAN.md` tracker tabelu** — označiti fazu kao urađenu kad acceptance criteria iz `docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` budu ispunjeni.

## Prije commita

- Pokrenuti relevantne testove/build (`npm run typecheck`, `npm run build`, `pytest` kad `python_backend/` postoji).
- Ne skipovati git hookove.
- Nikad ne commitovati bez eksplicitnog zahtjeva korisnika.

## Memorija

Nema MCP memory servera podešenog za ovaj projekat. Izvor istine je repo dokumentacija (`docs/`, `agent_reports/`) plus Claude Code auto-memory (radne navike, feedback od korisnika) između sesija.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **nas_agent** (4560 symbols, 7033 relationships, 140 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/nas_agent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/nas_agent/clusters` | All functional areas |
| `gitnexus://repo/nas_agent/processes` | All execution flows |
| `gitnexus://repo/nas_agent/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
