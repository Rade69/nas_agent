# Agent Report: open_path alat + browser_open bez Computer Mode

**Datum:** 2026-07-19
**Autor:** pi (co-authored)
**Problem:** korisnik-prijavljeni UX problemi sa pretragom foldera i otvaranjem browser-a

## Problem 1: agent nađe folder, ali ga ne može otvoriti

**Simptom:** "nađi folder X i otvori ga" → `filesystem_search` vrati putanju,
ali model nema alat da je otvori. Jedina opcija je `computer_open_app("explorer")`
+ slijepo klikanje kroz Explorer, gdje svaki klik traži novu potvrdu.

**Uzrok:** `computer_open_app` prima samo fiksni set imena i pokreće ih bez
argumenata (`Popen([target])`). Nema `os.startfile(path)`, nema
`explorer /select,<path>`. Sistem prompt zabranjuje klik-navigaciju, ali ne
nudi alternativu za otvaranje nađenog foldera.

**Ispravka:**
- Novi modul `python_backend/app/tools/system/open_path.py` sa handlerom koji:
  - Validira putanju kroz `path_sandbox.resolve_within_roots` (odbija
    UNC/network, resoluje symlinks/traversal)
  - Folderi: `os.startfile(path)` — otvara Explorer na tom folderu
  - Fajlovi: `explorer.exe /select,<path>` — označi fajl u containing folderu
    (NIKAD `os.startfile` na fajlu — to bi pokrenulo default aplikaciju)
  - allowed_roots = ista logika kao `filesystem_search` (svi diskovi + home
    + data_dir), tako da svaka putanja koju search nađe može biti otvorena
- Registracija u `phase13.py`: `risk="medium"`, `requires_computer_mode=False`,
  `requires_confirmation=False` (medium risk omogućava P2-K eskalaciju ako
  je model već video nepoverljivi sadržaj u ovom razgovoru)
- Spec u `realtimeToolSpecs.cjs`: dodat `open_path` sa `risk: "medium"`
- Sistem prompt (`realtime.cjs`): dodat instrukciju — "After filesystem_search
  returns a path and ${userName} asks to open it, call open_path with that
  path — do NOT use computer_open_app + click navigation to get there."

**Kriterij prihvatanja:** `filesystem_search("thumbnails")` → `open_path(nađena_putanja)`
→ Explorer otvori taj folder, bez ijedne potvrde i bez Computer Mode.

## Problem 2: "otvori browser" ne radi bez Computer Mode

**Simptom:** "otvori Brave i idi na example.com" → `COMPUTER_MODE_REQUIRED`
greška, korisnik mora prvo ući u Computer Mode (koji pali orb, mijenja prozor)
samo da bi otvorio browser.

**Uzrok:** `phase13.py` `_def()` helper ima `requires_computer_mode: bool = True`
kao default. `browser_open` nije postavljao `requires_computer_mode=False`,
pa je nasljeđivao `True`. Nedosljedno: `web_search` (čita web) ne traži
Computer Mode, a `browser_open` (samo pokrene browser na validiranom URL) — traži.

**Ispravka:**
- `phase13.py`: `browser_open` sada eksplicitno postavlja `requires_computer_mode=False`
- `realtimeToolSpecs.cjs`: uklonjeno "Requires computer mode" iz `browser_open`
  description-a

**Zašto je bezbjedno:** `browser.py:_validate_url` već traži http/https + netloc,
odbija embedded kredencijale; `shell=False`, lista argumenata; browser allowlist.
`risk="medium"` ostaje, tako da P2-K eskalacija (per-conversation
`external_content_seen`) i dalje blokira napad "web stranica naredi modelu
da otvori browser na zlonamernom URL".

**Kriterij prihvatanja:** `browser_open(browser="brave", url="https://example.com")`
u display modu → prolazi, browser se otvara, bez `COMPUTER_MODE_REQUIRED`.

## Izmijenjeni fajlovi

| Fajl | Promjena |
|------|----------|
| `python_backend/app/tools/system/open_path.py` | NOVI — open_path handler |
| `python_backend/app/agent/tool_catalog/phase13.py` | registracija open_path + browser_open bez computer_mode |
| `electron/core/realtimeToolSpecs.cjs` | open_path spec + browser_open description |
| `electron/ipc_handlers/realtime.cjs` | sistem prompt instrukcija za open_path |

## Testovi

- Svi postojeći pytest testovi prolaze (43 passed)
- TypeScript `tsc --noEmit` prolazi
- `node --check` svih .cjs fajlova prolazi
- `open_path` i `browser_open` se uspješno registruju sa ispravnim
  `requires_computer_mode` i `risk` vrijednostima

## Status

- **Problem 1:** ✅ implementirano
- **Problem 2:** ✅ implementirano
