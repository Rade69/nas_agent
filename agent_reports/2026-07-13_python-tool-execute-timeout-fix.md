# Agent report — pythonClient.cjs 5s default timeout uzrokovao "backend error" za spore alate

**Datum:** 2026-07-13
**Scope:** `electron/main.cjs`, `python_backend/app/tools/system/filesystem_search.py`.

**Povod:** Korisnik je prijavio "agent prijavljuje grešku na bekendu i ne
može da pretražuje foldere i fajlove" — runtime greška za novi
`filesystem_search` alat, koji je prema pytest-u i ručnim testovima protiv
pravog fajl sistema (agent_reports/2026-07-13_filesystem-search-tool.md
"Revizija 2") radio ispravno na Python strani.

## Istraga

Reprodukovao sam poziv direktno preko `/tools/execute` HTTP endpoint-a (ne
samo unit testove) i izmjerio da `filesystem_search` rutinski traje **5.4s
do 12.2s** protiv pravog fajl sistema (puna pretraga `data_dir` + `home` +
`C:\`). Zatim sam pronašao `electron/services/pythonClient.cjs:18`:

```js
const timeoutMs = Number(options.timeoutMs || 5000);
```

`requestJson()` ima **hardkodiran default od 5000ms** ako pozivalac ne
proslijedi eksplicitan `timeoutMs`. `electron/main.cjs`'s `executeTool()`
pozivi (i u `set_mode` grani i u `PHASE11_DELEGATED_TOOLS` grani) NISU
prosljeđivali `timeoutMs` uopšte — nasljeđivali su ovaj 5s default,
potpuno nezavisno od toga što svaki Python alat ima SVOJ, mnogo veći
registrovani `timeout_ms` (`image_generate=90000`, `web_search=30000`,
`filesystem_search=20000`, ostali default `10000` — `phase11.py`).

**Zašto se ovo nije primijetilo ranije:** za alate sa legacy Electron
fallback-om (`image_generate`, `web_search`, `computer_click`, ...), kad
5s timeout prerano baci grešku, `catch` blok u `handleToolsExecute` (main.cjs
linija ~412+) tiho pada na legacy handler ispod, koji radi SVOJ, neograničen
`fetch()` poziv — pa je krajnji korisnik i dalje dobijao rezultat, samo kroz
drugi kod put, bez ikakve vidljive greške. `filesystem_search` NEMA legacy
ekvivalent (nema PowerShell/Electron verziju "pretraži fajl sistem") — kad
je 5s timeout prerano prekinuo poziv, fallback lanac je došao do kraja bez
poklapanja i vratio `{ ok: false, error: "Unknown tool: filesystem_search" }`
(main.cjs linija ~628) — TO je greška koju je korisnik vidio.

## GitNexus impact

`detect_changes` — risk HIGH (kumulativno sa ostalim necommitovanim radom
ove sesije; `handleToolsExecute` je ponovo dodirnut). Ručno provjeren
`git diff` — izmjena je striktno: novi imenovani konstant
`PYTHON_TOOL_EXECUTE_TIMEOUT_MS` + dodavanje `{ timeoutMs: ... }` kao drugog
argumenta na oba postojeća `executeTool()` poziva. Nijedna postojeća grana
logike nije izmijenjena.

## Šta je urađeno

1. **`electron/main.cjs`** — novi `const PYTHON_TOOL_EXECUTE_TIMEOUT_MS = 100000`
   (100s, iznad najvećeg trenutno registrovanog Python `timeout_ms`-a od
   90000 za `image_generate`, sa marginom za mrežni/serijalizacioni overhead).
   Prosljeđen kao `{ timeoutMs: PYTHON_TOOL_EXECUTE_TIMEOUT_MS }` drugi
   argument na OBA `executeTool()` poziva (set_mode grana + PHASE11_DELEGATED_TOOLS
   grana) — sad Python-ova sopstvena `timeout_ms` vrijednost po alatu je ta
   koja stvarno odlučuje kad je poziv "predugo trajao", ne Electron-ov HTTP
   sloj koji je preuranjeno presijecao.
2. **`filesystem_search.py`** — usput uočeno i popravljeno dvoje, otkriveno
   ručnim testiranjem protiv pravog fajl sistema tokom ove istrage:
   - `_bfs_search()` je sad primao eksplicitan `deadline` parametar
     (apsolutno vrijeme, ne trajanje) umjesto da svaki poziv računa svoj
     svježi `MAX_SECONDS` budžet — jednina/množina retry prolaz (dodan u
     Reviziji 2) je prije mogao UDVOSTRUČITI najgori slučaj latencije (do
     ~20s za genuinski "nema rezultata" upit); sad dijeli JEDAN budžet, pa
     je gornja granica ~10s ukupno. Ručno potvrđeno: isti "nema rezultata"
     upit sad traje 10.06s (prije 12.24s, a teorijski moglo do ~20s na
     sporijem disku).
   - Per-entry provjere (`entry.is_symlink()`, `entry.is_dir()`) su sad
     zajedno u jednom `try/except OSError` bloku umjesto samo `is_dir()`.
     Puna sistem-šira pretraga NEIZBJEŽNO nailazi na zaštićene/neobične
     stavke (tuđi korisnički profili pod `C:\Users\`, reparse point-ovi,
     permission-denied fajlovi) — jedan nepokriven `is_symlink()` poziv koji
     baci `OSError` bi prije srušio CIJELU pretragu umjesto da samo
     preskoči tu jednu stavku. Nije potvrđeno da je ovo bio uzrok
     PRIJAVLJENE greške (glavni uzrok je timeout iznad), ali je stvaran,
     realan rizik otkriven dok sam ovo istraživao, i direktno se odnosi na
     korisnikov zahtjev da pretraga bude "besprijekorna".

## Zašto ovako

- Blanket povećanje timeout-a (umjesto per-tool mapiranja Electron ↔ Python
  `timeout_ms` vrijednosti) — jednostavnije, i HTTP klijent treba biti
  VELIKODUŠNIJI od bilo kojeg pojedinačnog server-side budžeta, nikad
  restriktivniji; server-side `timeout_ms` po alatu (tool_executor.py) je i
  dalje stvarna, autoritativna granica.
- Dijeljen `deadline` umjesto per-poziv budžeta u `_bfs_search` — ista
  filozofija kao za Electron timeout: jedan combined budžet je uvijek
  bezbjedniji od zbira nezavisnih budžeta kad se pozivi lančano nadovezuju.

## Šta nije dirano

- `pythonClient.cjs`'s `requestJson()` sam po sebi — default od 5000ms
  ostaje za pozive koji GA eksplicitno ne overrideuju (npr. `/health` već
  koristi svoj 1000ms override) — nije globalno povećan, samo za
  `executeTool()` pozive iz `handleToolsExecute`.
- Ostali `timeout_ms` po Python alatu (`phase11.py`, `phase13.py`, `phase14.py`)
  — nedirani, i dalje validni kao donja/stvarna granica.
- Legacy fallback lanac u `handleToolsExecute` — nedirano; i dalje postoji
  kao safety net za alate koji ga imaju.

## Verifikacija

- `python -m pytest -q` (cijeli suite) — **281 passed**, uključujući svih 8
  `test_filesystem_search.py` testova nakon `_bfs_search` refaktora
  (deljeni deadline parametar).
- Ručni test protiv pravog HTTP endpoint-a i pravog fajl sistema (van pytest
  suite-a): upit sa postojećim pogotkom (`"thumbnail"`) i upit bez ijednog
  pogotka (`"xyznonexistentfolders"`, forsira i plural retry) — oba vraćaju
  `200 OK` sa ispravnim rezultatom; drugi sad traje ~10s (prije popravke bi
  Electron-ov 5s timeout prekinuo OBA nakon 5s).
- `npm run typecheck`, `npm run build`, `npm run check` (node --check) — čisto.
- `mcp__gitnexus__detect_changes` — risk HIGH (kumulativno, `handleToolsExecute`
  ponovo dodirnut), ručno potvrđen `git diff` kao strogo aditivan/ograničen.
- Runtime u Electron-u NIJE testiran (agent nema GUI pristup) — ovo je
  ISPRAVKA HTTP-klijent sloja unutar Electron main procesa, van pytest-ovog
  dosega (pytest testira samo Python stranu direktno preko TestClient-a, ne
  Electron-ov `fetch`/`AbortController` put).

## Rizici/ograničenja

- Ovaj bug je vjerovatno tiho uticao i na `image_generate`/`web_search`/druge
  spore Python-delegirane alate ranije (maskiran njihovim legacy fallback-om)
  — sad kad Electron-ov timeout više ne preuranjeno puca, ti alati će
  dosljednije koristiti Python put umjesto tihog pada na legacy kod. Ovo je
  POBOLJŠANJE (Python put ima permission_engine, action log, itd. koje legacy
  put nema), ali je promjena u ponašanju vrijedna pomena — ako je legacy put
  imao neku suptilnu razliku u ponašanju na koju se korisnik možda oslanjao,
  sad će se rjeđe koristiti.
- 100000ms je i dalje konačna granica — genuinski zaglavljen Python proces
  (ne spor, nego mrtav/blokiran) bi i dalje ostavio glasovni razgovor da čeka
  do 100 sekundi prije greške. Prihvatljivo za sada (rijedak slučaj), ali
  vrijedi imati na umu.

## Potreban follow-up

Korisnički test: zatražiti glasom/tekstom "pronađi folder sa thumbnailovima"
ili sličan upit i potvrditi da `filesystem_search` sad radi bez "backend
error"/"Unknown tool" poruke.

## Potrebna korisnička potvrda

Runtime test (gore) prije nego se ovo smatra potpuno zatvorenim.
