# Agent Report — C0 (Browser Bridge live bug fix)

- Datum: 2026-07-16
- Agent: pi
- Faza: C0 — instalacija i pairing jednog Brave profila (nastavak na PR 1-3)

## Uvod — zašto C0

PR 1-3 imaju 41 automatizovani test i ispravnu internu logiku, ali **stvarni browser nije imao završen instalacijski, pairing i routing put**:

- Ekstenzija nije instalirana ni u jedan browser
- Nije bilo Settings UI-ja za browser bridging
- Pairing je zahtijevao ručno kopiranje 64-karakterskog globalnog secreta
- `GET /browser-bridge/status` je prikazivao prvih 8 karaktera secreta (loš UX + bezbjednosni problem)
- Backend nije imao per-install credentials — jedan globalni secret za sve

C0 rješava ove probleme za **jedan browser profil** (Brave, development-only `Load unpacked` tok).

## Šta je urađeno

### 1. Backend: pairing token sistem (`browser_extension_broker.py`)
- **PairingSession** — in-memory session sa TTL-om (5 minuta), human_code (6 karaktera), full_token
- **InstallCredential** — per-install: installation_id, profile_id, credential (256-bit), browser_kind, profile_label
- **`create_pairing_session(browser_kind)`** — generiše jednokratni pairing token
- **`_consume_pairing_token()`** — atomarno troši token, kreira credential
- **`get_status()`** — vraća strukturirani status (connected, browser_kind, profile_label, profile_id, installation_id, extension_version)
- **Legacy backward compat** — stari `auth` sa globalnim secretom i dalje radi (privremeno)
- **Credential-based auth** — extension šalje `{type: "auth", credential, installation_id}`
- **`pair` message type** — novi protokol: extension šalje `{type: "pair", code, browser_kind, installation_id, ...}`, backend vrati `{type: "paired", credential, profile_id, ...}`

### 2. Backend API (`browser_bridge.py`)
- `GET /browser-bridge/status` — strukturirani status (bez izlaganja secreta)
- `POST /browser-bridge/pairing-sessions` — prima `{browser_kind}`, vraća `{pairing_id, human_code, expires_in_seconds}`
- `GET /browser-bridge/pairing-sessions/{id}` — status pairing sesije
- `DELETE /browser-bridge/pairing-sessions/{id}` — otkazivanje

### 3. Ekstenzija (`service-worker.js`)
- **`installationId`** — generiše se na prvoj instalaciji, perzistira u `chrome.storage.local`
- **Credential storage** — `credential`, `profile_id`, `browser_kind`, `profile_label`
- **`pairWithCode(code, browserKind, profileLabel)`** — novi pairing flow:
  - Otvara WebSocket, šalje `pair` poruku
  - Prima `paired` odgovor sa credentialom
  - Čuva credential, reconnectuje sa credential-based auth
- **`connect()`** — preferira credential-based auth, fallback na legacy secret
- **`reset_pairing`** — briše credential (za re-pairing)

### 4. Ekstenzija Options stranica
- **Pairing code unos** — 6-karaktersko polje, browser selector, profile label
- **Status prikaz** — browser/profile, installation_id, reconnect attempts
- **Reset pairing dugme**
- Legacy secret sekcija sakrivena (toggle za dev)

### 5. SettingsPanel — "Browseri i kartice" sekcija
- **Status indikator** — povezano/nepovezano, browser, profil, verzija
- **Pairing flow** — "Poveži" dugme → generiše pairing kod → prikazuje 6-char kod sa countdownom → "Kopiraj kod" / "Otkaži"
- **Instrukcije za instalaciju** — `Load unpacked` koraci za Brave/Chrome/Edge
- **Live polling** — status se osvježava svakih 5 sekundi

### 6. Electron IPC (tanak transport)
- `preload.cjs`: 4 nove `window.ricky` metode (getBrowserBridgeStatus, startBrowserPairing, getBrowserPairingStatus, cancelBrowserPairing) — samo `ipcRenderer.invoke` pozivi, bez logike
- `main.cjs`: 4 handler funkcije — samo `requestJson` pozivi ka Python backendu
- Bez poslovne logike u electron sloju

### 7. Testovi
- `test_broker_pairing_session_flow` — kreiraj session, provjeri status, otkaži
- `test_broker_get_status_returns_structure` — provjera strukturiranog statusa
- `test_broker_ensure_secret_generates_and_persists` — ažuriran za `_ensure_legacy_secret` API
- **Ukupno: 42 testa, svi prolaze**

## Fajlovi

### Izmijenjeni
- `python_backend/app/services/browser_extension_broker.py` — kompletan redizajn: pairing tokeni, per-install credentials, installation_id, `pair` protokol
- `python_backend/app/api/browser_bridge.py` — pairing endpointi, novi structured status
- `browser_extension/service-worker.js` — installation_id, credential storage, `pairWithCode`, credential-based auth
- `browser_extension/options.html` — pairing code UI, browser selector, reset
- `browser_extension/options.js` — pair flow, status polling
- `src/components/pixel/SettingsPanel.tsx` — "Browseri i kartice" sekcija
- `src/vite-env.d.ts` — BrowserBridgeStatus, PairingSession tipovi + window.ricky metode
- `electron/main.cjs` — 4 IPC handler funkcije + registracija
- `electron/preload.cjs` — 4 window.ricky bindinga
- `python_backend/tests/test_browser_tabs.py` — ažurirani testovi

## Šta NIJE urađeno (C1-C4)
- Multi-connection registry (samo jedan browser istovremeno — C1)
- Browser discovery (detekcija instaliranih browsera — C2)
- Chrome/Edge/Vivaldi/Opera GX/Chromium guided install (C2-C3)
- `browser_tab_open` novi tab u povezanom profilu (C2)
- Produkcijska distribucija (Chrome Web Store, Edge Add-ons — C4)
- Stvarni E2E smoke test sa pravim browserom (zahtijeva ručno testiranje)

## Stvarni smoke test checklist (ručno)

1. Otvoriti Brave sa najmanje 6 tabova poznatih naslova
2. Settings → "Browseri i kartice" → Poveži (Brave) → iskopirati kod
3. Otvoriti `brave://extensions` → Developer mode ON → Load unpacked → `browser_extension/`
4. Kliknuti na ikonicu ekstenzije → Options → unijeti pairing kod → Pair Now
5. Status mora pokazati "Povezano"
6. Agent treba moći da izlista tabove, aktivira ordinalni tab
7. Zatvaranje zahtijeva potvrdu

## Provjere
- TypeScript: `tsc --noEmit` → čisto, bez grešaka
- Python: `pytest tests/test_browser_tabs.py -q` → 42/42 PASSED
- Nema nove business logike u `electron/main.cjs`
- Bez proizvoljnog shell executiona, content injectiona

## Dopuna 2026-07-16 — pairing 422 hotfix

Stvarni klik na Settings dugme „Poveži“ otkrio je integracijski bug koji mock testovi nisu pokrili: `handleBrowserPairingStart()` je unaprijed pozivao `JSON.stringify`, a zajednički `requestJson()` zatim je isti body ponovo serijalizovao. FastAPI je zato primao JSON string umjesto objekta `{"browser_kind":"brave"}` i vraćao HTTP 422.

Codex je uklonio prvi `JSON.stringify`; handler sada predaje običan objekat, a `requestJson` ostaje jedina JSON serialization granica. Verifikacija: `npm run check` i `npm run typecheck` prošli; browser-tabs testovi 42/42; direktni `POST /browser-bridge/pairing-sessions` sa objektnim bodyjem vratio HTTP 200 i pairing sesiju.

## Preostali rad za pi — jednostavan korisnički tok

C0 razvojni `Load unpacked` tok nije prihvatljiv krajnji UX. Pi treba nastaviti sljedećim redom:

1. **Automatsko uparivanje poslije instalacije** — korisnik ne unosi kod, secret ni localhost adresu; ekstenzija sama pronalazi instaliranu aplikaciju i vezuje profil.
2. **Jedno dugme u aplikaciji „Poveži preglednik“** — detektuje browser i otvara odgovarajući službeni store listing. Browserova obavezna potvrda „Dodaj ekstenziju“ je jedina dodatna korisnička radnja.
3. **Native Messaging Host** — installer registruje lokalni host, a objavljena ekstenzija komunicira samo sa dozvoljenim stabilnim extension ID-em. Time se uklanja ručni pairing i zavisnost od WebSocket porta u korisničkom UX-u.
4. **Beta pomoćnik dok store listing nije spreman** — aplikacija otvara `brave://extensions`, kopira stabilnu putanju ekstenzije i prikazuje najviše dva jasna koraka; ovo ostaje development/beta fallback, ne produkcijski tok.
5. **Stvarni Brave smoke gate** — instalirati/povezati ekstenziju, otvoriti najmanje šest tabova i dokazati count/list/activate te confirmation-gated close. Mock testovi nisu dovoljan dokaz.
6. **C1–C4 iz Chromium completion brifa** — multi-profile broker, Chrome/Edge, Vivaldi/Opera/Chromium, store distribucija i hardening.

Potpuno tiha instalacija bez browserove potvrde dozvoljena je samo kroz administratorske enterprise politike; aplikacija to ne smije koristiti kao consumer default.
