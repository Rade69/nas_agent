# Agent report — S-03: native file picker + opaque ID za thumbnail referentne slike

**Datum:** 2026-07-13
**Scope:** Python (`app/core/path_sandbox.py`, `app/storage/db.py`,
`app/storage/repositories/thumbnail_reference_repo.py` novo,
`app/services/thumbnail_reference_service.py` novo, `app/schemas/thumbnail.py`
novo, `app/api/thumbnails.py` novo, `app/main.py`,
`tests/test_thumbnail_references.py` novo); Electron (`core/realtimeToolSpecs.cjs`,
`main.cjs`, `services/pythonClient.cjs`, `ipc_handlers/thumbnails.cjs` novo,
`tools_legacy/legacyMedia.cjs`, `preload.cjs`); Frontend
(`src/components/ArtifactPanel.tsx`, `src/App.tsx`, `src/vite-env.d.ts`,
`src/styles/03-artifacts.css`, `src/i18n/locales/*.json`).

**Povod:** Treći i posljednji CRITICAL/P0 nalaz iz
`docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md` (Codex-ov audit, S-01/S-02
popravljeni ranije danas, S-04 popravljen ranije danas). Korisnik je izabrao
punu audit preporuku (native file picker + opaque ID) nakon što sam u plan
mode-u predložio i objasnio zašto puna migracija cijele thumbnail
generate/edit/board logike u Python NE ulazi u obim (visok rizik za
opsežan, već fino podešen sistem — vidi odobreni plan,
`C:\Users\38765\.claude\plans\eager-exploring-hejlsberg.md`).

## GitNexus impact

Prije izmjene: `mcp__gitnexus__impact` na `thumbnailReferenceAdd`,
`thumbnailGenerate`, `thumbnailEdit` — sva tri LOW, jedini pozivalac
`handleToolsExecute` (main.cjs dispatch switch), kako se i očekivalo.

Prije commita: `detect_changes` je prvo prijavio risk "critical" sa zbunjujućim
nazivima procesa (`ThumbnailReferenceAdd → ...`) jer indeks nije bio osvježen
nakon preimenovanja `thumbnailReferenceAdd` → `commitThumbnailReference`.
Pokrenuo `npx gitnexus analyze` da osvježim indeks, ponovio `detect_changes`
— i dalje "critical", ali sad sa tačnim imenima. Ručno provjereno da je ovo
opravdano OBIMOM (nova bezbjednosna granica kroz 3 sloja — Python/Electron/
React, ~15 novih/izmijenjenih simbola koji se međusobno pozivaju), ne
stvarnim problemom: `git diff` na `electron/main.cjs` potvrđuje da je jedina
izmjena u `handleToolsExecute` uklanjanje jedne dispatch grane (3 linije) +
komentar — "affected" flert na nepovezane flow-ove (`HandleToolsExecute →
Connect` itd.) je posljedica toga što diff dodiruje istu veliku dispatch
funkciju koja rutira i mnoge druge, nepromijenjene tool pozive.

## Šta je urađeno

Arhitektura (detaljno u odobrenom planu):

1. Korisnik klikne "+ Dodaj referentnu sliku" u Thumbnail Board UI-ju.
2. Electron otvara native OS file picker (`dialog.showOpenDialog`,
   filtrirano na image ekstenzije) — jedini način da referenca uopšte nastane.
3. Electron šalje izabranu putanju Python-u: `POST /thumbnail-references`.
4. Python validira (`app/core/path_sandbox.py` — prvi stvarni pozivalac,
   ranije "priprema bez pozivaoca"): canonical path unutar `Path.home()`,
   dozvoljena slikovna ekstenzija (novi `ensure_image_extension_allowed`,
   allowlist — suprotan smjer od postojećeg execution-blocklist-a), max 8 MB.
   Perzistira u novu SQLite tabelu `thumbnail_references` i vraća
   `{id (opaque, npr. ref_xxx), label, preview_data_url}` — **nikad
   canonical_path** u ovom odgovoru.
5. Electron upisuje `{id, label, previewDataUrl, createdAt}` u legacy JSON
   `db.thumbnailBoard.references` — bez `path` polja.
6. `thumbnailGenerate`/`thumbnailEdit` sad rade `resolveReferencePaths()` —
   za svaku referencu pozivaju `GET /thumbnail-references/{id}/resolve`
   (Python re-validira da fajl još postoji i da je unutar allowed roots —
   TOCTOU zaštita, ne samo provjera pri registraciji), i tek onda čitaju
   fajl. Neuspješna rezolucija (fajl obrisan/pomjeren) se tiho preskoči, ne
   ruši cijeli generate/edit poziv.

`thumbnail_reference_add` je potpuno uklonjen iz model-facing tool liste
(`realtimeToolSpecs.cjs`) — isti obrazac kao S-01 `set_mode`. Model nikad
više ne može registrovati referencu; help meni/tool opisi ažurirani da to
odražavaju.

**Namjerno van obima** (obrazloženo u odobrenom planu, ponovljeno ovdje radi
transparentnosti):
- `thumbnailGenerate`/`thumbnailEdit`/`thumbnailSelect`/`thumbnailLoadingPrepare`
  ostaju u Electron-u nepromijenjeni osim retke koja gradi `referencePaths` —
  OpenAI pozivi, loading placeholderi, paginacija, numeracija, parent/child
  edit lanci netaknuti.
- Nema druge confirmation dijaloga pri generate/edit vremenu — native file
  picker klik JESTE eksplicitna saglasnost (dialog title eksplicitno kaže da
  će slika biti poslana OpenAI-ju).
- Action-log `sent_to_cloud` receipt nije dodat — `thumbnail_generate`/`edit`
  ne prolaze kroz Python `ToolExecutor` uopšte (nisu u
  `PHASE11_DELEGATED_TOOLS`), pa nemaju pristup postojećem action logu; to je
  širi preduslov (retrofit za SVE legacy alate), zaseban budući nalaz.

## Zašto ovako

- Preview bez Pillow-a — `base64.b64encode()` sirovih bajtova umjesto
  server-side resize-a. Pillow JE dostupan u ovom dev okruženju (koristi ga
  `screenshot.py` lazy-importom) ali NIJE deklarisan u `pyproject.toml`
  dependencies — uvođenje formalne zavisnosti samo za ovaj preview nije
  vrijedno rasprave/rizika kad je direktan base64 sasvim dovoljan (8 MB cap
  drži response razuman).
- `resolve()` re-validira SVAKI put (ne samo cache-uje `canonical_path` iz
  baze) — brani od fajla premještenog/obrisanog/simlink-ovanog nakon
  registracije, ne samo u trenutku registracije.

## Šta nije dirano

- `thumbnailGenerate`/`thumbnailEdit`/`thumbnailSelect`/`thumbnailLoadingPrepare`
  business logika (samo referencePaths building izmijenjen).
- `docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md` — nije ažuriran statusom
  za S-03 u ovom fajlu (nasuprot S-01/S-02/S-04) jer runtime test korisnika
  nije još urađen — vidi Potreban follow-up.

## Verifikacija

- `mcp__gitnexus__impact` prije izmjene (LOW x3) i `detect_changes` prije
  commita (critical, ručno potvrđen kao obim-ne-problem, indeks osvježen).
- `node --check` na svih 6 dotaknutih `.cjs` fajlova — čisto.
- `python -m pytest -q` — **273 passed** (262 prije + 11 novih u
  `test_thumbnail_references.py`: path traversal odbijen, non-image ekstenzija
  odbijena, prevelik fajl odbijen, nepostojeći fajl odbijen, uspješan add bez
  curenja sirove putanje u odgovoru, resolve nepoznatog ID-a, resolve
  registrovane reference, resolve obrisanog fajla, API round-trip, API
  odbija path traversal, API 404 na nepoznat ID).
- `npm run typecheck`, `npm run build` — čisto.
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- **Migracija postojećih referenci:** korisnici koji su prije ovog fix-a već
  registrovali reference (stari format `{id: uuid, path, label, createdAt}`)
  imaju `id` koji NIKAD nije registrovan u novoj Python `thumbnail_references`
  tabeli. `resolveReferencePaths()` će za njih dobiti 404 od Python-a i tiho
  ih preskočiti (graceful degradation, ne crash) — ali to znači da će
  postojeće reference efektivno prestati raditi nakon ovog fix-a dok ih
  korisnik ponovo ne doda kroz novi file picker. Nije automatski migrirano
  (stare putanje nisu bile ni validirane, pa ih ne bih trebao "tiho"
  prihvatiti u novi sistem bez iste validacije koju sad zahtijevam od svih).
- `MAX_REFERENCE_IMAGE_BYTES = 8 MB` je konzervativan (manji od
  `path_sandbox`-ovog opšteg 25 MB default-a) — namjerno, jer se cijeli fajl
  base64-encode-uje u API response za preview.
- `Path.home()` kao allowed root je širok (cijeli korisnički profil) — brani
  od path traversal-a/sistemskih foldera, ali ne od "korisnik ima privatan
  fajl u Desktop folderu" scenarija koji audit takođe pominje kao rizik;
  native file picker (korisnik SAM bira fajl mišem) je primarna odbrana za
  taj slučaj, sandbox je sekundarna.

## Potreban follow-up

Runtime test korisnika: kliknuti "+ Dodaj referentnu sliku", izabrati
fotografiju, potvrditi da se preview prikaže u board-u, zatim reći "generiši
thumbnail" glasom i potvrditi da generisanje i dalje radi sa novom
referencom. Nakon uspješnog testa, ažurirati status S-03 na ✅ u
`docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md` (isti obrazac kao
S-01/S-02/S-04).

## Potrebna korisnička potvrda

Runtime test (gore) prije nego se S-03 smatra potpuno zatvorenim.
