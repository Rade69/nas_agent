# Agent Report — browser_tabs PR 2 (aktiviranje ordinalnog taba)

- Datum: 2026-07-15
- Agent: pi
- Faza: PR 1-3 (kompletno — browser tab kontrola)

## PR 1 — Ekstenzija, pairing, read-only lista

### MV3 browser ekstenzija (`browser_extension/`)
- `manifest.json` — Manifest V3, minimal permissions (`tabs`, `storage`), samo loopback WebSocket
- `service-worker.js` — autentifikovani WebSocket klijent sa auth, list_tabs, activate_tab, close_tab
- `options.html` / `options.js` — pairing interfejs sa status pollingom

### Python WebSocket broker (`app/services/browser_extension_broker.py`)
- `BrowserExtensionBroker` — singleton, 256-bit pairing secret, WebSocket handler
- `SnapshotStore` — in-memory store sa TTL-om (10s)
- Auth: `secrets.compare_digest()`, timing-safe
- Request/response: `asyncio.Future` semafor + 8s timeout

### browser_tabs tool, šeme, REST endpoint, registracija
- 23 testa

## PR 2 — Aktiviranje ordinalnog taba

### Pojačan error handling
- `activate_tab()` detektuje "No tab with id"/"No window with id"/"not found" → `TAB_SNAPSHOT_STALE`
- Isti pattern na `close_tab()`

### Model instrukcije
- Precizirane u `realtimeToolSpecs.cjs` i `phase13.py`

### Testovi
- 8 novih activate testova (ukupno 31)

## PR 3 — Zatvaranje sa potvrdom i hardening

### browser_tab_close — zaseban high-risk confirmation tool
- **Odvojen od browser_tabs** jer permission engine radi na nivou tool-a (`requires_confirmation` je boolean)
- `risk="high"`, `requires_confirmation=True`
- Parametri: `browser`, `snapshot_id`, `position` (bez `action` — tool radi samo close)
- `browser_tabs` sad podržava samo `list` i `activate` (action enum bez "close")

### Confirmation flow
- Prvi poziv bez `confirmation_id` → permission engine vraća `CONFIRMATION_REQUIRED`
- Confirmation se veže za `tool_name="browser_tab_close"` + `payload_hash` argumenata
- `payload_hash` garantuje da odobreni tab ne može biti zamijenjen drugim
- Poslije odobrenja, handler provjerava snapshot svježinu → `TAB_SNAPSHOT_STALE` ako je istekao
- Potrošeni confirmation_id ne može se ponovo koristiti (`CONFIRMATION_NOT_APPROVED`)

### Sigurnosne garancije
- Zatvaranje zahtijeva eksplicitno odobrenje korisnika ✅
- Odobrenje je vezano za tačan tab (snapshot_id + position) preko payload_hash ✅
- Stale snapshot prije odobrenja → `TAB_SNAPSHOT_STALE`, ne zatvara drugi tab ✅
- Potrošeni confirmation_id ne može se iskoristiti dvaput ✅
- `browser_tab_close` u `LEGACY_FAIL_CLOSED_TOOLS` — ne može proći kroz legacy PowerShell fallback ✅
- Incognito tabovi odbijeni i u close path-u ✅
- `brejv` → `brave` normalizacija za close ✅

### Testovi — 10 novih close testova (ukupno 41)
- `test_close_requires_confirmation_without_id` — CONFIRMATION_REQUIRED bez confirmation_id
- `test_close_succeeds_after_approval` — pun flow: propose → approve → execute → success
- `test_close_stale_snapshot_after_approval` — snapshot istekao poslije odobrenja
- `test_close_confirmation_cannot_be_reused` — potrošeni ID odbijen
- `test_close_payload_hash_mismatch_rejected` — različiti argumenti odbijeni
- `test_close_incognito_rejected` — incognito odbijen
- `test_close_brejv_normalized` — brejv → brave
- `test_browser_tab_close_is_high_risk_with_confirmation` — provjera definicije
- `test_close_requires_snapshot_id_for_dedicated_tool` — validacija argumenata
- `test_close_requires_position` — validacija argumenata

## Fajlovi

### Novi
- `browser_extension/manifest.json`
- `browser_extension/service-worker.js`
- `browser_extension/options.html`
- `browser_extension/options.js`
- `python_backend/app/schemas/browser_tabs.py`
- `python_backend/app/services/browser_extension_broker.py`
- `python_backend/app/tools/system/browser_tabs.py`
- `python_backend/app/api/browser_bridge.py`
- `python_backend/tests/test_browser_tabs.py`

### Izmijenjeni
- `python_backend/app/agent/tool_catalog/phase13.py` — browser_tabs + browser_tab_close
- `python_backend/app/main.py` — init_broker, WebSocket ruta, browser_bridge router
- `electron/core/realtimeToolSpecs.cjs` — browser_tabs + browser_tab_close
- `electron/main.cjs` — PHASE11_DELEGATED_TOOLS + LEGACY_FAIL_CLOSED_TOOLS

## Provjere
- `python -m pytest tests/test_browser_tabs.py -v` → 41/41 PASSED
- Nema nove business logike u electron/main.cjs
- Bez proizvoljnog shell executiona, content injectiona, pristupa sadržaju stranice

## Preostalo za follow-up
- Produkcijski packaging/auto-instalacija ekstenzije
- Firefox ekstenzija
- Smoke test sa pravim browserom po checklisti iz brifa
- Ikone za ekstenziju
