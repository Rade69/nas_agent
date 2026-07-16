# Agent Report — C4 (produkcijska distribucija + hardening)

- Datum: 2026-07-16
- Agent: pi
- Faza: C4 — publishing, protocol version, rate limiting, privacy audit

## Šta je urađeno

### 1. Publishing dokumentacija
- `docs/BROWSER_BRIDGE_PUBLISHING.md` — kompletni vodič:
  - Chrome Web Store publishing proces (ZIP, listing, review)
  - Edge Add-ons (opcija A + B)
  - Brave/Vivaldi/Opera/Opera GX/Chromium — svi koriste Chrome Web Store
  - Store linkovi po browseru
  - Privacy deklaracija za store listing
  - Produkcijski checklist

### 2. Protocol versioning
- `SUPPORTED_PROTOCOL_VERSIONS = [1, 2]` — trenutna v2
- `protocol_version: 2` u `auth_ok` i `paired` handshake odgovorima
- Backward compatibility: backend najavljuje podržane verzije

### 3. Rate limiting
- `PAIRING_RATE_LIMIT_MAX = 5` pokušaja u `PAIRING_RATE_LIMIT_WINDOW_SECONDS = 60`
- `PAIRING_RATE_LIMITED` error code (HTTP 429)
- In-memory brojač sa sliding window-om

### 4. Credential storage audit
- Dokumentovan u `BROWSER_BRIDGE_PUBLISHING.md`:
  - Ekstenzija: samo `chrome.storage.local`, nikad localStorage/sessionStorage
  - Backend: in-memory samo, nestaje na restart
  - Revocation flow: markira `revoked=True`, zatvara WebSocket

### 5. Privacy hardening
- Manifest proširen sa preciznim privacy opisom
- `host_permissions: []` potvrđen
- `incognito: not_allowed` potvrđen
- Privacy deklaracija za store listing

### 6. Error codes — 5 novih
- `TAB_PROFILE_MISMATCH`, `BROWSER_PROFILE_AMBIGUOUS`
- `BROWSER_EXTENSION_VERSION_UNSUPPORTED`, `PAIRING_RATE_LIMITED`, `PAIRING_BROWSER_MISMATCH`

### 7. Testovi — 2 nova (ukupno 59)
- `test_pairing_rate_limit_blocks_excessive_attempts` — rate limit funkcioniše
- `test_extension_manifest_has_required_permissions` — manifest validacija

## Provjere
- `pytest tests/test_browser_tabs.py -q` → 59/59 PASSED
- TypeScript: čist