# Pi brief — završetak Browser Bridgea za sve Chromium browsere

## Status i cilj

- Status: planirano, nije implementirano.
- Vlasnik: pi agent.
- Datum: 2026-07-16.
- Nastavlja se na završene browser-tabs PR1–PR3.

Cilj je da agent stvarno, end-to-end, može vidjeti, brojati, otvoriti, aktivirati i potvrđeno zatvoriti kartice u svakom podržanom Chromium browseru/profilu koji je korisnik svjesno povezao.

Primjeri koji moraju raditi:

- „Koliko kartica imam u Braveu?“
- „Otvori petu karticu u Edgeu.“
- „Otvori YouTube kao novu karticu u Chrome profilu Posao.“
- „Koji Chromium browseri su povezani?“
- „Zatvori treću karticu u Vivaldiju.“ — uz postojeću potvrdu.

Agent ne smije tvrditi da vidi tabove ako ekstenzija nije povezana.

## Potvrđeni trenutni problem

PR1–PR3 imaju 41 automatizovani test, ali testovi koriste lažni/mokovani extension klijent. Na stvarnom računaru je potvrđeno:

- Ricky Browser Bridge nije instaliran u Braveu;
- nema aktivne WebSocket veze na `127.0.0.1:9119`;
- extension options traži puni pairing secret;
- backend `/browser-bridge/status` vraća samo prvih 8 znakova (`pairing_display`);
- Settings nema Browser Bridge sekciju ni pairing/install tok;
- broker čuva samo jedan `_active_ws`, pa posljednji povezani browser/profil zamjenjuje prethodni;
- tool contract ima browser naziv, ali nema stabilni connection/profile identitet;
- produkcijski packaging i pravi browser smoke test nisu završeni.

Zaključak: unutrašnja tool logika postoji, ali stvarni browser nema završen instalacijski, pairing i routing put.

## Podržani browseri

### Tier 1 — obavezno testirati i podržati

- Google Chrome
- Microsoft Edge
- Brave

### Tier 2 — ista ekstenzija, obavezna detekcija i najmanje jedan stvarni smoke test

- Vivaldi
- Opera
- Opera GX
- Chromium

### Van ovog paketa

- Firefox/Safari — nisu Chromium i zahtijevaju zaseban compatibility paket.
- Android/iOS browseri.
- Cloud sinhronizacija tabova između računara.

Generički Chromium fork može koristiti ručni install/pair tok, ali se ne smije reklamirati kao verifikovan dok ne prođe compatibility smoke test.

## Važno ograničenje instalacije

Consumer Chromium browseri uglavnom ne dozvoljavaju desktop aplikaciji da tiho instalira ekstenziju bez korisnikove akcije. Ne zaobilaziti tu zaštitu registry/policy trikovima.

Produkcijski tok treba biti:

1. Settings detektuje instalirane browsere.
2. Korisnik klikne „Poveži“ za konkretan browser/profil.
3. Aplikacija otvara odgovarajući store listing ili dokumentovani manual install ekran.
4. Korisnik eksplicitno instalira/omogući ekstenziju.
5. Jednokratni pairing povezuje upravo taj browser profil.
6. Settings potvrđuje stvarnu autentifikovanu WebSocket vezu.

Za razvoj je dozvoljen „Load unpacked“, jasno označen kao development-only. Za produkciju pripremiti Chrome Web Store listing; provjeriti može li isti listing koristiti Brave/Vivaldi/Opera. Za Edge preferirati Edge Add-ons listing ili dokumentovani Chrome Web Store tok. Enterprise policy deployment može biti zaseban administratorski dodatak, nikad default za običnog korisnika.

## Arhitektura: multi-connection registry

Zamijeniti single-connection broker registrom više istovremenih konekcija:

```text
BrowserExtensionBroker
  connections:
    connection_id -> BrowserConnection
      browser_kind
      profile_id
      profile_label
      installation_id
      websocket
      authenticated_at
      last_seen_at
      active_window_id
      extension_version
      capabilities
```

Svaka instalacija ekstenzije generiše i trajno čuva nasumični `installation_id`. Backend nakon pairinga izdaje zaseban credential vezan za tu instalaciju. Ne koristiti jedan globalni secret za sve profile.

Obavezna pravila:

- jedan browser profil = jedan `installation_id` + jedan backend `profile_id`;
- istovremeno mogu biti povezani Brave Default, Chrome Posao i Edge Personal;
- reconnect zamjenjuje samo staru vezu istog `installation_id`, ne druge browsere;
- snapshot sadrži `connection_id/profile_id` i nikad se ne može upotrijebiti na drugoj vezi;
- pending request mapa mora biti scoped po connection ID-u;
- disconnect jedne veze prekida samo njene requestove;
- heartbeat/last_seen određuje online status;
- ne oslanjati se na „posljednji povezani browser“.

## Sigurno uparivanje

Ne izlagati dugotrajni broker secret u React DOM-u niti tražiti korisniku da otvara lokalni secret fajl.

Preporučeni tok:

1. Settings pozove zaštićeni backend endpoint `POST /browser-bridge/pairing-sessions` sa očekivanim `browser_kind` i opcionim labelom profila.
2. Backend generiše jednokratni kriptografski token sa TTL-om 5 minuta i statusom `pending`.
3. Settings prikazuje kratki korisnički kod i dugme „Kopiraj jednokratni kod“; puni dugotrajni credential se nikad ne prikazuje.
4. Ekstenzija šalje `pair` poruku sa jednokratnim tokenom, svojim `installation_id`, browser identitetom, profil labelom i verzijom.
5. Backend atomarno potroši token, registruje profil i vrati per-install credential.
6. Ekstenzija čuva credential u `chrome.storage.local`; sljedeće konekcije koriste challenge/response ili siguran auth handshake.
7. Settings dobije status `paired/connected` i više ne prikazuje token.

Sigurnosni zahtjevi:

- token jednokratan, vremenski ograničen i vezan za očekivani browser;
- per-profile credential se može opozvati i rotirati;
- poređenje secreta constant-time;
- loopback-only WebSocket;
- rate limit za pairing pokušaje;
- audit događaji bez secreta, punog URL-a ili osjetljivog naslova taba;
- revoke endpoint odmah zatvara konkretnu WebSocket vezu;
- extension handshake prijavljuje verziju i capabilities;
- backend odbija nepodržanu/staru verziju preciznim kodom;
- ne vjerovati proizvoljnom `profile_label`; tretirati ga samo kao korisnički prikazni tekst.

## Browser i profil identitet

Ekstenzija ne može uvijek savršeno zaključiti fork samo iz Chromium API-ja. Koristiti kombinaciju:

- browser iz korisnikovog eksplicitnog Settings install/pair toka;
- kratkotrajni pairing token vezan za očekivani `browser_kind`;
- user-agent brand samo kao signal/provjeru, ne kao jedini izvor istine;
- stabilni extension `installation_id` za identitet instalacije;
- korisnički `profile_label` poput „Default“, „Posao“ ili „Lični“.

Podržani canonical enum:

```text
chrome | edge | brave | vivaldi | opera | opera_gx | chromium
```

Jezički aliasi najmanje:

```text
brejv -> brave
edž -> edge
hrom / chrome -> chrome
opera gx / opera ge-iks -> opera_gx
vivaldi -> vivaldi
```

Alias logiku držati centralno u Pythonu i testirati; Realtime opis treba modelu objasniti najčešće fonetske oblike.

## Detekcija instaliranih browsera na Windowsu

Dodati Python read-only browser discovery servis. Preferirati App Paths registry ključeve i uninstall metadata, zatim poznate putanje kao fallback.

Poznati profili se mogu otkriti samo po direktorijima, bez čitanja history/cookies sadržaja:

- Chrome: `%LOCALAPPDATA%/Google/Chrome/User Data`
- Edge: `%LOCALAPPDATA%/Microsoft/Edge/User Data`
- Brave: `%LOCALAPPDATA%/BraveSoftware/Brave-Browser/User Data`
- Vivaldi: `%LOCALAPPDATA%/Vivaldi/User Data`
- Chromium: `%LOCALAPPDATA%/Chromium/User Data`
- Opera: `%APPDATA%/Opera Software/Opera Stable`
- Opera GX: `%APPDATA%/Opera Software/Opera GX Stable`

Discovery rezultat ne znači da je ekstenzija instalirana. Statusi moraju biti odvojeni:

```text
not_installed | browser_detected | extension_not_connected | pairing | connected | incompatible | revoked
```

Ne pokušavati zaključiti live connection samo pregledom `Extensions` foldera; autoritativan dokaz je uspješan autentifikovan handshake.

## Settings GUI

U postojeći `SettingsPanel` dodati sekciju „Browseri i kartice“.

Za svaki browser/profil prikazati:

- ikonu i canonical naziv browsera;
- profil label;
- browser instaliran: da/ne;
- ekstenzija povezana: da/ne;
- posljednje viđeno;
- extension verziju;
- dugmad `Poveži`, `Ponovo poveži`, `Preimenuj profil`, `Opozovi`;
- development-only `Load unpacked` upute iza eksplicitnog dev flag-a;
- jasan tekst da agent vidi samo title/URL tab metadata, ne sadržaj stranice.

Nikad ne prikazivati sirovi dugotrajni credential. Pairing status poll koristiti samo dok je pairing ekran otvoren; live status može koristiti postojeći backend polling obrazac sa razumnim intervalom.

Potrebni Electron preload/IPC pozivi trebaju biti imenovani i allowlistovani. Electron ostaje tanak transport; discovery, pairing i registry poslovna logika pripada Pythonu. Ne dodavati je u `electron/main.cjs`.

## Backend API

Predloženi zaštićeni endpointi:

```text
GET    /browser-bridge/browsers
GET    /browser-bridge/connections
POST   /browser-bridge/pairing-sessions
GET    /browser-bridge/pairing-sessions/{id}
DELETE /browser-bridge/pairing-sessions/{id}
POST   /browser-bridge/connections/{profile_id}/revoke
PATCH  /browser-bridge/connections/{profile_id}
```

WebSocket ostaje na `/browser-bridge`, ali handshake mora podržati `pair` i `auth` protokole sa verzijom protokola.

Status API više ne treba vraćati `pairing_display` od globalnog secreta. Zadržati privremenu kompatibilnost samo ako je potrebna migracija već uparenog development profila; nakon migracije ukloniti legacy global-secret tok.

## Tool contract i routing

Proširiti tool contracte da podrže tačan profil:

```json
{
  "browser": "brave",
  "profile_id": "optional-stable-id",
  "scope": "current_window",
  "action": "list"
}
```

Snapshot rezultat mora sadržati:

```json
{
  "browser": "brave",
  "profile_id": "profile-...",
  "profile_label": "Default",
  "connection_id": "conn-...",
  "snapshot_id": "tabsnap-...",
  "count": 6
}
```

Routing pravila:

1. Ako korisnik navede browser i profil, koristi tačno njih.
2. Ako navede browser sa samo jednim povezanim profilom, koristi njega.
3. Ako više profila istog browsera odgovara, pitaj koji.
4. Ako ne navede browser, preferiraj jedinu vezu koja prijavljuje fokusiran aktivni window.
5. Ako fokus nije jednoznačan, pitaj korisnika; ne biraj posljednju konekciju.
6. `snapshot_id` je trajno vezan za profile/connection i ordinalna akcija mora biti odbijena na mismatch.
7. Na disconnect vratiti `BROWSER_PROFILE_NOT_CONNECTED`, sa dostupnim profilima, bez keyboard fallbacka.

## Otvaranje nove kartice

Postojeći `browser_open` pokreće executable/URL, ali ne može precizno birati već povezani profil. Dodati poseban `browser_tab_open` alat ili pažljivo proširiti contract tako da extension otvori tab u tačno odabranom profilu.

Preporuka: zaseban `browser_tab_open` medium-risk alat:

```json
{
  "browser": "edge",
  "profile_id": "profile-work",
  "url": "https://example.com",
  "activate": true
}
```

Pravila:

- model-controlled URL ostaje apsolutni HTTP(S), bez credentials;
- prazan novi tab je eksplicitna opcija koju backend interno mapira, ne proizvoljan scheme;
- extension koristi `chrome.tabs.create` samo sa validiranim parametrima;
- rezultat vraća tab ID/title/URL/profile;
- ako nema povezane ekstenzije, može se ponuditi postojeći `browser_open` kao manje precizan fallback samo nakon jasnog objašnjenja da profil nije garantovan;
- ne koristiti content scripts niti arbitrary JavaScript.

## Postojeće list/activate/close ponašanje

- `browser_tabs(list/activate)` ostaje medium-risk i zahtijeva Computer Mode.
- `browser_tab_close` ostaje poseban high-risk confirmation tool.
- Confirmation payload za close mora uključiti `profile_id`, `snapshot_id`, position i stabilni tab ID/origin binding.
- Approval retry mora koristiti istu profile konekciju; disconnect/reconnect ili snapshot promjena vraća stale/mismatch grešku.
- Jedna potvrda nikad ne smije zatvoriti tab u drugom browseru/profilu.
- Incognito ostaje zabranjen u prvom produkcijskom izdanju za sve browsere.

## Strukturisane greške

Najmanje:

- `NO_CHROMIUM_BROWSER_DETECTED`
- `BROWSER_NOT_SUPPORTED`
- `EXTENSION_NOT_INSTALLED`
- `BROWSER_EXTENSION_NOT_CONNECTED`
- `BROWSER_PROFILE_NOT_CONNECTED`
- `BROWSER_PROFILE_AMBIGUOUS`
- `PAIRING_TOKEN_EXPIRED`
- `PAIRING_TOKEN_USED`
- `PAIRING_BROWSER_MISMATCH`
- `BROWSER_EXTENSION_AUTH_FAILED`
- `BROWSER_EXTENSION_VERSION_UNSUPPORTED`
- `BROWSER_CONNECTION_REPLACED`
- `TAB_PROFILE_MISMATCH`
- postojeći `TAB_SNAPSHOT_STALE`, `TAB_POSITION_OUT_OF_RANGE`, `INCOGNITO_NOT_ALLOWED`.

Svaka korisnička poruka mora navesti sljedeći korak, npr. „Brave je pronađen, ali Ricky ekstenzija nije povezana. Otvorite Settings → Browseri i kartice → Brave → Poveži.“

## Predložene implementacijske faze

### C0 — live bug fix: instalacija i pairing jednog Brave profila

- Settings Browser Bridge sekcija.
- Jednokratni pairing token umjesto kopiranja globalnog secreta.
- Vođeni `Load unpacked` development tok.
- Stvarni Brave list/count/activate smoke test.
- Ovo je prvi gate: ništa dalje ne označavati završeno dok pravi Brave ne radi.

### C1 — multi-connection broker i profile routing

- Connection registry.
- Per-install credential/revoke.
- Snapshot/profile binding.
- Tool schemas sa `profile_id`.
- Dva istovremena browser profila u integration testu.

### C2 — Chrome, Edge i nova kartica

- Browser discovery za Tier 1.
- Guided install/pair za Chrome i Edge.
- `browser_tab_open` u precizno odabranom profilu.
- Stvarni E2E matrix: Brave + Chrome + Edge.

### C3 — Vivaldi, Opera, Opera GX i Chromium

- Discovery adapteri i canonical aliasi.
- Compatibility provjera iste MV3 ekstenzije.
- Najmanje jedan stvarni smoke test po browser porodici; ako browser nije instaliran na dev računaru, dokumentovati reproduktivan ručni test i ne tvrditi „verifikovano“.

### C4 — produkcijska distribucija i hardening

- Stabilan extension ID/build.
- Chrome Web Store/Edge Add-ons publishing plan.
- Produkcijski installer/Settings linkovi.
- Protocol version migration.
- Credential storage/revocation audit.
- Privacy i multi-profile red-team testovi.

Svaka faza je mali commit/PR sa trackerom i agent reportom. Ne raditi veliki rewrite.

## Test plan

### Python unit/integration

- dva/tri istovremena autentifikovana fake extension klijenta;
- reconnect jednog profila ne prekida drugi;
- request/reply ide samo ciljnoj konekciji;
- snapshot se ne može koristiti na drugom profilu;
- pairing token TTL/single-use/browser binding;
- revoke prekida samo ciljnu vezu;
- browser discovery mapira standardne Windows instalacije;
- aliasi za Brave/Edge/Chrome/Opera GX;
- ambiguous profile vraća preciznu grešku;
- `browser_tab_open` URL validacija;
- close confirmation hash uključuje profile identitet;
- credential/URL/title redaction u logovima.

### Extension testovi

- stabilni `installation_id` preživljava restart service workera;
- pair/auth/version handshake;
- credential se ne ispisuje u console log;
- list/activate/open/close koriste samo dozvoljene Chrome API-je;
- request ID deduplikacija je per connection;
- reconnect backoff se resetuje nakon uspješne autentifikacije, ne samo TCP opena;
- auth failure ne prikazuje lažni `connected` status;
- incognito je `not_allowed`.

### Renderer/Electron

- Settings stanja za detected/not connected/pairing/connected/revoked;
- pairing token se uklanja iz UI-a nakon uspjeha/isteka;
- preload/IPC contract typecheck;
- model tool schema parity sa Python katalogom;
- nema browser poslovne logike u `electron/main.cjs`.

### Obavezni stvarni E2E smoke matrix

Za svaki dostupni Tier 1 browser:

1. Instalirati/povezati ekstenziju kroz Settings.
2. Otvoriti najmanje šest poznatih tabova.
3. Agent tačno odgovara na count.
4. Aktivira prvi, peti i posljednji tab.
5. Otvara URL kao novu karticu u pravom browser/profilu.
6. Zatvaranje traži potvrdu i zatvara samo vezani tab.
7. Promjena redoslijeda prije approvala vraća stale grešku.
8. Gašenje browsera mijenja status u disconnected.
9. Ponovno pokretanje automatski autentifikuje isti profil.
10. Istovremeno povezati dva browsera i dokazati da naredbe ne odlaze pogrešnom.

Rezultate zapisati u agent report kao tabelu browser/verzija/profile/scenario/pass-fail. Mock testovi se ne smiju predstavljati kao live E2E dokaz.

## Acceptance kriteriji

- Settings detektuje instalirane Chromium browsere i jasno razlikuje instaliran browser od povezane ekstenzije.
- Korisnik može bez otvaranja secret fajla sigurno upariti svaki željeni profil.
- Najmanje Brave, Chrome i Edge rade live end-to-end.
- Broker podržava više istovremenih browser/profil veza.
- Agent tačno rutira list/count/activate/open/close prema browseru i profilu.
- Nejasan izbor rezultira pitanjem, ne nasumičnim routingom.
- Snapshot i confirmation se ne mogu prenijeti između profila.
- Browser disconnect se korisniku saopštava iskreno.
- Nema silent extension instalacije, arbitrary shella, content injectiona ni čitanja sadržaja stranice.
- Python/JS testovi, `npm run test:voice`, `npm run check`, `npm run typecheck`, `npm run build` i stvarni browser smoke matrix prolaze.
- Tracker i agent report se ažuriraju u istom commitu.

## Predloženi fajlovi za pregled/izmjenu

Pi agent mora potvrditi tačan blast radius prije rada. Očekivani moduli:

- `python_backend/app/services/browser_extension_broker.py`
- novi `python_backend/app/services/chromium_discovery.py`
- `python_backend/app/api/browser_bridge.py`
- `python_backend/app/schemas/browser_tabs.py`
- `python_backend/app/tools/system/browser_tabs.py`
- `python_backend/app/agent/tool_catalog/phase13.py`
- `browser_extension/manifest.json`
- `browser_extension/service-worker.js`
- `browser_extension/options.*`
- `src/components/pixel/SettingsPanel.tsx` ili izdvojena `BrowserConnectionsSettings.tsx`
- `electron/preload.cjs` i `src/vite-env.d.ts` samo za named bridge contracte
- `electron/core/realtimeToolSpecs.cjs`
- relevantni Python/Vitest/extension testovi
- packaging/store dokumentacija.

## Šta pi agent ne smije uraditi

- Ne dodavati poslovnu logiku u `electron/main.cjs`.
- Ne pokušavati tihu instalaciju ekstenzije za obične korisnike.
- Ne prikazivati globalni dugotrajni secret u GUI-u.
- Ne koristiti jedan credential za sve profile.
- Ne usmjeravati komandu na posljednju povezanu ekstenziju.
- Ne koristiti keyboard shortcuts kao lažni fallback za count/list.
- Ne čitati page DOM, cookies, passwords, history ili sadržaj stranice.
- Ne tvrditi da je browser podržan samo zato što mock test prolazi.

## Obavezna procedura za pi agenta

1. Provjeriti `git status`, `git log`, tracker i aktuelni PR3 diff.
2. Ne pokupiti postojeće nepovezane izmjene iz zajedničkog worktreea.
3. Osvježiti GitNexus indeks; ako FTS ostane degradiran, dokumentovati i ručno provjeriti call siteove.
4. Pokrenuti impact analysis prije izmjene svakog postojećeg simbola; prijaviti HIGH/CRITICAL prije rada.
5. Raditi C0–C4 redom, u malim commitima.
6. Prije svakog commita pokrenuti relevantne testove i `gitnexus_detect_changes`.
7. Napisati `agent_reports/` izvještaj i ažurirati `docs/MIGRATION_PLAN.md` u istom commitu.
8. Ne commitovati bez eksplicitnog korisničkog zahtjeva.
