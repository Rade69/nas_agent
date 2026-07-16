# Pi brief — pouzdano upravljanje Brave/Chrome tabovima

## Status i vlasnik

- Status: PR 1, PR 2 i funkcionalni PR 3 implementirani od pi agenta 2026-07-15.
- Preostali follow-up: produkcijski packaging/auto-instalacija ekstenzije i ručni smoke test sa stvarnim browserom.
- Datum brifa: 2026-07-15.
- Vezano za postojeći `browser_open`, ali je zaseban, mali paket rada.

## Korisnički cilj

Agent treba pouzdano razumjeti i izvršiti zahtjeve kao što su:

- „Koliko tabova imam otvorenih?“
- „Koji je prvi/peti tab?“
- „Otvori peti tab“ — ovdje „otvori“ znači aktiviraj već otvoreni tab.
- „Pređi na prvi tab.“
- „Zatvori treći tab.“
- „Otvori YouTube u novom tabu u Braveu.“

Agent ne smije nagađati broj, redoslijed ili naslov tabova. Prvo mora dobiti stvarno stanje browsera, a zatim djelovati nad tim stanjem.

## Trenutno stanje, provjereno u kodu

- `python_backend/app/tools/system/browser.py` implementira sigurni `browser_open`: otvara default/Brave/Chrome/Edge/Firefox i opcioni HTTP(S) URL. Prihvata `brave` i fonetski `brejv`, ali nema pristup postojećim tabovima.
- `python_backend/app/agent/tool_catalog/phase13.py` registruje Python alate i njihove JSON sheme.
- `electron/core/realtimeToolSpecs.cjs` izlaže Realtime modelu tool contracte.
- `electron/main.cjs` delegira odabrane alate Python backendu. Ne dodavati novu browser poslovnu logiku u ovaj fajl.
- `ToolExecutor.execute()` radi validaciju, Computer Mode/permission provjere, confirmation provjere, izvršenje i standardizovane greške.
- Post-approval bridge već vraća rezultat retryja aktivnoj Realtime sesiji; novi destruktivni tab alat treba koristiti taj postojeći tok, ne praviti paralelni confirmation sistem.

GitNexus napomena: konceptualni query je upozorio da FTS indeks treba osvježiti, ali direktni kontekst je potvrdio navedeni execution path. Prije implementacije pokrenuti `npx gitnexus analyze` ako indeks i dalje prijavljuje degradaciju.

## Zašto prečice nisu prihvatljivo glavno rješenje

`Ctrl+1`, `Ctrl+5`, `Ctrl+Tab` i UI Automation mogu povremeno aktivirati tab, ali ne daju pouzdanu listu, broj, URL, prozor ni stabilan identitet taba. Fokus može biti u drugoj aplikaciji, redoslijed se može promijeniti, a `Ctrl+9` ima posebno značenje. Takav pristup može ostati samo eksplicitno označen fallback za aktiviranje kada ekstenzija nije dostupna; ne smije tvrditi da zna koliko tabova postoji.

## Preporučena arhitektura

Koristiti malu Manifest V3 ekstenziju kompatibilnu sa Braveom i Chromeom. Ekstenzija je jedini sloj koji poziva `chrome.tabs`/`chrome.windows`; Python ostaje vlasnik agent alata, snapshotova, autorizacije, validacije i audit logike.

```text
Realtime model
  -> Electron tool bridge (tanak transport)
  -> Python browser_tabs alat / broker
  -> autentifikovani localhost WebSocket
  -> Brave/Chrome MV3 ekstenzija
  -> chrome.tabs + chrome.windows
```

Ne koristiti Chrome DevTools Protocol kao primarno rješenje: zahtijeva browser pokrenut sa remote-debugging opcijama i često poseban profil, pa ne upravlja pouzdano korisnikovom već otvorenom običnom sesijom.

## Transport i uparivanje

Implementirati lokalni WebSocket broker u Python backendu, vezan isključivo na `127.0.0.1`. Ekstenzija se povezuje kao klijent.

Minimalni sigurnosni zahtjevi:

- slučajni per-install pairing secret, najmanje 256 bita;
- jednokratni kod ili eksplicitni pairing korak u Settings/ekstenziji; bez hardkodovanog tokena;
- secret čuvati u postojećem sigurnom lokalnom storage obrascu, a u ekstenziji u `chrome.storage.local`;
- autentifikovan handshake prije bilo koje komande;
- provjeriti extension identity/origin gdje je dostupno i odbiti nepoznate klijente;
- samo loopback bind, bez `0.0.0.0`, LAN pristupa ili cloud releja;
- request ID, timeout, maksimalna veličina poruke i stroga JSON schema validacija;
- nikada ne slati shell komande niti proizvoljan JavaScript ekstenziji;
- ne logovati pairing secret; URL/title u audit logu redigovati prema postojećoj privacy politici;
- reconnect sa ograničenim backoffom; jedan aktivni browser connection po `browser_profile_id`.

Ako pouzdano i bezbjedno uparivanje ne može stati u prvi mali PR, podijeliti rad na transport/pairing PR i tool-contract PR. Ne spuštati sigurnost radi bržeg demoa.

## Dozvole ekstenzije

Tražiti najmanji skup dozvola:

- `tabs` za listu naslova/URL-ova i aktiviranje/zatvaranje;
- `storage` za pairing podatke;
- host pristup samo loopback WebSocket endpointu ako ga browser zahtijeva.

Ne dodavati content scripts, `<all_urls>`, čitanje sadržaja stranice, history, bookmarks, cookies ili downloads. Ovaj paket upravlja metapodacima tabova, ne sadržajem web stranice. Incognito tabove isključiti po defaultu; ako korisnik posebno omogući ekstenziju u incognito režimu, rezultat mora jasno označiti `incognito: true`.

## Python model podataka i snapshot pravilo

Lista tabova mora vratiti nepromjenjivi kratkotrajni snapshot. Redni broj je 1-based jer korisnik kaže „prvi“, „peti“.

Predloženi rezultat liste:

```json
{
  "browser": "brave",
  "scope": "current_window",
  "window_id": "w-17",
  "snapshot_id": "tabsnap-...",
  "created_at": "2026-07-15T...Z",
  "count": 6,
  "tabs": [
    {
      "position": 1,
      "tab_id": "t-101",
      "title": "YouTube",
      "url": "https://www.youtube.com/",
      "active": false,
      "pinned": false,
      "audible": false,
      "incognito": false
    }
  ]
}
```

Za aktiviranje ili zatvaranje koristiti `snapshot_id` + `position`, a interno razriješiti stabilni `tab_id`. Snapshot treba imati kratak TTL, npr. 10 sekundi. Ako se tab zatvorio, premjestio ili je snapshot istekao, vratiti `TAB_SNAPSHOT_STALE` i novu listu/sugestiju; nikada ne izvršiti akciju nad tabom koji je sada slučajno zauzeo isti redni broj.

Default scope je trenutni browser prozor. Za sve prozore zahtijevati eksplicitni `scope="all_windows"` i u rezultatu grupisati po prozoru. Redoslijed mora odgovarati browserovom stvarnom `index` poretku, uključujući pinned tabove.

## Tool contract

Preferirati jedan koherentan Python alat `browser_tabs`, umjesto mnogo skoro identičnih modelskih alata:

```json
{
  "action": "list | activate | close",
  "browser": "brave | brejv | chrome",
  "scope": "current_window | all_windows",
  "snapshot_id": "required for activate/close",
  "position": 1
}
```

Pravila:

- `list`: vraća broj i sanitizovanu listu; `position` i `snapshot_id` nisu dozvoljeni.
- `activate`: zahtijeva snapshot i 1-based position; fokusira odgovarajući window pa tab.
- `close`: zahtijeva snapshot i position; ne smije zatvoriti browser prozor greškom kada je to posljednji tab bez jasne potvrde/politike.
- `browser="brejv"` normalizovati na `brave`, isto kao u `browser_open`.
- Otvaranje novog URL taba ostaje u `browser_open`; po potrebi proširiti njegov rezultat sa `disposition="new_tab"`, ali ne duplirati URL validaciju u ekstenziji.
- Za „otvori novi prazan tab“ `browser_open` može poslati `about:blank` samo kao interno generisanu vrijednost; model-controlled URL ostaje HTTP(S)-only.

Ako se tokom implementacije pokaže da jedna action schema loše radi sa Realtime validacijom, dozvoljena je podjela na `browser_tabs_list`, `browser_tab_activate` i `browser_tab_close`, uz isti Python broker i ista snapshot pravila. Odluku dokumentovati u agent reportu.

## Rizik i potvrde

Predložena klasifikacija:

- listanje tabova: `medium` zbog izlaganja naslova i URL-ova; zahtijeva Computer Mode, bez confirmation popupa;
- aktiviranje taba: `medium`; zahtijeva Computer Mode, bez confirmation popupa;
- zatvaranje taba: `high`; zahtijeva eksplicitnu confirmation provjeru i koristi postojeći approval/retry bridge;
- otvaranje novog URL-a: ostaje postojeći `browser_open` medium-risk tok.

Confirmation payload za close mora uključiti snapshot/tab identitet, title i origin, tako da odobrenje bude vezano za tačno onaj tab. Ako snapshot zastari prije odobrenja, retry mora vratiti `TAB_SNAPSHOT_STALE`, ne zatvoriti drugi tab.

## Modelske instrukcije i jezička pravila

U `electron/core/realtimeToolSpecs.cjs` i Python katalogu jasno navesti:

- „otvori peti tab“ znači aktiviraj postojeći tab na poziciji 5, ne kreiraj novi;
- prije ordinalne akcije uvijek pozvati `list`, osim ako postoji još važeći snapshot iz neposredno prethodnog tool rezultata;
- nikada ne izmišljati broj/nazive tabova;
- ako korisnik kaže „Brejv“, koristiti Brave;
- ako ima više browser prozora i korisnik nije rekao koji, prvo koristiti trenutni aktivni Brave/Chrome prozor; ako nema jasnog aktivnog prozora, pitati;
- nakon uspjeha reći precizno: „Aktivirao sam peti tab: YouTube.“;
- na `BROWSER_EXTENSION_NOT_CONNECTED` objasniti da ekstenzija nije povezana, bez pokušaja nasumičnih prečica;
- na `TAB_SNAPSHOT_STALE` ponovo listati i tražiti razjašnjenje samo ako se cilj više ne može jednoznačno povezati.

## Kod i predloženi fajlovi

Tačne lokacije agent treba potvrditi nakon svježeg pregleda stabla i GitNexus impact analize. Predložena organizacija:

- `browser_extension/manifest.json`
- `browser_extension/service-worker.js`
- `browser_extension/options.html` / `options.js` za pairing status
- `python_backend/app/tools/system/browser_tabs.py`
- `python_backend/app/services/browser_extension_broker.py`
- `python_backend/app/schemas/browser_tabs.py`
- registracija u `python_backend/app/agent/tool_catalog/phase13.py`
- Realtime schema u `electron/core/realtimeToolSpecs.cjs`
- samo minimalna delegacija/allowlist u Electron shellu; bez nove poslovne logike u `electron/main.cjs`
- backend testovi i JS testovi za schema parity
- instalacijska dokumentacija za Brave/Chrome ekstenziju i pairing

Ako installer treba automatski instalirati/registrirati ekstenziju, tretirati to kao poseban follow-up. Prvi paket može koristiti dokumentovan „Load unpacked“ postupak, ali acceptance test mora jasno reći da je to razvojni način instalacije.

## Strukturisane greške

Najmanje:

- `BROWSER_EXTENSION_NOT_CONNECTED`
- `BROWSER_EXTENSION_AUTH_FAILED`
- `BROWSER_PROFILE_NOT_FOUND`
- `BROWSER_WINDOW_NOT_FOUND`
- `TAB_NOT_FOUND`
- `TAB_POSITION_OUT_OF_RANGE`
- `TAB_SNAPSHOT_STALE`
- `TAB_ACTION_TIMEOUT`
- `TAB_ACTION_FAILED`
- `INCOGNITO_NOT_ALLOWED`

Sve greške prolaze kroz postojeći `AppError`/tool error format. Poruka korisniku mora biti korisna, a tehnički detalji ne smiju otkriti secret ili puni privatni URL u logovima.

## Implementacijske faze

### PR 1 — ekstenzija, pairing i read-only lista ✅ završeno

- MV3 ekstenzija i autentifikovan localhost transport.
- Python broker sa connection statusom i timeoutima.
- `browser_tabs(action="list")` za trenutni prozor.
- Snapshot store sa TTL-om.
- Settings status: povezano/nepovezano i postupak uparivanja.
- Unit/integration testovi bez stvarnog browsera preko fake extension klijenta.

### PR 2 — aktiviranje ordinalnog taba ✅ završeno

- `activate` nad snapshotom i stabilnim tab ID-em.
- Fokus browser prozora + aktiviranje taba.
- stale/race zaštita i jezičke instrukcije.
- Ručni test sa najmanje šest tabova i naredbama prvi/peti/posljednji.

### PR 3 — zatvaranje i hardening ✅ završeno

- `close` kao high-risk confirmation akcija.
- Provjera da approval retry ne može djelovati na drugi tab nakon promjene redoslijeda.
- Reconnect, multi-window, incognito behavior i privacy audit.
- Packaging/installation odluka za produkciju.

Ne spajati sva tri PR-a u veliki rewrite.

## Obavezni testovi

### Python

- list vraća 1-based stabilan redoslijed i tačan count;
- `brejv` se normalizuje na `brave`;
- activate koristi tab ID iz snapshot-a, ne trenutni tab na istom indeksu;
- istekli/promijenjeni snapshot vraća `TAB_SNAPSHOT_STALE`;
- position 0, negativan ili veći od counta se odbija;
- disconnect, auth failure i timeout imaju precizne kodove;
- close bez odobrenja vraća `CONFIRMATION_REQUIRED`;
- approved close sa izmijenjenim snapshotom ništa ne zatvara;
- URL/title sanitizacija i audit redaction.

### Ekstenzija

- neautentifikovana komanda se odbija;
- list mapira `chrome.tabs.query` u ugovoreni odgovor;
- activate poziva `chrome.windows.update(...focused:true)` i `chrome.tabs.update(...active:true)` za tačne ID-eve;
- close poziva `chrome.tabs.remove` samo za potvrđeni tab ID;
- reconnect ne duplira izvršenje istog request ID-a;
- nema content-script ili arbitrary-code putanje.

### Realtime/Electron

- Python i Realtime enum/schema ostaju usklađeni;
- tool se delegira Pythonu;
- model dobija kompletan list rezultat;
- confirmation approval rezultat za close vraća se agentu;
- batch/tool timeout ponašanje ostaje fail-safe.

### Ručni smoke test

1. Otvoriti Brave sa najmanje šest tabova poznatih naslova.
2. „Koliko tabova imam?“ — odgovor mora odgovarati aktivnom prozoru.
3. „Koji je peti?“ — naziv mora odgovarati UI-u.
4. „Otvori peti tab.“ — fokus mora preći na tačan tab.
5. Promijeniti redoslijed između list i activate — agent ne smije otvoriti pogrešan tab.
6. „Zatvori treći tab.“ — mora se pojaviti potvrda; odbijanje ništa ne zatvara, odobrenje zatvara tačan tab.
7. Isključiti ekstenziju — agent mora prijaviti nepovezanost, bez lažne tvrdnje o uspjehu.
8. Ponoviti ključne testove sa izgovorom „Brejv“.

## Acceptance kriteriji

- Agent može tačno reći broj i nazive tabova u aktivnom Brave/Chrome prozoru.
- Ordinalne naredbe su 1-based i aktiviraju tab iz važećeg snapshot-a.
- Promjena redoslijeda/race nikada ne dovodi do akcije nad pogrešnim tabom.
- Zatvaranje zahtijeva postojeću potvrdu i agent nakon klika zna konačan rezultat.
- Bez povezane ekstenzije nema nagađanja niti lažnog uspjeha.
- `Brave` i `Brejv` rade jednako.
- Nema nove business logike u `electron/main.cjs`, proizvoljnog shell executiona, content injectiona ni pristupa sadržaju stranice.
- Relevantni pytest/JS testovi, `npm run check`, `npm run typecheck` i `npm run build` prolaze.
- `agent_reports/` i `docs/MIGRATION_PLAN.md` ažurirani su u istom commitu kao implementacija.

## Šta nije dio ovog paketa

- čitanje ili sažimanje sadržaja web stranica;
- klikanje elemenata unutar stranice;
- history/bookmarks/cookies/passwords/downloads;
- Firefox ekstenzija u prvom paketu;
- sinhronizacija tabova preko cloud naloga;
- automatska produkcijska distribucija ekstenzije bez zasebne installer odluke.

## Obavezna procedura za pi agenta

1. `git status` i `git log` prije rada; ne pokupiti postojeće tuđe izmjene.
2. Provjeriti `docs/MIGRATION_PLAN.md` i aktuelni kod; ovaj brif nije dokaz da je funkcija već implementirana.
3. Osvježiti GitNexus indeks ako upozorenje ostane.
4. Pokrenuti `gitnexus_impact` prije izmjene svakog postojećeg simbola; stati i prijaviti HIGH/CRITICAL.
5. Re-čitati `electron/main.cjs` neposredno prije eventualne minimalne allowlist/delegation izmjene.
6. Sačuvati Electron kao tanak shell; Python je vlasnik funkcionalnosti.
7. Implementirati po malim PR fazama i pokrenuti testove iz ovog brifa.
8. Pokrenuti `gitnexus_detect_changes` prije commita.
9. Napisati agent report i ažurirati tracker u istom commitu.
10. Ne commitovati bez eksplicitnog korisničkog zahtjeva.
