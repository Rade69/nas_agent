# Agent report — R2b: legacy JSON DB helpers → electron/core/legacyDb.cjs

**Datum pisanja:** 2026-07-09
**Brief:** `docs/refactor_plan.md` sekcija "R2 — electron/main.cjs split", podsekcija "R2b".
**Izvršilac:** pi · **Vlasnik plana:** Claude (verifikuje).
**Tip:** Mehanički refactor — verbatim premještanje, ponašanje nepromijenjeno, legacy kod NIJE obrisan.

## Scope

Izvukao ~75 ln legacy JSON DB helper funkcija iz `electron/main.cjs` (1600 → 1533 ln)
u novi `electron/core/legacyDb.cjs`. `main.cjs` ih sad `require`-uje i poziva isto kao prije.

## Lista premještenih funkcija (po imenu, PRIJE premještanja)

| Funkcija | Orig. linija (u 1600-ln main.cjs) | Svrha |
| --- | --- | --- |
| `ensureData()` | 93 | mkdir + ensure dbPath exists |
| `readDb()` | 102 | read + normalize JSON db |
| `writeDb(db)` | 108 | write JSON db |
| `updateDb(mutator)` | 113 | queued read-mutate-write (uses `dbWriteQueue`) |
| `asObject(value)` | 124 | safe-object guard |
| `defaultDb()` | 128 | default db shape (notes/records/thumbnailBoard) |
| `normalizeDb(db)` | 144 | schema-coerce legacy db |

Također premješteno: `let dbWriteQueue = Promise.resolve();` (orig. linija 60) —
`dbWriteQueue` se koristi SAMO unutar `updateDb`, nikad van nje (grep potvrđeno), pa
je enkapsuliran u modul.

**Nije premješteno:** `clearStartupLoadingThumbnails()` (orig. 168) — to je thumbnail
biznis logika (R2c teritorija), koristi `readDb`/`writeDb` ali nije DB helper. Ostaje u main.cjs.

## Zavisnosti i kako su riješene (bez circular require)

DB helperi referenciraju slobodne varijable: `fs`, `path`, `dataDir`, `dbPath`, `dbWriteQueue`.
- `fs`/`path`: legacyDb.cjs ih sam `require("node:fs/promises")` / `require("node:path")`
  — nema Electron `app` dependency (dataDir se računa iz `process.cwd()`, isto kao u main.cjs).
- `dataDir`/`dbPath`: legacyDb.cjs ima svoje top-level definicije
  (`path.join(process.cwd(), "data")` / `ricky-db.json`) — identične vrijednosti kao main.cjs.
  main.cjs ZADRŽAVA svoje `dataDir`/`dbPath` (linije 57–58) jer ih i dalje koristi za
  screenshot/image/thumbnail putanje (l. 672, 858, 859). Duplikacija definicija je prihvatljiva
  — obje računaju isto; izbjegnuta je bilo kakva izmjena tijela funkcija.
- `dbWriteQueue`: premješten u legacyDb.cjs kao top-level `let` (samo `updateDb` ga koristi).

**Nema circular require-a:** legacyDb.cjs require-uje isključivo Node builtine (`fs`, `path`).
NIKAD `main.cjs` niti `electron` core modul. Brief R2 pravilo 3 ispunjeno.

## Koraci izvedeni (tačno po briefu R2b)

1. **Identifikacija** skupa DB helpera (7 funkcija, 93–166) + `dbWriteQueue` (60).
   Grep potvrdio: `dbWriteQueue` se koristi samo u `updateDb` (l. 114, 120).
2. **Kreiran `electron/core/legacyDb.cjs`:**
   - Vrh: `require("node:fs/promises")`, `require("node:path")`, sopstveni
     `dataDir`/`dbPath`/`dbWriteQueue`.
   - 7 funkcija premješteno **verbatim** (tijela bajt-identična, 0 uvlačenja).
   - `module.exports = { ensureData, readDb, writeDb, updateDb, asObject, defaultDb, normalizeDb };`
3. **`main.cjs` prespojen:**
   - Obrisano `let dbWriteQueue = Promise.resolve();` (orig. 60).
   - Dodano `const { ensureData, readDb, writeDb, updateDb, asObject, defaultDb, normalizeDb } = require("./core/legacyDb.cjs");`
     odmah poslije `realtimeToolSpecs` require-a.
   - Obrisane 7 funkcija (orig. 93–166 + blank 167).
   - `dataDir`/`dbPath` (57–58) ZADRŽANI.
4. `npm run build` + `node -e "require('./electron/core/legacyDb.cjs')"` (load-smoke) + grep.

## Verifikacija (acceptance criteria iz briefa)

| Kriterij | Očekivano | Dobiveno |
| --- | --- | --- |
| `main.cjs` veličina | ~1506 ln | **1533 ln** (1600 → 1533, -67 ln) — blizu procjeni; razlika jer je 7 funkcija ~74 ln + dbWriteQueue 1 ln + dodat require blok ~9 ln → neto -67 |
| `legacyDb.cjs` postoji sa svim DB helperima | 7 funkcija | ✓ (svih 7 exportovano, `Object.keys(require(...))` = sva 7 imena) |
| `npm run build` | čisto | ✓ (samo pre-postojeći 500kB chunk warning, nevezan) |
| load-smoke (`require('./electron/core/legacyDb.cjs')`) | čisto | ✓ `exports: ensureData,readDb,writeDb,updateDb,asObject,defaultDb,normalizeDb` |
| grep: nijedno staro ime funkcije definisano dvaput u main.cjs | prazno | ✓ nema duplikata (`^(async )?function (ensureData|readDb|...)` → 0 hitova u main.cjs) |
| `dbWriteQueue` uklonjen iz main.cjs | čisto | ✓ 0 hitova |
| verbatim diff dokaz | nula razlika u tijelima | ✓ (vidi dolje) |

### Verbatim diff dokaz (bajt-identična tijela)
```
diff <(sed -n '93,166p' /tmp/r2b-main.cjs.orig) <(sed -n '17,90p' electron/core/legacyDb.cjs)
→ nula razlika (VERBATIM ✓)
```
`/tmp/r2b-main.cjs.orig` = snimka main.cjs pre-R2b (1600 ln, identično `git show HEAD:electron/main.cjs`).
legacyDb.cjs linije 17–90 = 7 funkcija (bez header importa + module.exports).
Jedina razlika između originala i novog modula: dodatni prazan red nakon zadnje `}` u
legacyDb.cjs (kozmetika, ne utiče na tijela funkcija). Funkcije 1:1 bajt-identične.

### Call sites u main.cjs (svi rješeni putem importovanog destructure-a)
- 27 mjesta poziva 7 funkcija (`\b(ensureData|readDb|...|normalizeDb)\(`) — sva rješena
  jer destrukturisani import daje ista imena u istom scope-u. Pozivi nisu dirnuti.

### GitNexus detect_changes (info za Claude)
```
Changes: 2 files, 3 symbols
Affected processes: 0
Risk level: low
Changed symbols: Refactor plan... → docs/refactor_plan.md (druga sesija),
                 Inventar... → docs/refactor_plan.md (druga sesija),
                 toolSpecs → electron/main.cjs
```
**Risk: low, 0 affected processes.** Nema HIGH/CRITICAL. GitNexus nije potpuno
indeksirao .cjs simbole (main.cjs legacy funkcije nisu u graph-u), ali affected
flows = 0 potvrđuje da nijedan izvršni tok nije slomljen.

## Fajlovi dirani (tačna lista)

- `electron/main.cjs` — modifikovan (1600 → 1533 ln): uklonjeno `dbWriteQueue`
  (60) + 7 DB funkcija (93–166); dodat `require("./core/legacyDb.cjs")` destructure
  (~9 ln). `dataDir`/`dbPath` zadržani.
- `electron/core/legacyDb.cjs` — novi (94 ln): header komentar + fs/path/dataDir/
  dbPath/dbWriteQueue + 7 funkcija verbatim + `module.exports`.

**Nije dirano:** `src/*`, `python_backend/*`, `src/styles/*`, `electron/core/*` drugi
fajlovi osim `legacyDb.cjs`, `handleToolsExecute`, IPC handleri, kill-switch/
lifecycle/`currentMode`, R2c teritorija (thumbnail biznis logika).

## Potvrda: ponašanje nepromijenjeno, legacy kod NIJE obrisan

- Funkcije premještene verbatim (diff dokaz: nula razlika u tijelima).
- Nijedno ime, redoslijed argumenata, logika, return vrijednost nije diruta.
- main.cjs poziva iste funkcije, istim imenima, istim scope-om (destrukturisani import).
- `dataDir`/`dbPath` identične vrijednosti u oba fajla (obe iz `process.cwd()`).
- `dbWriteQueue` zadržava singleton semantiku (Node module cache → jednom require-an,
  `let dbWriteQueue` je modul-level singleton, isto ponašanje kao top-level u main.cjs).
- Legacy JSON DB kod (readDb/writeDb/updateDb/normalizeDb) i dalje živ i korišten —
  samo je relociran, nije uklonjen (CLAUDE.md pravilo: legacy ostaje dok Python
  zamjena nije potvrđena).

## Found issues (brief sekcija — NE popravljati u ovom koraku)

- (prazno) — nijedan bug nije zapažen tokom R2b. `dbWriteQueue` duplikacija definicije
  (main.cjs ima svoju `dataDir`/`dbPath`, legacyDb.cjs svoju) je svjesna — izbjegnuta
  izmjena tijela funkcija. Otvoreno pitanje za Claude: da li refactorirati u
  factory `createLegacyDb({ dataDir, dbPath })` (čišće, ali lagana uvlačenja funkcija)
  u zasebnom PR-u, ili ostaviti duplikaciju?

## Status funkcionalnog smoke-a

- **Load-smoke:** urađen ✓ — `require('./electron/core/legacyDb.cjs')` učitava se bez
  greške, exportuje svih 7 funkcija.
- **Funkcionalni smoke (legacy PowerShell tool put):** Nije primjenjivo za R2b — DB
  helperi su internal utility (readDb/writeDb se pozivaju iz mnogih main.cjs tokova:
  plans, confirmations, events, tools execute, thumbnail). Nije "legacy PowerShell
  tool put" koji R2c traži. Pokretanje app-a i pozivanje bilo koje funkcije koja čita
  DB (npr. plans list) bi bio stvarni smoke, ali to traži Electron runtime + ljudsku
  interakciju. Brief R2b acceptance traži samo build + load-smoke (oba urađena).
  R2c će tražiti funkcionalni smoke (legacy image/thumbnail put) — to je eksplicitno
  navedeno u R2c koraku 5.

## Commit

**Nije komitovan** — čeka Claude pregled (brief R2 pravilo 4: "kad završiš R2b, javi
(Claude verifikuje) pa onda R2c").

## Potrebna korisnička potvrda (Claude R2b protokol)

1. `npm run build` sam → čisto (ja potvrdio: čisto).
2. Load-smoke: `node -e "require('./electron/core/legacyDb.cjs')"` → čisto (ja potvrdio).
3. **Diff pregled:** uporediti tijela 7 funkcija sa `git show HEAD:electron/main.cjs`
   (linije 93–166) vs `electron/core/legacyDb.cjs` (linije 17–90) — bajt-identično.
   Ja uradio verbatim diff (`/tmp/r2b-main.cjs.orig` = snimka pre-R2b = `git show HEAD`),
   nula razlika u tijelima.
4. `gitnexus detect_changes` — low risk, 0 affected processes (vidi gore).
5. Ako čisto → zeleno za R2c (web/image/thumbnail poslovna logika → `electron/tools_legacy/`).
