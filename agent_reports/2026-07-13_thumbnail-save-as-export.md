# Agent report — "Sačuvaj kao..." za generisane thumbnail slike

**Datum:** 2026-07-13
**Scope:** `electron/ipc_handlers/thumbnails.cjs`, `electron/main.cjs`,
`electron/preload.cjs`, `src/components/ArtifactPanel.tsx`,
`src/vite-env.d.ts`, `src/styles/03-artifacts.css`,
`src/i18n/locales/*.json` (5 fajlova).

**Povod:** Korisnik je prijavio da nakon što Riki generiše thumbnail, slika
se automatski sačuva "negdje" bez mogućnosti izbora lokacije. Provjereno u
kodu: `saveImageResponse()` (`legacyMedia.cjs:486-495`) oduvijek automatski
piše svaku generisanu sliku u aplikacijin interni `data/` folder
(`thumbnail-<timestamp>-<uuid>.png`), bez ikakvog dijaloga — ovo nije
regresija iz S-03 rada, postojeće ponašanje otkad thumbnail feature postoji.
Korisnik je potvrdio da želi "Sačuvaj kao..." dugme.

## GitNexus impact

`detect_changes` prije commita — risk "high", ručno potvrđeno kao line-shift
artefakt: `git diff` na `thumbnails.cjs` i `ArtifactPanel.tsx` potvrđuje da
`handleThumbnailAddReference`/`handleAddReference` tijela nisu dotaknuta —
samo je novi kod (handleThumbnailSaveAs, handleSaveAs) umetnut pored njih,
pomjerajući linije. Indeks osvježen (`npx gitnexus analyze`) nakon izmjena.

## Šta je urađeno

- `electron/ipc_handlers/thumbnails.cjs`: novi `handleThumbnailSaveAs(_event,
  {path, suggestedName})` — otvara `dialog.showSaveDialog` (native Windows
  "Save As", PNG filter), pa `fs.copyFile(source, dest)`. **Source path
  validacija**: mora biti unutar aplikacijinog `dataDir` (`data/` folder) —
  odbija bilo koju putanju van toga, PRIJE nego što dialog uopšte otvori.
  Ovo je defense-in-depth: renderer šalje `path` string preko IPC-a, i bez
  ove provjere, kompromitovan renderer (npr. XSS kroz artifact render) bi
  teoretski mogao pretvoriti ovo u "kopiraj proizvoljan lokalni fajl na
  destinaciju koju korisnik izabere" — provjera to svodi na "samo
  aplikacijine vlastite thumbnail slike".
- `main.cjs`/`preload.cjs`: novi `"thumbnails:save-as"` IPC kanal, isti
  allowlist obrazac kao ostali kanali.
- `ArtifactPanel.tsx` (`ThumbnailBoard`): novo "Sačuvaj kao..." dugme u
  fullscreen/selected prikazu pojedinačnog thumbnail-a (ne u grid prikazu —
  namjerno, manje zatrpavanja UI-ja za prvi prolaz). Poziva
  `window.ricky.saveThumbnailAs({path, suggestedName})`, `suggestedName`
  izveden iz thumbnail broja (`thumbnail-<broj>.png`).
- `ThumbnailBoardData.images[]` TS tip proširen sa `path?: string` — Electron
  je taj podatak već slao u board JSON-u (`thumbnailBoardArtifact` spread-uje
  cijeli stored image record), samo nije bio deklarisan u tipu.

## Zašto ovako

- Dugme samo u selected/fullscreen prikazu, ne po-kartici u grid-u — grid
  kartice su male (3x3 layout), dodavanje dugmeta na svaku bi zatrpalo UI za
  prvi prolaz na ovom feature-u. Korisnik klikne thumbnail da ga otvori
  fullscreen, pa "Sačuvaj kao..." tamo.
- Path allowlist na `dataDir` umjesto potpunog povjerenja u renderer-ov
  string — ista disciplina kao S-03 rad ranije danas (path_sandbox
  validacija za user-supplied putanje), primijenjena ovdje na Electron strani
  pošto Python nije uključen u ovaj tok.

## Šta nije dirano

- `saveImageResponse()`/interno auto-čuvanje u `data/` folder — ostaje
  netaknuto (i dalje se dešava, "Sačuvaj kao..." pravi DODATNU kopiju, ne
  zamjenjuje interno čuvanje koje board galerija zahtijeva za rad).
- Grid prikaz (per-card save dugme) — moguće buduće proširenje, nije
  traženo u ovom prolazu.

## Verifikacija

- `node --check` na sva 3 dotaknuta `.cjs` fajla — čisto.
- `npm run typecheck`, `npm run build` — čisto.
- `python -m pytest -q` — 273 passed (sanity provjera, Python nije diran).
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- `fs.copyFile` ne provjerava da li `result.filePath` (korisnikov izbor u
  save dijalogu) postoji već — Electron-ov native save dialog sam pita "Do
  you want to replace it?" ako fajl postoji, pa je ovo pokriveno na OS nivou.

## Potreban follow-up

Runtime test korisnika: generisati thumbnail, otvoriti ga fullscreen
klikom, kliknuti "Sačuvaj kao...", potvrditi da native dijalog radi i da se
kopija stvarno pojavi na izabranoj lokaciji.

## Potrebna korisnička potvrda

Runtime test prije nego se ovo smatra potpuno gotovim.
