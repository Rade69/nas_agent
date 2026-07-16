# Agent Report — C1 (multi-connection broker + profile routing)

- Datum: 2026-07-16
- Agent: pi
- Faza: C1 — multi-connection registry i profile routing (nastavak na C0)

## Šta je urađeno

### 1. Multi-connection broker (`browser_extension_broker.py`)
- **`ConnectionState`** — per-connection stanje: websocket, install_credential, pending dict, connected_at
- **`_connections: dict[profile_id, ConnectionState]`** — zamjenjuje single `_active_ws`/`_active_install`
- **`_register_connection()`** — registruje novu konekciju; ako isti profile_id već postoji, zatvara staru
- **`_remove_connection()`** — čisti konekciju po WebSocket-u
- **`_resolve_profile(browser, profile_id)`** — routing logika:
  1. Ako `profile_id` naveden → egzaktan match
  2. Ako `browser` naveden sa tačno jednim matchom → koristi ga
  3. Ako `browser` naveden sa više matcheva → `BROWSER_PROFILE_AMBIGUOUS`
  4. Ako ništa nije navedeno sa tačno jednom konekcijom → koristi nju
  5. Inače → odgovarajuća greška
- **`revoke_connection(profile_id)`** — opoziva credential, zatvara WebSocket, briše iz registry-ja
- **`rename_profile(profile_id, new_label)`** — mijenja display label profila
- **`get_connections()`** — lista sve konekcije (aktivne + stored credentials)

### 2. Snapshot/profile binding
- **`SnapshotStore.get(snapshot_id, profile_id)`** — snapshot se može dohvatiti samo za profil koji ga je kreirao
- Ako `profile_id` ne odgovara → `None` (odbijen pristup)
- `TAB_PROFILE_MISMATCH` — novi error code kad snapshot pripada drugom profilu
- Sve `list_tabs`/`activate_tab`/`close_tab` metode sada vezuju snapshot za profile_id

### 3. Tool schemas — `profile_id` parametar
- `browser_tabs`: dodato `profile_id` polje (opciono)
- `browser_tab_close`: dodato `profile_id` polje (opciono)
- `realtimeToolSpecs.cjs`: ažurirani opisi sa profile instrukcijama
- `phase13.py`: ažurirani opisi

### 4. API (`browser_bridge.py`)
- `GET /browser-bridge/status` — sada vraća `connections` listu (C1 multi-connection)
- `GET /browser-bridge/connections` — lista svih konekcija (aktivnih + stored credentials)
- `POST /browser-bridge/connections/{profile_id}/revoke` — opoziv credentiala
- `PATCH /browser-bridge/connections/{profile_id}` — preimenovanje profila

### 5. Testovi — 8 novih C1 testova (ukupno 50)
- `test_multi_connection_resolve_profile_exact_match` — egzaktan profile_id match
- `test_resolve_profile_by_browser_kind` — routing po browser_kind
- `test_resolve_profile_ambiguous` — više profila istog browsera → ambiguous
- `test_resolve_profile_single_connection_no_browser` — jedna konekcija, automatski routing
- `test_snapshot_profile_binding_prevents_cross_profile_use` — snapshot iz profila A ne može na profilu B
- `test_revoke_connection_removes_it` — revoke briše konekciju i markira credential revoked
- `test_get_connections_lists_active_and_stored` — lista aktivne + stored credentials
- `test_rename_profile_updates_label` — rename ažurira label

## Fajlovi

### Izmijenjeni
- `python_backend/app/services/browser_extension_broker.py` — multi-connection registry, profile routing, snapshot binding
- `python_backend/app/api/browser_bridge.py` — connections/revoke/rename endpointi
- `python_backend/app/tools/system/browser_tabs.py` — profile_id parametar u pozivima brokeru
- `python_backend/app/agent/tool_catalog/phase13.py` — profile_id u tool schemas
- `electron/core/realtimeToolSpecs.cjs` — profile_id u Realtime specovima
- `python_backend/tests/test_browser_tabs.py` — 8 novih C1 testova + popravke postojećih

## Provjere
- TypeScript: `tsc --noEmit` → čist
- Python: `pytest tests/test_browser_tabs.py -q` → 50/50 PASSED
- Nema nove business logike u `electron/main.cjs`
