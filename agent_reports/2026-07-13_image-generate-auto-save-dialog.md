# Agent report — image_generate sad automatski otvara "Sačuvaj kao..." dijalog

**Datum:** 2026-07-13
**Scope:** `src/lib/realtime.ts`, `electron/ipc_handlers/thumbnails.cjs`.

**Povod:** Korisnik je ispravio prethodni pristup (`agent_reports/2026-07-13_thumbnail-save-as-export.md`,
ručno "Sačuvaj kao..." dugme) — pogrešan smjer, jer je htio da se dijalog za
izbor lokacije otvori AUTOMATSKI čim generisanje slike završi, ne da čeka
ručni klik. Razjašnjeno kroz pitanja: `image_generate` (obična slika, ne
thumbnail board) radi ispravno i generiše, ali uvijek snima na predefinisano
mjesto bez pitanja korisnika.

## GitNexus impact

`detect_changes` prije commita — risk "medium" (dodirnuto `executeFunctionCalls`,
centralna tool-calling petlja za glas i tekst). Ručno provjeren pun diff —
čisto aditivan, jedan novi `if` blok striktno ograničen na
`name === "image_generate"`, ništa drugo u toj funkciji nije dirano.

## Šta je urađeno

- `src/lib/realtime.ts`'s `executeFunctionCalls()` — odmah nakon što
  `result.artifact` prikaže generisanu sliku (postojeća linija), novi blok:
  ako je tool bio `image_generate` i uspio, poziva
  `window.ricky.saveThumbnailAs({path: result.path, ...})` — **fire-and-forget**,
  ne čeka korisnikov izbor prije nego što glasovni/tekstualni razgovor
  nastavi (Riki je već "završio" iz perspektive razgovora; dijalog je
  asinhrona nuspojava).
- Otkriveno usput: `image_generate` je **Python-registrovan tool** (FAZA 16,
  `python_backend/app/tools/images/generate.py`), izvršava se na backend
  procesu koji NEMA pristup Windows GUI dijalozima — zato dijalog ne može
  biti dio same tool-execution logike (Python), mora biti okinut sa
  Electron/renderer strane NAKON što se tool poziv vrati (postojeći
  `saveThumbnailAs` IPC, izgrađen ranije danas za thumbnail export, ponovo
  iskorišten bez izmjene).
- Provjereno da je Python-ov `image_generate` save-path (`settings.data_dir /
  "images"`) fizički ISTI folder kao Electron-ov `dataDir` u dev i packaged
  modu (`electron/services/pythonProcess.cjs:112-115`, `RICKY_DATA_DIR` se
  eksplicitno postavlja da dijeli isti folder) — postojeća `handleThumbnailSaveAs`
  allowlist provjera (mora biti unutar `dataDir`) je već ispravno pokrivala
  ovu putanju bez izmjene.
- Ažuriran dokumentacioni komentar u `thumbnails.cjs` — `handleThumbnailSaveAs`
  je sad generički "export app-generated image" handler, ne samo za
  thumbnail board (uprkos imenu — nije preimenovano da se izbjegne nepotreban
  diff/rizik za već commitovan, radan kod).

## Zašto ovako

- Fire-and-forget umjesto `await` prije nastavka razgovora — voice/text
  konverzacija ne smije da "visi" čekajući da korisnik zatvori native
  dijalog; korisnik već vidi generisanu sliku u artifact panelu odmah, a
  dijalog za izbor lokacije se pojavljuje paralelno.
- Ako korisnik otkaže dijalog, interna kopija ostaje netaknuta (ništa se ne
  gubi) — dijalog je DODATNA prilika za izvoz, ne jedini način da slika
  preživi.
- Nisam mijenjao thumbnail board (`thumbnail_generate`/`thumbnail_edit`) —
  korisnikovo pojašnjenje je bilo specifično za `image_generate` ("kažem mu
  da generiše sliku"); board i dalje koristi ranije dodano ručno "Sačuvaj
  kao..." dugme (board je dizajniran kao brojana galerija koja zahtijeva
  internu putanju za rad, drugačiji kontekst).

## Šta nije dirano

- `python_backend/app/tools/images/generate.py` — nula izmjena, `result.path`
  je već bio dio odgovora, samo prethodno nekorišten na frontend strani za
  ovu svrhu.
- Thumbnail board generate/edit tok — i dalje ručno dugme, ne auto-trigger
  (van obima ovog pojašnjenja).

## Verifikacija

- `npm run typecheck`, `npm run build` — čisto.
- `node --check electron/ipc_handlers/thumbnails.cjs` — čisto.
- `mcp__gitnexus__detect_changes` — risk medium, ručno potvrđen kao čisto
  aditivan, ispravno ograničen diff.
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- Ako Python backend ikad promijeni `image_generate`'s save putanju izvan
  dijeljenog `dataDir`-a (npr. buduća izmjena), `saveThumbnailAs`-ova
  allowlist provjera bi tiho odbila export (baca grešku koju frontend
  guta preko `.catch(() => {})`) — korisnik ne bi dobio dijalog niti
  vidljivu grešku, samo interna kopija ostaje. Prihvatljivo za sada jer je
  putanja provjereno stabilna, ali vrijedi imati na umu.

## Potreban follow-up

Runtime test korisnika: reći/otkucati "generiši sliku [nešto]" i potvrditi
da se native "Sačuvaj kao..." dijalog otvori ODMAH nakon što se slika
prikaže u artifact panelu, bez ikakvog ručnog klika.

## Potrebna korisnička potvrda

Runtime test prije nego se ovo smatra potpuno gotovim.
