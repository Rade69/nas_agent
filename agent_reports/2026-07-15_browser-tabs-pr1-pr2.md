# Agent Report — browser_tabs PR 2 (aktiviranje ordinalnog taba)

- Datum: 2026-07-15
- Agent: pi
- Faza: PR 2 od 3 (nastavak na PR 1)

## Šta je urađeno u PR 2

### 1. Pojačan error handling za activate (broker)
- `activate_tab()` sada detektuje "No tab with id", "No window with id", "not found" u error porukama ekstenzije i mapira ih na `TAB_SNAPSHOT_STALE`
- Isti pattern primijenjen i na `close_tab()` za PR 3
- Sve error poruke su sada preciznije i korisnije (npr. "Tab at position 3 no longer exists. Please list tabs again to see the current state.")

### 2. Poboljšan odgovor za activate
- `browser_tabs.py` sada uključuje `url` polje u rezultat
- Poruka uključuje naslov taba: "Aktivirao sam 2. tab: GitHub."
- Fallback poruka ako title nije dostupan: "Aktivirao sam 2. tab."

### 3. Model instrukcije — precizirane u oba sloja
- `electron/core/realtimeToolSpecs.cjs`: proširen description sa eksplicitnim instrukcijama:
  - '"open the fifth tab" → aktiviraj, NE kreiraj novi tab'
  - 'Na TAB_SNAPSHOT_STALE re-list i potvrdi metu'
  - 'Na BROWSER_EXTENSION_NOT_CONNECTED reci korisniku, NE pokušavaj prečice'
  - 'Poslije uspjeha reci tačno: Aktivirao sam peti tab: YouTube.'
  - `snapshot_id` i `position` parametri sad imaju description
- `phase13.py`: isti nivo instrukcija u Python katalogu

### 4. Testovi — 8 novih activate testova (ukupno 31)
- `test_activate_succeeds_with_valid_snapshot` — uspješan activate sa snapshotom
- `test_activate_first_and_last_tab` — pozicije 1 i 6 (prvi/posljednji)
- `test_activate_stale_snapshot_error` — TAB_SNAPSHOT_STALE kod isteklog snapshota
- `test_activate_tab_not_found_in_stale_snapshot` — tab više ne postoji na poziciji
- `test_activate_position_out_of_range` — pozicija van opsega
- `test_activate_rejects_incognito` — incognito tab odbijen
- `test_activate_extension_not_connected` — nema konekcije
- `test_activate_brejv_normalized` — 'brejv' → 'brave' za activate

## Fajlovi

### Izmijenjeni
- `python_backend/app/services/browser_extension_broker.py` — pojačan error handling za activate_tab i close_tab
- `python_backend/app/tools/system/browser_tabs.py` — bolje poruke, url u odgovoru
- `electron/core/realtimeToolSpecs.cjs` — precizne model instrukcije
- `python_backend/app/agent/tool_catalog/phase13.py` — precizne model instrukcije
- `python_backend/tests/test_browser_tabs.py` — 8 novih testova

## Provjere
- `python -m pytest tests/test_browser_tabs.py -v` → 31/31 PASSED
- `python -m pytest tests/ -v` → 354/356 PASSED (2 pre-existing)
- Nema nove business logike u electron/main.cjs
- Bez proizvoljnog shell executiona

## Preostalo za PR 3
- close kao high-risk confirmation akcija
- Provjera da approval retry ne može djelovati na drugi tab
- Reconnect hardening (multi-window, incognito behavior, privacy audit)
- Packaging/installation za produkciju
- Smoke test po checklisti iz brifa
