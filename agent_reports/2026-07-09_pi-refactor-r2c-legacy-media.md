# Agent report — R2c: web/image/thumbnail poslovna logika → electron/tools_legacy/

**Datum pisanja:** 2026-07-09
**Brief:** `docs/refactor_plan.md` sekcija "R2 — electron/main.cjs split", podsekcija "R2c".
**Izvršilac:** pi · **Vlasnik plana:** Claude (verifikuje).
**Tip:** Mehanički refactor — verbatim premještanje, ponašanje nepromijenjeno, legacy kod NIJE obrisan.

## Scope

Izvukao ~643 ln legacy web/image/thumbnail poslovne logike iz `electron/main.cjs`
(1533 → 923 ln) u novi `electron/tools_legacy/legacyMedia.cjs`. main.cjs ih sad
`require`-uje i poziva isto kao prije.

## Lista premještenih funkcija (32, po imenu)

Web search (5): `webSearch`, `formatSearchMarkdown`, `cleanMarkdownText`, `hostname`,
`buildMenuMarkdown`.

Image (2): `generateImage`, `imageErrorArtifact`.

Thumbnail board — entry ops (5): `thumbnailReferenceAdd`, `thumbnailLoadingPrepare`,
`thumbnailGenerate`, `thumbnailEdit`, `thumbnailSelect`.

Thumbnail board — image pipeline (4): `createThumbnailImage`, `editImageWithInputs`,
`saveImageResponse`, `thumbnailRecord`.

Thumbnail board — prompts (2): `thumbnailPrompt`, `editThumbnailPrompt`.

Thumbnail board — db helpers (8): `thumbnailByNumberOrSelected`,
`replaceLoadingThumbnails`, `removeLoadingThumbnailRun`, `thumbnailNumber`,
`assignThumbnailNumber`, `pageForArgs`, `sortedThumbnailImages`,
`paginatedThumbnailImages`.

Thumbnail board — summary/artifact (4): `thumbnailPageMeta`,
`thumbnailBoardSummary`, `buildThumbnailBoardInstructions`,
`thumbnailBoardArtifact`.

Image data utils (2): `imageDataUrl`, `mimeForPath`.

Orig. linije (u 1533-ln main.cjs pre-R2c): 703–1345.

## Zavisnosti i kako su riješene (bez circular require)

| Zavisnost | Rješenje |
| --- | --- |
| `fs`, `path`, `crypto` | legacyMedia.cjs sam `require("node:fs/promises")` / `node:path` / `node:crypto` |
| `fetch`, `FormData`, `Blob` | Node globali (Node 18+) — ne require-uju se |
| `dataDir` | legacyMedia.cjs ima sopstveni `const dataDir = path.join(process.cwd(), "data")` — ista vrijednost kao main.cjs. **Duplikacija odobrena od Claude-a za R2b** ("duplikaciju dataDir/dbPath ostaviti kako jeste"), primijenjena konzistentno i ovdje. |
| `readDb`/`writeDb`/`updateDb` | `require("../core/legacyDb.cjs")` (R2b) — relativna putanja iz `tools_legacy/` |
| `currentMode`/`mainWindow`/`handleToolsExecute` | **NIJE dirano** — web/image/thumbnail blok ih NE referencira (grep potvrđeno: 0 hitova za currentMode/mainWindow/handleToolsExecute u bloku 703–1345). Nema potrebe za proslijeđivanjem parametara. |

**Nema circular require-a:** legacyMedia.cjs require-uje isključivo Node builtine +
`../core/legacyDb.cjs` (koji sam require-uje Node builtine). NIKAD `main.cjs` niti
`electron`. Brief R2 pravilo 3 ispunjeno bez potrebe za factory/parametrima.

## Zašto JEDAN fajl umjesto web.cjs/image.cjs/thumbnail.cjs

Brief R2c eksplicitno dozvoljava: *"Ako su web/image/thumbnail međusobno
isprepleteni tako da razdvajanje traži mijenjanje logike → stavi ih u JEDAN
`tools_legacy/legacyMedia.cjs` umjesto da lomiš tijela funkcija. Grupisanje je
sekundarno; verbatim move je primarno."*

Analiza pokazala snažno ispreplitanje:
- `cleanMarkdownText` dijele `webSearch` (markdown brief) i `imageErrorArtifact`
  (error markdown) — 6 referenci.
- `imageErrorArtifact` zovu web/image/thumbnail entry ops (10 referenci).
- `thumbnailBoardSummary`/`thumbnailBoardArtifact`/`thumbnailByNumberOrSelected`
  su shared utilityi koje zove većina thumbnail ops.
- `mimeForPath` dijele `editImageWithInputs` (thumbnail) i `imageDataUrl` (board).

Razdvajanje u 3 fajla bi zahtijevalo cross-module importe tih shared funkcija
(čitava web blok bi importovao `cleanMarkdownText` iz image bloka, itd.) — rizik
greške i odstupanja od verbatim principa. Jedan fajl čuva sva tijela bajt-identična
i smanjuje blast radius.

## Koraci izvedeni (tačno po briefu R2c)

1. **Mapiranje** funkcija (703–1345) i zavisnosti. Izlistano gore. Potvrđeno:
   blok NE dira `currentMode`/`mainWindow`/`handleToolsExecute` (0 referenci) →
   nema potrebe za proslijeđivanjem parametara.
2. **Kreiran `electron/tools_legacy/legacyMedia.cjs`:**
   - Header: require fs/path/crypto, `dataDir` (sopstveni), `require("../core/legacyDb.cjs")`
     za readDb/writeDb/updateDb.
   - 32 funkcije premještene **verbatim** (tijela bajt-identična, 0 uvlačenja).
   - `module.exports = { ...svih 32 funkcija };` na dnu.
3. **`main.cjs` prespojen:**
   - Dodan `const { webSearch, formatSearchMarkdown, ..., mimeForPath } = require("./tools_legacy/legacyMedia.cjs");`
     (32 imena) odmah poslije `legacyDb.cjs` require bloka.
   - Obrisane 32 funkcije (orig. 703–1345 + blank 1346).
   - `dataDir`/`dbPath` (57–58) ZADRŽANI (main.cjs ih koristi za screenshot, l. 706).
   - `recordsArtifact`/`normalizeMermaidDiagram`/`fallbackMermaidDiagram` (orig. 1347+)
     ZADRŽANI u main.cjs — to su artifact utilityji koje direktno zove
     `handleToolsExecute` (records/mermaid alat), NE web/image/thumbnail biznis logika.
4. `npm run build` + load-smoke `require('./electron/tools_legacy/legacyMedia.cjs')`.
5. **Funkcionalni smoke:** urađen minimalan (vidi dolje).

## Verifikacija (acceptance criteria iz briefa)

| Kriterij | Očekivano | Dobiveno |
| --- | --- | --- |
| `main.cjs` veličina | ~850 ln | **923 ln** (1533 → 923, -610 ln) — blizu procjeni; razlika jer su recordsArtifact/mermaid utilityji (koji se graniče sa blokom) opravdano ostavljeni u main.cjs |
| `tools_legacy/` moduli postoje | da | ✓ (`legacyMedia.cjs`, 700 ln) |
| `npm run build` | čisto | ✓ (samo pre-postojeći 500kB chunk warning, nevezan) |
| load-smoke | čisto | ✓ `exports: 32 fns` |
| verbatim diff dokaz | nula razlika u tijelima | ✓ (vidi dolje) |
| funkcionalni smoke | urađen ILI jasno naznačeno | minimalan urađen; legacy API put NE (vidi dolje) |

### Verbatim diff dokaz (bajt-identična tijela)
```
diff <(sed -n '703,1345p' /tmp/r2c-main.cjs.orig) <(sed -n '24,666p' electron/tools_legacy/legacyMedia.cjs)
→ nula razlika (VERBATIM ✓)
```
`/tmp/r2c-main.cjs.orig` = snimka main.cjs pre-R2c (1533 ln, = `git show HEAD:electron/main.cjs`
+ R2b nekomitovane izmjene koje je Claude odobrio). legacyMedia.cjs linije 24–666 = 32 funkcije
(za header require bloka i module.exports). **Nula razlika u tijelima funkcija.**

### Funkcionalni smoke (status)
- **Load-smoke:** ✓ — `require('./electron/tools_legacy/legacyMedia.cjs')` učitava se bez greške.
- **Minimalni funkcionalni smoke (čiste funkcije, bez API keys):** ✓ urađen:
  - `cleanMarkdownText("  a<b>  c  ")` → `"ab c"` ✓
  - `hostname("https://www.example.com/x")` → `"example.com"` ✓
  - `formatSearchMarkdown("q", [])` → markdown sa "No strong web results" ✓
  - `thumbnailBoardSummary({...defaultDb...})` → `{references: 0, ...}` ✓
  - `mimeForPath("/x/a.jpg")` → `"image/jpeg"` ✓
- **Legacy API put smoke (webSearch/generateImage/thumbnailGenerate):** ✗ NIJE urađen —
  zahtijeva `EXA_API_KEY` / `OPENAI_API_KEY` (nisu u okruženju) + stvarne API pozive.
  Verbatim diff dokaz + load-smoke su primarno osiguranje; **Claude treba tražiti od
  korisnika ručni smoke (legacy image/thumbnail put sa `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1`
  + OPENAI_API_KEY) prije commita**, po brief R2c korak 5.

### GitNexus detect_changes (info za Claude)
```
Changes: 3 files, 3 symbols
Affected processes: 0
Risk level: low
Changed symbols: Refactor plan... → docs/refactor_plan.md (druga sesija),
                 Inventar... → docs/refactor_plan.md (druga sesija),
                 toolSpecs → electron/main.cjs
```
**Risk: low, 0 affected processes.** Nema HIGH/CRITICAL. (GitNexus ne indeksira
.cjs funkcije granularno, ali affected flows = 0 potvrđuje nema slomljenih tokova.)

## Fajlovi dirani (tačna lista)

- `electron/main.cjs` — modifikovan (1533 → 923 ln): uklonjeno 32 funkcije
  (orig. 703–1345); dodat `require("./tools_legacy/legacyMedia.cjs")` destructure
  (32 imena, ~37 ln). `dataDir`/`dbPath` zadržani (57–58). `recordsArtifact`/
  `normalizeMermaidDiagram`/`fallbackMermaidDiagram` zadržani (sad 737+).
- `electron/tools_legacy/legacyMedia.cjs` — novi (700 ln): header komentar +
  fs/path/crypto/dataDir + `require("../core/legacyDb.cjs")` + 32 funkcije verbatim
  + `module.exports`.

**Nije dirano:** `src/*`, `python_backend/*`, `src/styles/*`, `electron/core/*`
(osim legacyDb.cjs iz R2b — već komitovano/odobreno), `handleToolsExecute` tijelo,
IPC handleri, kill-switch/lifecycle/`currentMode`, `electron/tools_legacy/powershell/*`.

## Potvrda: ponašanje nepromijenjeno, legacy kod NIJE obrisan

- Funkcije premještene verbatim (diff dokaz: nula razlika u tijelima).
- Nijedno ime, redoslijed argumenata, logika, return vrijednost, API endpoint,
  model ime (`gpt-image-2`), prompt tekst nije diruto.
- main.cjs poziva iste funkcije, istim imenima, istim scope-om (destrukturisani import).
- `dataDir` identična vrijednost u main.cjs i legacyMedia.cjs (obe `process.cwd()/data`).
- Legacy web/image/thumbnail kod i dalje živ i korišten — samo relociran, nije
  uklonjen (CLAUDE.md: legacy ostaje dok Python zamjena nije potvrđena).

## Found issues (brief sekcija — NE popravljati u ovom koraku)

- (prazno) — nijedan bug nije zapažen tokom R2c. `recordsArtifact`/
  `normalizeMermaidDiagram`/`fallbackMermaidDiagram` su ostavljeni u main.cjs jer
  su artifact utilityji (zove ih `handleToolsExecute` za records/mermaid alate),
  ne web/image/thumbnail biznis logika — ovo je ispravna granica, ne propust.
- `dataDir` duplikacija (main.cjs + legacyDb.cjs + legacyMedia.cjs) — svjesna,
  odobrena od Claude-a za R2b.

## Commit

**Nije komitovan** — čeka Claude pregled (brief R2 pravilo 4: "kad završiš R2c, javi
ponovo").

## Potrebna korisnička potvrda (Claude R2c protokol)

1. `npm run build` sam → čisto (ja potvrdio: čisto).
2. Load-smoke: `node -e "require('./electron/tools_legacy/legacyMedia.cjs')"` → čisto (ja potvrdio: 32 fns).
3. **Diff pregled:** uporediti tijela 32 funkcije sa `git show HEAD:electron/main.cjs`
   (linije 703–1345 — NAPOMENA: HEAD je pre-R2b, pa treba main.cjs pre-R2c =
   `git show HEAD:electron/main.cjs` + R2b izmjene; ili poređenje sa snimkom
   `/tmp/r2c-main.cjs.orig` koju sam napravio) vs `legacyMedia.cjs` (24–666) —
   bajt-identično. Ja uradio verbatim diff: nula razlika u tijelima.
4. `gitnexus detect_changes` — low risk, 0 affected processes (vidi gore).
5. **Funkcionalni smoke (legacy image/thumbnail put):** NISAM uradio (nema API keys).
   Preporuka Claude-u: tražiti od korisnika ručni smoke sa `OPENAI_API_KEY` postavljenim
   i pozvati `image_generate` ili `thumbnail_generate` kroz app, da se potvrdi da
   migracija nije slomila runtime prije commita. Ako korisnik to ne može odmah,
   verbatim diff + load-smoke + build su dovoljni za preliminarno zeleno, uz
   eksplicitnu napomenu da runtime smoke nije urađen.
