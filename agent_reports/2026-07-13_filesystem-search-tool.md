# Agent report — filesystem_search tool (rješava beskonačnu petlju potvrda pri traženju foldera)

**Datum:** 2026-07-13
**Scope:** `python_backend/app/tools/system/filesystem_search.py` (novo),
`python_backend/app/agent/tool_catalog/phase11.py`, `python_backend/app/main.py`,
`python_backend/tests/test_filesystem_search.py` (novo), `electron/main.cjs`,
`electron/core/realtimeToolSpecs.cjs`, `electron/ipc_handlers/realtime.cjs`.

**Povod:** Korisnik je prijavio da agent upada u beskonačnu petlju traženja
odobrenja kad se od njega traži da pronađe folder (npr. gdje su thumbnailovi),
i da pretraga foldera mora raditi besprijekorno za bilo koji folder na
sistemu.

## Istraga (Explore agent, prije izmjene)

Nijedan tool za pretragu fajl sistema nije postojao. Model je za "pronađi
folder" imao samo `computer_open_app` (otvara Explorer bez ciljanja putanje)
i slijepo `computer_click`/`computer_type_text` navigiranje — oba su
`risk="high"`, `requires_confirmation=True` (`phase13.py`). Svaki takav
pokušaj triggeruje NOVI `CONFIRMATION_REQUIRED` (`permission_engine.py`,
confirmation je single-use preko `confirmation_service.consume()`), a model
nema način da u JEDNOM potezu locira folder — svaki sljedeći nagađani klik
traži svoju potvrdu. To je stvarni uzrok "beskonačne petlje" koju je
korisnik vidio: nije bug u confirmation mehanizmu, nego potpuno odsustvo
alata koji bi ovaj zahtjev mogao riješiti u jednom pozivu.

Usput uočen i poseban, nezavisan gap (NIJE popravljen ovim PR-om, dokumentovan
kao follow-up niže): kad se confirmation ipak odobri, retry put
(`App.tsx:handleApproveConfirmation`) izvršava alat direktno preko IPC-a ali
nikad ne javlja rezultat nazad u glasovnu Realtime sesiju (nema
`function_call_output` za taj `call_id`) — model iz glasovne sesije nikad ne
sazna da li je pokušaj uspio, pa može ponovo pokušati. Ovo bi i dalje moglo
uzrokovati petlje za DRUGE confirmation-gated alate (ne samo pretragu
foldera), ali je van obima ovog fix-a jer zahtijeva širu izmjenu generičkog
confirmation-retry mehanizma koji dijele svi alati.

## GitNexus impact

`detect_changes` — risk HIGH (kumulativno sa još necommitovanim `set_mode`
radom iz ranije ove sesije; `handleToolsExecute` i `toolSpecs` su ponovo
dodirnuti). Ručno provjeren `git diff --stat`: sve izmjene su čisto aditivne
(nova registracija alata + novi Set unos), ništa postojeće nije izmijenjeno
van namjeravanog opsega.

## Šta je urađeno

Nov Python tool `filesystem_search(query, type?)` — read-only, bez
confirmation-a (vraća samo imena/putanje foldera/fajlova, nikad sadržaj):

- **Redoslijed pretrage** (`_search_roots()`): prvo aplikacijin vlastiti
  `data_dir` (tu žive thumbnailovi/slike — direktan odgovor na konkretan
  trigger ovog izvještaja), zatim `Path.home()` (Desktop/Documents/Downloads/
  Pictures/AppData), pa tek onda fallback na sve fiksne lokalne diskove
  (`C:\`, `D:\`, ...) — pravi "bilo koji folder na sistemu" zahtjev iz
  korisnikove poruke, ali prioritizovan tako da najčešći upiti pogode odmah
  u prva dva (mala, brza) korijena umjesto da čekaju pun sken diska.
- **Granice** (da glasovni potez nikad ne "visi"): `MAX_RESULTS=40`,
  `MAX_SECONDS=10.0` wall-clock budžet dijeljen preko svih korijena; kad se
  dostigne, pretraga se prekida i vraća `truncated: true` sa dotadašnjim
  rezultatima umjesto da baci grešku.
- **Preskočeni direktoriji** radi brzine/šuma: `$Recycle.Bin`, `System Volume
  Information`, `WinSxS`, `Installer`, `node_modules`, `.git`.
- Case-insensitive substring match na imenu; `type: "folder" | "file" | "any"`
  (default `"any"` — vidi "Revizija 2" niže).
- Registrovan u `phase11.py` sa `risk="low"`, `requires_confirmation=False`,
  `requires_computer_mode=False`, `reads_external_content=True` (imena
  foldera/fajlova idu modelu/cloud-u, isti tretman kao `web_search`/
  `ui_inspect`) — dostupan bilo kad, ne samo u Computer Mode-u, jer ne
  kontroliše ništa, samo čita imena.
- Electron: dodat u `PHASE11_DELEGATED_TOOLS` (main.cjs) i u
  `realtimeToolSpecs.cjs` (model-facing spec) — isti obrazac kao ostali FAZA
  11/16 alati.
- System prompt (`realtime.cjs`'s `buildRickyInstructions`) — eksplicitna
  instrukcija: pozovi `filesystem_search` za "pronađi/gdje je folder/fajl",
  nikad ne pokušavaj slijepim klikanjem kroz Explorer.

## Revizija 2 (isti dan) — "agent ne može ništa pronaći"

Korisnik je nakon prve verzije prijavio da alat i dalje ne nalazi ništa, i
predložio da Python sigurno ima biblioteke koje bi bolje riješile problem.
Istražena su DVA stvarna, nezavisna bug-a, oba potvrđena ručnim testom protiv
pravog fajl sistema (ne samo pytest fixtures):

1. **Algoritam (DFS umjesto BFS):** originalni `os.walk` po korijenu je
   dubinski prvi (depth-first) — kad se prvi obiđe `Path.home()`, `os.walk`
   ulazi u `AppData` (abecedno prije `Desktop`/`Documents`) i može potrošiti
   CIJEL vremenski budžet duboko unutar te jedne grane prije nego ikad
   dosegne plitak folder koji korisnik traži. Isprobana je i prava Windows
   Search indeksirana pretraga (`ADODB`/`Search.CollatorDataSource`, tačno
   ono na šta je korisnik ciljao pitanjem o bibliotekama) — COM provider nije
   registrovan na ovoj mašini (čest 32/64-bit registracioni gap), pa nije
   pouzdana osnova. Umjesto toga, algoritam je promijenjen na **BFS preko SVIH
   korijena odjednom** (jedan red čekanja seedovan sa `data_dir` + `home` +
   svi fiksni diskovi) — plitki pogoci bilo gdje se nalaze prije nego
   pretraga ikad ode duboko u BILO KOJU granu, bez obzira na abecedni
   redoslijed ili veličinu te grane. Dodan regresioni test
   (`test_filesystem_search_finds_shallow_match_past_deep_decoy`) koji
   dokazuje ovo svojstvo nezavisno od redoslijeda kojim OS vraća stavke
   direktorija.
2. **Pogrešan default tip + jednina/množina:** ručni test protiv PRAVOG
   `data/` foldera ove aplikacije otkrio je da thumbnailovi uopšte NE žive u
   folderu po imenu "thumbnails" — to su labavi fajlovi direktno u `data/`
   (`thumbnail-<id>.png`). Default `type: "folder"` je zato ispravno vraćao
   NIŠTA za tačno onaj zahtjev koji je pokrenuo ovaj alat. Popravljeno: (a)
   default promijenjen na `type: "any"` (foldere I fajlove), (b) dodan
   jednostavan engleski jednina/množina fallback — ako prvi prolaz sa
   punim upitom ne nađe ništa I nije prekinut zbog vremena, ponovo pokušava
   bez završnog "s" (npr. "thumbnails" → "thumbnail"). Retry se namjerno NE
   pokreće ako je prvi prolaz istekao (izbjegava udvostručavanje najgoreg
   slučaja latencije za genuinski "ne postoji" upit).

Ručni test protiv stvarnog fajl sistema (van pytest-a, direktno pozivanje
`_bfs_search`): pun sken `data_dir` + `home` + `C:\` (bez skip liste) trajao
je **8.58s** i pronašao samo 1 (irelevantan) pogodak sa `type="folder"` — sa
`type="any"` i upitom "thumbnail" (jednina), stvarni thumbnail `.png` fajlovi
su pronađeni odmah, **prvi u listi rezultata**, za 4.63s.

`timeout_ms` u `phase11.py` registraciji podignut sa 15000 na 20000 da
outer watchdog ne prekine legitiman drugi (retry) prolaz.

## Zašto ovako

- Prioritizovan redoslijed korijena (data_dir → home → drives) umjesto
  ravnopravnog sken svih odjednom — brzina za tipičan slučaj ("gdje su
  thumbnailovi" pogađa PRVI korijen skoro trenutno) bez žrtvovanja
  korisnikovog eksplicitnog zahtjeva za pravim sistem-širokim pokrivanjem
  kao fallback-om.
- `requires_computer_mode=False` — pretraga imena foldera ne "kontroliše"
  ništa (za razliku od `screen_snapshot`/`ui_inspect` koji čitaju živi
  ekran/prozor), pa je svrstana bliže `web_search`/`note_search` kategoriji
  (dostupno uvijek) nego Computer-Mode-gated kategoriji — direktno smanjuje
  trenje koje je korisnik prijavio.
- `os.walk` sa `followlinks=False` (default) — sprječava beskonačnu rekurziju
  kroz Windows-ove poznate symlink petlje (npr.
  `AppData\Local\Application Data`).

## Šta nije dirano

- Confirmation-retry-ne-javlja-modelu gap (opisan gore u "Istraga") —
  dokumentovan kao poseban, širi follow-up nalaz, ne popravljen ovdje.
- `permission_engine.py` — nula izmjena.
- `computer_click`/`computer_type_text`/ostali Phase 13/14 alati — netaknuti;
  i dalje postoje za slučajeve kad je stvarna GUI interakcija potrebna (ne
  samo lociranje foldera).

## Verifikacija

- `python -m pytest -q` (cijeli `python_backend` suite) — **281 passed**
  (273 prije + 8 iz `test_filesystem_search.py`, uključujući 3 dodana u
  Reviziji 2). Novi testovi monkeypatch-uju `_search_roots` na jedan
  `tmp_path` da testovi ne diraju pravi home direktorij/diskove (brzo,
  deterministički) — pokrivaju: folder match, file match, prazan query →
  `INVALID_ARGUMENTS`, cap na 40 rezultata + `truncated=True`,
  case-insensitive match, default `type="any"` na pravom "thumbnails" gap-u,
  jednina/množina fallback, i BFS regresioni test (plitak pogodak pored
  duboke abecedno-prve "decoy" grane).
- Ručni test protiv PRAVOG fajl sistema (van pytest suite-a, opisano u
  "Revizija 2") — potvrđeno da alat sad pronalazi stvarne thumbnail fajlove.
- `npm run typecheck`, `npm run build` — čisto.
- `npm run check` (node --check na sve `.cjs`) — čisto.
- `mcp__gitnexus__detect_changes` — risk HIGH (kumulativno sa necommitovanim
  `set_mode` radom), ručno potvrđen `git diff` kao čisto aditivan.
- Runtime NIJE testiran (agent nema Electron GUI pristup).

## Rizici/ograničenja

- Sistem-širok fallback (full-drive walk) na sporim/velikim diskovima može
  potrošiti pun 10s budžet bez pogotka ako upit ne postoji ni u data_dir ni u
  home direktoriju — vraća `truncated: true` i prazne/djelomične rezultate
  umjesto greške, ali korisnik neće dobiti "nema tog foldera" konačan
  odgovor, samo "pretraga je stala".
- Ne prati simboličke linkove (namjerno, sigurnost), pa folder dostupan samo
  preko symlink-a van skeniranih korijena neće biti pronađen.
- Confirmation-retry-ne-javlja-modelu gap (vidi "Istraga") ostaje otvoren za
  DRUGE confirmation-gated alate — ako se korisnikova petlja ponovi za neki
  drugi visok-rizik alat (ne pretragu foldera), to je taj poseban, širi
  problem, ne ovaj.

## Potreban follow-up

1. Korisnički test: glasom zatražiti "pronađi folder sa thumbnailovima" (ili
   "pronađi thumbnailove") i potvrditi da `filesystem_search` odgovori
   direktno, sa pravim `.png` fajlovima na listi, bez ijedne confirmation
   dijaloga.
2. Razmotriti (odvojena odluka, van ovog PR-a): popraviti generički
   confirmation-retry da javlja rezultat nazad u Realtime sesiju
   (`function_call_output` za originalni `call_id`) — riješilo bi potencijalne
   slične petlje za SVE confirmation-gated alate, ne samo pretragu foldera.
3. Ako korisnik i dalje traži da thumbnailovi žive u pravom `thumbnails/`
   podfolderu (ne kao labavi fajlovi u `data/`) — to je odvojena
   arhitektonska odluka (mijenja postojeće putanje sačuvane u
   `data/ricky-db.json`), van obima ovog PR-a.

## Potrebna korisnička potvrda

Runtime test (stavka 1 gore) prije nego se ovo smatra potpuno zatvorenim.
