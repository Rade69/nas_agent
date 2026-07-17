# Agent Report — Browser Bridge: pet problema koja su blokirala pairing/upotrebljivost (port, orphaned init(), auth gate na WS ruti, in-memory credential, persist-crash na live konekciji)

- **Datum:** 2026-07-16
- **Agent:** Claude Code
- **Scope:** `browser_extension/service-worker.js`, `browser_extension/options.js`, `browser_extension/options.html`, `python_backend/app/main.py`, `python_backend/app/storage/db.py`, `python_backend/app/storage/repositories/browser_bridge_credential_repo.py` (novo), `python_backend/app/services/browser_extension_broker.py`

## Četvrti problem (korisnički zahtjev nakon uspješnog pairing-a): credential se gubio na svaki restart

Nakon uspješnog pairing-a (treći fix), korisnik je potvrdio da agent može
brojati i otvarati kartice — ali je prijavio da se sve gubi čim se
aplikacija/Brave zatvore, što je ocijenio "nepraktičnim i zamornim".
Uzrok: `InstallCredential` je bio namjerno **samo u memoriji**
(`docs/BROWSER_BRIDGE_PUBLISHING.md`: "InstallCredential — in-memory samo...
Ekstenzija se mora ponovo autentifikovati nakon restarta backend-a") — svaki
restart Python procesa brisao je sve upar ene kredencijale, tjerajući
korisnika da ponovi cijeli pairing ritual.

Ovo je bila namjerna arhitektonska odluka iz C0 faze (vjerovatno iz
sigurnosnih razloga — izbjeći trajno čuvanje pairing kredencijala na disku),
pa **nisam samoinicijativno mijenjao** — eksplicitno pitao korisnika
(`AskUserQuestion`) da li da se kredencijal trajno sačuva. Korisnik je
potvrdio: da, sačuvaj trajno (SQLite, isti obrazac kao ostalo stanje appa).

**Implementacija:**

- Nova tabela `browser_bridge_credentials` (`app/storage/db.py`) — isti
  `CREATE TABLE IF NOT EXISTS` obrazac kao ostale tabele.
- Nova `BrowserBridgeCredentialRepository`
  (`app/storage/repositories/browser_bridge_credential_repo.py`) — isti
  obrazac kao `ThumbnailReferenceRepository` (`connect()` context manager,
  `upsert`/`list`).
- `BrowserExtensionBroker.__init__` prima **opcioni** `database_path: Path | None = None`
  (default `None` — čuva povratnu kompatibilnost sa svih 13 direktnih
  `BrowserExtensionBroker(tmp_path)` poziva u `tests/test_browser_tabs.py`,
  koji ostaju in-memory-only, bez izmjene). Kad je dat, konstruktor učitava
  sve persistovane kredencijale u `_install_credentials` na startu
  (`_load_persisted_credentials`).
- `_persist_credential(install)` — no-op ako repo nije konfigurisan; inače
  upsert. Pozvan na sva četiri mjesta gdje se `InstallCredential` mijenja:
  nakon uspješnog pairing-a (`_consume_pairing_token`), nakon svake
  (re)konekcije/auth-a (`_register_connection` — ažurira `last_seen_at`),
  na revoke (`revoke_connection`), na preimenovanje (`rename_profile`).
- `init_broker(data_dir, database_path=None)` i `main.py`'s
  `init_broker(settings.data_dir, settings.database_path)` — produkcijski
  put sad prosljeđuje pravu putanju; `initialize_database(settings)` se
  poziva PRIJE `init_broker` u `create_app()`, pa tabela postoji na vrijeme.

GitNexus impact prije izmjene: `init_broker` upstream — LOW, 1 direktan
pozivalac (`create_app`), potvrđeno da nijedan test ne poziva `init_broker`
direktno (samo `BrowserExtensionBroker` konstruktor, koji ostaje
kompatibilan zbog opcionog parametra).

**Verifikacija (uživo, ne samo statička):**

1. Izolovan unit-nivo test (privremeni skript): pairing preko
   `_consume_pairing_token` na "broker 1" instanci → novi "broker 2" (ista
   SQLite putanja, simulira restart) učitava identičan kredencijal iz baze
   — PASSED.
2. **Pun end-to-end test preko stvarnog uvicorn servera** (izolovana test
   instanca na portu 18765, `python_backend/data` — potpuno odvojeno od
   korisnikovog pravog `RICKY_DATA_DIR`, netaknuto): kreirana prava pairing
   sesija preko HTTP API-ja, pravi WebSocket `pair` handshake, sačuvan
   vraćeni credential; server **ugašen i pokrenut NOV proces** (drugačiji
   PID, potvrđeno); novi WebSocket `auth` poziv sa starim credential-om,
   **bez novog pairing koda** → `{"type": "auth_ok", ...}` sa istim
   `profile_id` — potvrđuje da kredencijal stvarno preživljava restart
   procesa u realnim uslovima.
3. Test artefakti (`dev_local_token.txt`, `ricky.sqlite` u
   `python_backend/data/`) obrisani nakon verifikacije.

Full `pytest` suite ponovo pokrenut nakon ove izmjene: i dalje 380 passed,
ista 2 pred-postojeća nepovezana failure-a.

## Peti korak — debug logovi u ekstenziji

Na korisnikov zahtjev, dodato detaljno logovanje u `pairWithCode()`
(`service-worker.js`) — URL koji se koristi, `ws.onopen`/`onmessage`/
`onclose` (sa close code/reason/wasClean — najdijagnostičnije polje za WS
handshake probleme) i `ws.onerror` sa punim event objektom. Ovo je bilo
presudno za pronalazak trećeg (glavnog) uzroka. Logovi su zadržani kao
trajna dijagnostika (ne obrisani nakon fix-a) — konzistentni su sa
postojećim ne-debug logovanjem u `connect()` u istom fajlu, i ne otkrivaju
credential vrijednosti niti drugi osjetljiv sadržaj.

## Treći bag (glavni uzrok — pronađen preko debug logova, HTTP 500 na WS handshake)

Nakon prve dvije popravke, korisnik je dodao debug logging (na moj zahtjev,
`console.log`/`console.error` u `pairWithCode()`) i poslao stvarni browser
konzolni log. Log je pokazao: prvih 6 pokušaja `net::ERR_CONNECTION_REFUSED`
(backend tada nije radio), zatim — kad je backend radio — **`Error during
WebSocket handshake: Unexpected response code: 500`**, sa `ws closed — code:
1006`.

**Pravi uzrok:** `python_backend/app/main.py` registruje
`app = FastAPI(dependencies=[Depends(require_local_token)])` — ovo je
**globalni** dependency koji se primjenjuje na SVE rute registrovane preko
FastAPI-jevog `@app.websocket(...)` dekoratora, uključujući
`/browser-bridge`. `require_local_token`
(`python_backend/app/core/auth.py`) zahtijeva `Authorization: Bearer <token>`
header — ali **browseri strukturalno ne mogu postaviti custom header na
native `WebSocket` handshake** (Web Platform ograničenje, ne bag u
ekstenziji). Ekstenzija ima svoj potpuno odvojen auth (one-time pairing
kod + per-install credential, implementiran u
`BrowserExtensionBroker.handle_ws()`) — upravo zato što ne može zadovoljiti
Electron-only lokalni token. Kad je `authorization` header uvijek `None`,
`require_local_token` baca `AppError(..., status_code=401)` tokom
dependency-resolution FAZE, PRIJE `websocket.accept()`. `AppError` handler
(`@app.exception_handler(AppError)` u `app/core/errors.py`) je registrovan
za HTTP `Request`/`JSONResponse` — nekompatibilan sa WebSocket ASGI scope-om
— pa Starlette/uvicorn ovo surfacuje kao sirov HTTP 500 tokom upgrade-a,
tačno ono što je browser prijavio.

**Fix:** `/browser-bridge` ruta registrovana preko raw Starlette
`app.router.add_websocket_route("/browser-bridge", browser_bridge_ws)`
umjesto `@app.websocket(...)` dekoratora. Ovaj put NE prolazi kroz
FastAPI-jev dependency-injection sistem (samo `APIWebSocketRoute`, koju
koristi dekorator, gradi `Dependant` iz app-level `dependencies=[...]`) —
plain Starlette `WebSocketRoute` (koju gradi `Router.add_websocket_route`)
nema pojma o FastAPI `Depends()`. Nula izmjena na `require_local_token` ili
bilo kojoj HTTP ruti — auth gate za sve HTTP rute ostaje identičan.

Verifikovano GitNexus impact (`browser_bridge_ws` upstream: LOW/0 pozivalaca;
`require_local_token` upstream: LOW/0 direktnih — nedirano) prije izmjene.

**Live test** (izolovana test instanca na portu 18765, korisnikova prava
sesija na 8765 netaknuta): raw WebSocket klijent (`websockets` biblioteka)
protiv `/browser-bridge` — handshake sad uspijeva (nema 500), broker vraća
čist `{"type": "pair_failed", "reason": "Invalid or expired pairing code."}`
za namjerno pogrešan test-kod — potvrđuje i da je auth-gate bag riješen I da
broker-ova sopstvena pairing validacija i dalje ispravno fail-closed radi.

Full `pytest` suite: 380 passed, 2 pre-postojeća failure-a (nepovezana,
env-specific — `test_phase16_integrations.py`, potvrđeno identična i BEZ
ove izmjene via `git stash`).

## Dopuna (drugi, nezavisan bag pronađen istog dana)

Nakon prve popravke (port 9119→8765) korisnik je i dalje prijavio da se
polje "Broker URL" uvijek prikazuje prazno, čak i nakon ručnog unosa i
"Save URL" klika. Istraga je otkrila da je `async function init()` u
`options.js` (koja puni `brokerUrlInput.value` iz `chrome.storage.local`
ili default vrijednosti, i pokreće `refreshStatus()` + 2s polling)
**definisana ali nikad pozvana nigdje u fajlu** (potvrđeno grep-om — jedino
poklapanje je sama definicija). Ovo je zaseban, pre-postojeći bag (ne
uzrokovan prvom port-popravkom), koji objašnjava:

- Broker URL polje uvijek prazno pri otvaranju (samo placeholder, nikad
  `.value` iz JS-a).
- Status trajno zaglavljen na "Checking connection..." (hardcoded HTML
  tekst — `refreshStatus()` se nikad ne pokreće da ga ažurira).

Bitno: klik na "Save URL" i dalje ISPRAVNO upisuje u `chrome.storage.local`
(taj event listener je nezavisan od `init()`), pa je ranije ručno uneseni
URL vjerovatno bio sačuvan — UI ga samo nikad nije prikazao natrag.

**Fix:** dodat poziv `init();` na kraj `options.js` (nakon svih
event-listener registracija). `service-worker.js` provjeren i NIJE imao
isti obrazac — ima ispravan top-level auto-start
(`loadStoredState().then(() => connect())` + `onInstalled`/`onStartup`
listeners), netaknut.

Verifikacija: `node --check browser_extension/options.js` → OK.

## GitNexus impact
Nije pokretan formalno (GitNexus ne indeksira `browser_extension/` — čist MV3 JS bez
Python/TS graph veza). Ručna provjera: `getBrokerUrl()` u `service-worker.js` je
jedina funkcija koja koristi default string; pozivaoci su `connect()`/pairing flow
unutar istog fajla. Izmjena je string literal, bez promjene potpisa/ponašanja funkcije.

## Šta je urađeno
Korisnik je prijavio da pairing sa Ricky Browser Bridge ekstenzijom ne uspijeva
(zaglavljeno na "Checking connection... / Reconnecting..."). Istraga (uporedila
stvarni port Python backend-a sa onim koji ekstenzija pokušava kontaktirati)
otkrila je pravi uzrok:

- Python backend sluša na **portu 8765** (`python_backend/app/core/config.py:20`,
  `electron/services/pythonProcess.cjs:15` — oba `DEFAULT_PORT = 8765`), a
  WebSocket endpoint je mountovan na putanji **`/browser-bridge`**
  (`python_backend/app/main.py:172`, `@app.websocket("/browser-bridge")`).
- Ekstenzija je imala hardkodiran fallback/placeholder **`ws://127.0.0.1:9119`**
  (bez `/browser-bridge` putanje, pogrešan port) na tri mjesta:
  `service-worker.js:79` (`getBrokerUrl()`), `options.js:20` (init popunjava
  input polje), `options.html:135` (placeholder atribut).
- Ekstenzija koristi stored/default vrijednost kao **cijeli** WebSocket URL
  bez dodavanja putanje (`new WebSocket(url)` direktno) — potvrđeno u
  `service-worker.js:90-93` i `:178-179` — pa je ispravna vrijednost morala
  uključivati i port i putanju.

Sve tri lokacije ispravljene na `ws://127.0.0.1:8765/browser-bridge`.

## Zašto je urađeno
Bag je blokirao svaki pokušaj uparivanja ekstenzije sa backend-om — ne
korisnička greška, nego pogrešan default koji nikad nije testiran protiv
stvarno pokrenutog Python backend-a tokom C0-C4 browser-bridge rada
(commits `04c88c1`..`d0337a0`).

## Kako je urađeno
- Pronađen stvarni port/putanju čitanjem `config.py`, `pythonProcess.cjs`,
  `main.py` (websocket route).
- Pronađene sve reference na `9119` u repo-u (`Grep`), potvrđeno da postoje
  samo u `browser_extension/` i docs (ne u Python/Electron kodu).
- Tri `Edit` poziva (string-literal zamjena), `node --check` na oba `.js`
  fajla za sintaksnu validaciju.

## Šta nije dirano
- `manifest.json` — `host_permissions: []` je namjerna privacy odluka
  (WebSocket iz service worker-a ne zahtijeva host_permissions u MV3), nije
  uzrok problema, netaknuto.
- Backend port konfiguracija (`config.py`, `pythonProcess.cjs`) — ispravna,
  nije dirana.
- Pairing flow logika, credential storage, protocol versioning — netaknuto.

## Verifikacija
- `node --check browser_extension/service-worker.js` → OK
- `node --check browser_extension/options.js` → OK
- `grep -rn "9119" browser_extension/` → nula rezultata (potvrđeno očišćeno)

## Rizici/ograničenja
- **Runtime nije testiran** (agent nema pristup pokrenutom browseru/ekstenziji).
  Korisnik treba da:
  1. Reload-uje ekstenziju (`brave://extensions` → reload ikonica na Ricky
     Browser Bridge) da MV3 service worker učita novi kod.
  2. Otvori Options ponovo i potvrdi da "Broker URL" polje sada pokazuje
     `ws://127.0.0.1:8765/browser-bridge`.
  3. Ako je stari pairing kod istekao, uzeti svjež kod iz Ricky Settings-a
     i ponovo pokušati "Pair Now".
- Ako korisnik već ima eksplicitno sačuvan (stari, pogrešan) broker URL u
  `chrome.storage.local` (kliknuo "Save URL" ranije sa 9119 vrijednošću),
  novi default se neće primijeniti automatski — potrebno ručno upisati
  ispravan URL i kliknuti "Save URL". Iz screenshot-a nema indikacije da je
  ovo urađeno (nema "✅ URL saved" potvrde vidljive), pa je vjerovatno da
  reload sam rješava.

## Potreban follow-up
- Ako se potvrdi da reload + fresh pairing kod rade — zatvoriti nalaz.
- Razmotriti (budući, ne ovaj PR): backend da javi svoj stvarni port/URL
  ekstenziji kroz sam pairing kod ili handshake, umjesto hardkodiranog
  default stringa u ekstenziji — eliminisalo bi ovu klasu buga trajno ako
  se port ikad promijeni (`RICKY_BACKEND_PORT` env varijabla).

## Šesti problem — perzistencija je mogla rušiti živu konekciju (glavni nalaz nakon uživo testiranja)

Nakon petog fixa (perzistencija), korisnik je prijavio: ekstenzija prikazuje
"Connected", ali app/agent prikazuje "nije povezano" i `browser_tabs` poziv
ne uspijeva. Dodatno: Computer Mode potvrde su nasumične — nekad traži,
nekad ne, a nakon jedne potvrde odmah traži novu za "istu" akciju.

**Analiza:** `_persist_credential()` se poziva sinhrono iznutar
`handle_ws()`-ove poruka-petlje — i na pairing I na SVAKI reconnect/auth
(ne samo prvi put). SQLite fajl istovremeno pišu mnogi drugi dijelovi appa
(voice turns, tool_runs, activity_events, confirmations) bez WAL moda ili
`busy_timeout`-a (provjereno u `db.py` — samo `PRAGMA foreign_keys = ON`).
Privremeno "database is locked" je realno pod stvarnim opterećenjem. Prije
fixa, takav izuzetak bi izašao iz `_persist_credential` → `_register_connection`
→ propagirao kroz `handle_ws`-ov generalni `except Exception: pass` →
`finally: self._remove_connection()` uklanja konekciju iz registra —
**dok ekstenzija i dalje misli da je povezana** (njeno `auth_ok`/`paired`
je ili već primljeno, ili se socket zatvorio i ekstenzija se rekonektuje
u petlji koja korisnik možda ne primijeti u UI-ju odmah). Svaki
`browser_tabs` poziv u tom prozoru puca sa `BROWSER_EXTENSION_NOT_CONNECTED`,
agent pokušava ponovo, a S-2 escalation pravilo (`permission_engine.py`
linije 129-134: `external_content_seen` + medium+ risk/computer-mode →
prisilna potvrda) traži svježu potvrdu za svaki novi pokušaj — ovo
objašnjava OBA prijavljena simptoma jednim uzrokom.

**Fix (primijenjen):** `_persist_credential()` sad hvata `Exception` i samo
loguje upozorenje (`logging.getLogger(__name__).warning(..., exc_info=True)`)
umjesto da propagira — perzistencija (nice-to-have, preživljava restart)
više NIKAD ne može srušiti živu WS sesiju, bez obzira na uzrok greške.

**Razmotreno, NAMJERNO ODLOŽENO:** dodavanje `PRAGMA busy_timeout` u dijeljeni
`connect()` (`app/storage/db.py`) bi smanjilo i samu vjerovatnoću
zaključavanja (ne samo posljedicu), za CIJELU aplikaciju. GitNexus impact
na `connect()`: **CRITICAL**, 45 pozivalaca u svim repozitorijima. Ovo je
prevelik, sistemski zahvat da se radi ad-hoc usred aktivnog debugovanja —
ostaje kao preporučen budući follow-up, ne primijenjeno sada.

Verifikacija: `python -c "import app.main"` → OK, pun `pytest` → 380 passed,
ista 2 pred-postojeća nepovezana failure-a.

**Napomena:** uzrok NIJE potvrđen live stack trace-om (nisam uspio pokrenuti
pravu app instancu iz Bash alata — `electron .` pokrenut tako nema pravi
main-process kontekst, `ipcMain` je undefined). Fix je odbrambeni i
kategorički ispravan bez obzira na tačan mehanizam greške (bilo koji
izuzetak u `_persist_credential` sad je bezopasan), ali pravi uzrok
("database is locked" specifično) ostaje hipoteza dok se ne potvrdi
korisnikovim ponovnim testom nakon restarta.

## Potrebna korisnička potvrda
Da — treba **ponovo restartovati aplikaciju** (Python kod se ne učitava
dinamički) i potvrditi: (1) da `browser_tabs` sad radi bez
"nije povezano" nesklada, (2) da se Computer Mode potvrde više ne
ponavljaju nepotrebno za istu radnju.
