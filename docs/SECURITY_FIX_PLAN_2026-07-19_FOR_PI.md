# Sigurnosni plan ispravki — za pi agenta

**Datum:** 2026-07-19
**Autor pregleda:** Claude (spoljni bezbjednosni pregled, na zahtjev korisnika)
**Projekat:** RileyJarvis Windows Hybrid ("Naš-agent")
**Za izvršioca:** pi agent
**Metod:** ručno čitanje ključnih bezbjednosnih fajlova (permission engine, tool
executor, confirmation service/repo, computer-use alati, browser broker,
Electron preload, auth, path sandbox). Nalazi su verifikovani u kodu, ne iz
dokumentacije.

**Ažuriranje 2026-07-19 (puni pregled):** na zahtjev korisnika obavljen je
prošireni pregled cijelog backenda (103 .py fajla), svih API endpointa, svih
tool kataloga, storage repozitorija, `core/`, agent runtime-a i Electron
sloja (`main.cjs`, `preload.cjs`, `ipc_handlers/`, `core/`). Rezultat:
**prošireni pregled POTVRĐUJE sve ranije P1–P3 nalaze** (nijedan nije opovrgnut)
i dodaje **tri nova nalaza** (P2-K, P3-L, P3-M — vidi ispod). Ukupna slika:
kôd je dosljedno i pažljivo osiguran; nema kritičnih ni lako iskoristivih rupa.
Detaljna lista provjerenog-i-čistog proširena je na kraju dokumenta.

---

## 0. Kako koristiti ovaj dokument

Svaki nalaz ima: **težinu**, **lokaciju (fajl:linija)**, **zašto je bitno**,
**tačnu ispravku** i **kriterij prihvatanja (test)**. Raditi **jedan nalaz =
jedan mali commit + agent_report**, redom po prioritetu (P1 prije P2 prije P3).
Poštovati postojeća pravila iz `AGENTS.md` / `CLAUDE.md`:

- Ne dodavati novu logiku u `electron/main.cjs`.
- `gitnexus_detect_changes` prije commita, `agent_reports/` izvještaj u istom commitu.
- `docs/MIGRATION_PLAN.md` tracker je izvor istine za status — ažurirati ako se zatvara stavka.
- Prije izmjene svakog fajla: `git status`/`git log` (dijeljeni tree), re-čitati
  collision fajlove (`permission_engine.py`, `tool_executor.py`, `main.py`) svježe.

**Napomena o kvalitetu zatečenog stanja:** arhitektura je zdrava i mnoge kontrole
su ispravno implementirane (izolacija OpenAI ključa, atomični single-use
confirmation, secure preload bez generic IPC, secure webPreferences, runtime
schema validacija, redakcija tajni u logovima, čist computer.py bez shell
injectiona). Nalazi ispod su **preostale rupe i defense-in-depth poboljšanja**,
ne temeljni problemi. Većina je mala po obimu.

---

## P1 — Prioritetne ispravke (uraditi prve)

### P1-A. Confirmation se troši PRIJE active-window provjere

- **Težina:** srednja (narušava ugovor "jedno odobrenje = jedna akcija"; nije eskalacija privilegija)
- **Lokacija:** `python_backend/app/agent/tool_executor.py:93` (poziv `check_permission`)
  vs `:112` (poziv `check_active_window`); potrošnja u
  `python_backend/app/agent/permission_engine.py:224` (`confirmation_service.consume`)
- **Zašto je bitno:** `check_permission` atomično **konzumira** approved
  confirmation (jednokratni token), a `check_active_window` se poziva **poslije**
  toga. Ako aktivni prozor prekrši blocked-apps pravilo (npr. korisnik u
  međuvremenu fokusira `powershell.exe`), akcija se blokira — ali je confirmation
  već potrošen. Korisnik mora ponovo odobravati, a napadač koji može mijenjati
  fokus može "trošiti" korisnikova odobrenja. Ugovor jednokratnog odobrenja se
  tiho gubi.
- **Ispravka:** Preurediti redoslijed tako da se **sve neuspješne provjere
  izvrše prije konzumiranja**. Konkretno: pozvati `check_active_window(tool)`
  PRIJE `check_permission(...)` u `tool_executor.py`, ili izdvojiti
  `consume()` iz `check_permission` u zasebni korak koji `tool_executor` poziva
  tek nakon što su i permission i active-window provjere prošle. Preferirana
  varijanta: active-window prije permission (manja izmjena, active-window nema
  bočnih efekata).
- **Kriterij prihvatanja:** Test koji odobri high-risk computer akciju, postavi
  aktivni prozor na blokiranu aplikaciju, pozove izvršenje → akcija se odbija
  sa `ACTIVE_WINDOW_BLOCKED` **i** confirmation ostaje `approved` (ne
  `consumed`), tj. može se iskoristiti kad se prozor vrati na dozvoljeni.

### P1-B. payload_hash se preskače kad nije postavljen (ista rupa kao S-04 tool_name)

- **Težina:** srednja (danas nije iskoristivo jer `propose()` uvijek postavlja
  hash, ali je defense-in-depth rupa identičnog oblika onoj koju je S-04 zatvorio)
- **Lokacija:** `python_backend/app/agent/permission_engine.py:211-217`
- **Zašto je bitno:** `if bound_hash and bound_hash != hash_payload(...)` znači:
  ako confirmation nema `payload_hash`, provjera argumenata se **potpuno
  preskače** i confirmation gejtuje bilo koje argumente za taj tool. To je isti
  obrazac koji je S-04 zatvorio za `tool_name` (linija 204 sada odbija prazan
  tool_name). `payload_hash` treba tretirati jednako strogo.
- **Ispravka:** Za tool confirmations zahtijevati da `payload_hash` postoji i da
  se poklapa — fail-closed ako nedostaje:
  ```python
  bound_hash = confirmation.get("payload_hash")
  if not bound_hash or bound_hash != hash_payload(request.arguments):
      return AppError("CONFIRMATION_MISMATCH",
          f"Confirmation '{confirmation_id}' does not match the submitted arguments.",
          status_code=403)
  ```
- **Kriterij prihvatanja:** Test koji ubaci approved confirmation sa
  `tool_name` postavljenim ali `payload_hash=None` → izvršenje tool-a se odbija
  sa `CONFIRMATION_MISMATCH`, ne prolazi.

### P1-C. WebSocket `/browser-bridge` prihvata konekciju prije provjere Origin-a

- **Težina:** srednja (autentikacija pairing kodom sprječava stvarno preuzimanje,
  ali nedostaje sloj koji bi odbio ne-ekstenzijske origine prije handshake-a)
- **Lokacija:** `python_backend/app/services/browser_extension_broker.py:576`
  (`await websocket.accept()` bez provjere Origin headera)
- **Zašto je bitno:** WebSocket handshake **nije** podložan same-origin/CORS
  politici kao `fetch()`. Bilo koja web stranica otvorena u browseru može svojim
  JavaScriptom otvoriti `ws://127.0.0.1:8765/browser-bridge`, konekcija se
  prihvata, i stranica ulazi u pairing petlju. Pairing traži humani kod prikazan
  u aplikaciji i rate-limitovan je (5/60s), pa stvarno uparivanje nije moguće —
  ali prihvatanje bilo kog web origina je nepotrebna izloženost (DoS pokušaji,
  probing). Ovo je jedini mrežni ulaz koji namjerno **nema** Bearer token gejt
  (koristi vlastiti pairing), pa je Origin provjera prava dodatna brava.
- **Ispravka:** Prije `websocket.accept()` pročitati `websocket.headers.get("origin")`
  i odbiti sve što nije `chrome-extension://`, `moz-extension://` ili prazno
  (native WS klijent bez Origin-a). Allowlist origina konfigurabilan; nepoznat
  origin → `await websocket.close(code=4403)` bez `accept()`. Paziti: legitimna
  MV3 ekstenzija šalje `chrome-extension://<id>` — ne hardkodovati konkretan id
  osim ako je poznat i stabilan.
- **Kriterij prihvatanja:** Test koji simulira WS handshake sa
  `Origin: https://evil.example` → konekcija se odbija prije `accept()`; test sa
  `Origin: chrome-extension://<id>` → prolazi u pairing petlju.

---

## P2 — Sekundarne ispravke

### P2-D. Poređenje lokalnog tokena nije constant-time

- **Težina:** niska (na localhost-u; ali nekonzistentno sa ostatkom koda)
- **Lokacija:** `python_backend/app/core/auth.py:40` (`token != expected`)
- **Zašto je bitno:** Broker ispravno koristi `secrets.compare_digest`
  (`browser_extension_broker.py:653,675`), a glavna kapija backenda koristi
  običan `!=` koji je podložan timing analizi. Rizik je nizak (lokalni token,
  loopback), ali glavna brava ne treba da bude slabija od sporedne.
- **Ispravka:** `import secrets` i zamijeniti:
  ```python
  if not secrets.compare_digest(token, expected):
      raise AppError("UNAUTHORIZED", "Invalid local session token.", status_code=401)
  ```
- **Kriterij prihvatanja:** Postojeći auth testovi i dalje prolaze (validan token
  200, nevalidan/nedostajući 401); `compare_digest` u kodu.

### P2-E. Opširno logovanje bridge poruka na WARNING nivou curi podatke o pretraživanju

- **Težina:** niska-srednja (privatnost; tab URL-ovi/naslovi u logovima)
- **Lokacija:** `python_backend/app/services/browser_extension_broker.py:575,603`
  (`log.warning("[bridge:%s] recv type=%s %s", ...)`)
- **Zašto je bitno:** Debug instrumentacija dodata 2026-07-16 ostavljena je na
  `warning` nivou i loguje **cijele** poruke. Rediguju se samo polja
  `credential/secret/code`, ali **ne** i tab URL-ovi i naslovi stranica, koji su
  osjetljivi podaci o pretraživanju i završavaju u trajnim logovima.
- **Ispravka:** Spustiti ove pozive na `log.debug`, ili ih staviti iza
  eksplicitnog debug feature-flag-a, i proširiti redakciju da maskira/skraćuje
  `url`/`title` polja u `safe_msg`. Zadržati `conn_tag` radi praćenja.
- **Kriterij prihvatanja:** Pri normalnom radu (bez debug flag-a) log ne sadrži
  pune tab URL-ove; test provjerava da `url` polje nije prisutno u ispisu na
  default nivou.

### P2-F. `filesystem_search` izlaže imena/putanje cijelog fajl-sistema modelu (i dalje ka OpenAI)

- **Težina:** srednja (otkrivanje informacija; dizajnerska odluka, ali bez ograde)
- **Lokacija:** `python_backend/app/tools/system/filesystem_search.py:51-76,144-185`
- **Zašto je bitno:** Alat pretražuje **sve diskove + home** (`_drive_roots`,
  `Path.home()`) i vraća imena i pune putanje pogodaka. Ne čita sadržaj (samo
  metapodaci), ali imena fajlova/foldera sa cijelog sistema postaju vidljiva
  modelu i, ako se proslijede u prompt, odlaze ka OpenAI. Ne koristi
  `path_sandbox` (namjerno — "nađi moj fajl"), ali nema ograničenja opsega ni
  saglasnosti korisnika za pretragu izvan `data_dir`/home.
- **Ispravka (odluka korisnika, pa implementacija):** Razmotriti jedno od:
  (a) podrazumijevano ograničiti pretragu na `data_dir` + korisnički home, a
  pretragu drugih diskova tražiti samo uz eksplicitnu potvrdu; (b) dodati
  filter/redakciju očigledno osjetljivih putanja; (c) zadržati kako jeste ali
  klasifikovati alat kao `reads_external_content`/`outbound` gdje je relevantno
  da uđe u prompt-injection eskalaciju. Minimum: potvrditi risk klasifikaciju
  ovog alata u njegovoj `ToolDefinition` i dokumentovati odluku.
- **Kriterij prihvatanja:** Zapisan razlog odabrane opcije u agent_report + test
  koji potvrđuje izabrano ponašanje (npr. pretraga izvan home traži potvrdu).

---

## P3 — Održavanje i dubinska odbrana (planirati, nije hitno)

### P3-G. Podaci u mirovanju nisu šifrovani; retencija snimaka ekrana

- **Težina:** niska (prihvatljivo za lični single-user alat, ali screenshots nose tuđe podatke)
- **Lokacija:** SQLite baza + `data/` folder; postojeći tok:
  `agent_reports/2026-07-12_screenshot-privacy.md`, IPC `deleteAllScreenshots`
  (`electron/preload.cjs:24`)
- **Zašto je bitno:** SQLite (tool_runs, confirmations, planovi, konverzacije) i
  `data/` (bilješke, **snimci ekrana**) stoje u čistom obliku. Snimci ekrana iz
  computer-use moda mogu sadržati tuđe osjetljive podatke (mejlovi, dokumenti
  drugih ljudi na ekranu).
- **Ispravka:** Verifikovati da postoji **podrazumijevana retencija/čišćenje**
  snimaka (ne samo ručno "obriši sve"); dodati opciju "ne čuvaj snimke nakon
  sesije"; dokumentovati preporuku BitLocker/FDE za disk. Ovo je najviše
  konfiguraciona i dokumentaciona stavka.
- **Kriterij prihvatanja:** Definisana i testirana default retencija; postavka
  za automatsko brisanje snimaka postoji.

### P3-H. Legacy PowerShell put zaobilazi Python permission engine

- **Težina:** niska-srednja (feature-flagovan; ali drugi put do OS-a bez blocked-apps/active-window)
- **Lokacija:** `electron/tools_legacy/powershell/*`, `electron/core/legacyTools.cjs`
- **Zašto je bitno:** Legacy computer_* alati (escaping im je ispravan — provjereno)
  ne prolaze kroz `permission_engine` (blocked_apps, active-window, prompt-injection
  eskalacija žive u Python putu). Dok postoje, to je drugi, slabije gejtovani put
  do OS automatizacije.
- **Ispravka:** Potvrditi da je feature-flag za legacy put **podrazumijevano
  OFF**; kad Python zamjena bude potvrđeno testirana za sve computer_* alate,
  ukloniti legacy put po planu iz `docs/LEGACY_TOOLS.md`.
- **Kriterij prihvatanja:** Zapisan status flag-a; ako je OFF po defaultu,
  dokumentovati; definisan datum/uslov uklanjanja.

### P3-I. Prompt-injection lanac (eksterni sadržaj → kucanje) nema eksplicitan regresioni test

- **Težina:** srednja (kontrola postoji, ali nedokazana za baš ovaj lanac)
- **Lokacija:** eskalacija u `permission_engine.py:129-145`
  (`external_content_seen` → traži potvrdu); ulazi: `web_search` (Exa),
  `computer_type_text`
- **Zašto je bitno:** Najrealniji napad je: web pretraga vrati tekst sa
  zlonamjernom instrukcijom → model → kucanje/klik u aktivni prozor. Eskalacija
  koja to hvata (`external_content_seen` + akcijski tool → confirmation) postoji
  i izgleda ispravno, ali treba **dokaz** kroz namjenski test, i treba pokriti i
  legacy put (README kaže da su kucanje/Enter u computer-use dozvoljeni bez
  potvrde — to važi za legacy PowerShell put, ne za Python).
- **Ispravka:** Dodati regresioni test: postaviti `external_content_seen=True`
  (kao da je `web_search` ranije u ovom turnu vratio rezultat) → poziv
  `computer_type_text` mora tražiti confirmation, ne izvršiti se tiho. Ponoviti
  za `outbound` tool (web_search sam) i za `computer_click`.
- **Kriterij prihvatanja:** Testovi u pytest setu koji dokazuju eskalaciju za
  bar tri toola; ulaze u `npm run quality` regresioni set.

### P3-J. npm / Electron / Chromium lanac snabdijevanja

- **Težina:** niska (inherentna cijena Electron stacka; kontinuirano)
- **Zašto je bitno:** Aplikacija nosi Chromium (Electron) i stotine tranzitivnih
  npm zavisnosti; zastarjeli Electron = nošenje poznatih browser CVE-ova.
- **Ispravka:** Dodati `npm audit --production` u `npm run quality` (ili u
  mjesečni ritual) i pratiti Electron security izdanja; pinovati i redovno dizati
  Electron verziju.
- **Kriterij prihvatanja:** `npm audit` korak postoji u quality/CI toku;
  dokumentovan ritual ažuriranja Electrona.

---

## Novi nalazi iz punog pregleda (2026-07-19)

### P2-K. Prompt-injection eskalacija je per-turn na tekstualnom putu, a tainted sadržaj ostaje u istoriji razgovora

- **Težina:** srednja-niska (glavni put je glas, koji je bolje zaštićen — vidi dolje)
- **Lokacija:** `python_backend/app/agent/runtime.py:64` (`external_content_seen = False`
  na početku **svakog** `handle_message`); nasuprot tome
  `src/lib/realtime.ts:86` prati `externalContentSeen` za **cijelu glasovnu sesiju**
- **Zašto je bitno:** Na tekstualnom putu (`POST /agent/message`), zastavica
  `external_content_seen` se resetuje na `False` na početku svake poruke. Ali
  nepovjerljivi sadržaj koji je `web_search`/`screen_snapshot`/`ui_inspect`/
  `filesystem_search` pročitao u poruci N ostaje u istoriji razgovora
  (`raw_history_for_prompt`, linija 67) i model ga vidi u poruci N+1. U poruci
  N+1 zastavica je opet `False`, pa akcija **srednjeg** rizika (npr. `set_mode`)
  **neće** biti eskalovana u potvrdu, iako je model i dalje pod uticajem
  tainted sadržaja iz poruke N. Jedina preostala odbrana kroz turnove je
  `wrap_untrusted_content` delimiter (koji model *treba* da poštuje), bez
  eskalacijskog backstop-a. **Napomena:** glasovni put (`realtime.ts`) prati
  zastavicu po sesiji (šire), pa je tamo rupa manja — ovo prvenstveno pogađa
  tekstualni `/agent/message`.
- **Ispravka:** Na tekstualnom putu, "zaljepiti" (sticky) `external_content_seen`
  za cijeli razgovor, ne po poruci — jednom kad je tainted sadržaj ušao u
  istoriju, zadržati eskalaciju za sve naredne akcijske alate u tom razgovoru.
  Izvor istine može biti flag na `conversation_state` (npr.
  `external_content_seen_at`), koji `runtime` čita na početku svake poruke
  umjesto tvrdog `False`. Uskladiti semantiku sa glasovnim putom (sesija/razgovor).
- **Kriterij prihvatanja:** Test: poruka 1 pozove `web_search` (tainted), poruka
  2 (novi `handle_message`, isti conversation_id) pozove `set_mode` →
  `set_mode` se eskalira u potvrdu (blokira se u autonomnom runtime-u), ne
  izvršava se tiho.

### P3-L. `source: "ui"` bypass vjeruje markeru koji dolazi iz renderera

- **Težina:** niska (ograničeno na `set_mode`; sam mod ne izvršava akcije)
- **Lokacija:** `electron/main.cjs:396` (`if (toolContext.source === "ui") return applyModeSwitch();`)
- **Zašto je bitno:** Ulazak u Computer Mode preko `source: "ui"` **zaobilazi**
  Python permission engine (namjerno — ljudski klik na toggle je jača
  saglasnost). Bypass je ispravno ograničen **samo na `set_mode`**, a sam
  Computer Mode ne izvršava nikakvu akciju (akcijski alati i dalje gejtuju na
  vlastiti rizik), pa je praktični rizik nizak. Ali `source: "ui"` je polje
  koje **renderer** popunjava; kompromitovan renderer (npr. kroz XSS, iako je
  ta površina uska — samo Mermaid strict SVG) mogao bi tiho ući u Computer Mode
  slanjem `context: { source: "ui" }`. Vjerovati markeru iz renderera za
  zaobilaženje backend gejta je dizajnerski miris.
- **Ispravka (dubinska odbrana, nije hitno):** Umjesto da vjeruje `source` polju
  iz `toolCall.context`, Electron main treba da sam prati da li je poziv potekao
  iz stvarnog UI event-a (npr. zaseban IPC kanal `set_mode:ui-toggle` koji samo
  toggle dugme može pozvati, odvojen od generičkog `tools:execute`). Tako
  renderer ne može "proglasiti" poziv korisničkim.
- **Kriterij prihvatanja:** UI toggle i dalje radi bez backenda; poziv
  `tools:execute` sa `context.source="ui"` iz koda koji nije toggle više ne
  zaobilazi permission engine (ili je toggle premješten na zaseban kanal).

### P3-M. Migracioni SQL koristi f-string za identifikatore (bezbjedno danas, čuvati invarijantu)

- **Težina:** niska (danas nije iskoristivo; izvori su developer-konstante)
- **Lokacija:** `python_backend/app/storage/db.py:234` (`PRAGMA table_info({table})`)
  i `:247` (`ALTER TABLE {table} ADD COLUMN {column} {definition}`)
- **Zašto je bitno:** SQL identifikatori (imena tabela/kolona) se ne mogu
  parametrizovati `?` placeholderom, pa je f-string ovdje tehnički neizbježan.
  Trenutno su `table`/`column`/`definition` isključivo developer-konstante iz
  `MIGRATIONS` liste (`db.py:275`), pa nema injection rizika. Rizik bi nastao
  tek ako bi neko ubuduće proslijedio spoljni/model-kontrolisani string ovim
  funkcijama.
- **Ispravka:** Ne mijenjati ponašanje, ali dodati invarijantu: kratak komentar
  + (opciono) `assert` da `table`/`column` prolaze `^[A-Za-z_][A-Za-z0-9_]*$`
  allowlist, da bi budući pozivač sa spoljnim ulazom pukao odmah umjesto tiho.
- **Kriterij prihvatanja:** Allowlist/validacija identifikatora na ulazu u
  `_ensure_column`/`_existing_columns`; test da neispravno ime tabele podiže grešku.

---

## Šta je provjereno i NIJE problem (da se ne troši vrijeme)

- **OpenAI API ključ** nikad ne stiže do renderera — backend kuje kratkoživući
  Realtime `client_secret` (`api/realtime.py`). ✅
- **Backend auth fail-closed** na svakoj ruti (`auth.py` — osim P2-D timing sitnice). ✅
- **Confirmation single-use** je atomičan na nivou baze
  (`confirmation_repo.py:127` — `UPDATE ... WHERE id=? AND status='approved'`). ✅
- **Electron preload** — eksplicitni imenovani kanali, bez generic
  `ipcRenderer.invoke` pass-through (`preload.cjs`). ✅
- **secure webPreferences** — `contextIsolation/sandbox/nodeIntegration=false`,
  jedan izvor istine + self-test gate. ✅
- **computer.py** — nema shell injectiona (`Popen([target], shell=False)`,
  allowlist aplikacija, koordinate kroz `int()`). ✅
- **computer_* tool definicije** — SADA ispravno postavljaju
  `blocked_apps=DEFAULT_BLOCKED_APPS` i `requires_active_window_match=True`
  (`tool_catalog/phase13.py`). ✅
- **Runtime schema validacija** ulaza (`tool_executor.py:77`). ✅
- **tool_name binding** na confirmation (S-04 fix, `permission_engine.py:204`). ✅

### Dodatno provjereno u punom pregledu (2026-07-19) — čisto

- **Svi API endpointi iza globalnog auth gejta** —
  `FastAPI(dependencies=[Depends(require_local_token)])` (`main.py:75`) pokriva
  sve rutere; jedini izuzetak je raw WS ruta koja ima vlastiti pairing (nalaz P1-C). ✅
- **Prompt-injection containment radi na OBA puta** — agent runtime
  (`runtime.py:124-129`) i glasovni put (`realtime.ts:836,917`) postavljaju
  `external_content_seen` i wrap-uju nepovjerljivi sadržaj; verifikovano
  end-to-end (jedino ograničenje = P2-K, per-turn na tekstu). ✅
- **`source:"ui"` bypass je ograničen isključivo na `set_mode`**
  (`main.cjs:373-427`), a sam mod ne izvršava akcije (samo je P3-L dubinska napomena). ✅
- **SQL svugdje parametrizovan** (`?` placeholderi) osim DDL migracija sa
  konstantama (P3-M); provjereni `notes_repo`, `confirmation_repo`,
  `event_repo`, `agent_repo`, `artifact_repo`, `browser_bridge_credential_repo`. ✅
- **Svi HTTP klijenti imaju timeout** (model 30s, realtime 15s, exa 20s,
  image 60s, gmail 1s) — nema neograničenih poziva koji vise. ✅
- **`browser_open` URL validacija** (`browser.py:33`) — traži http/https + netloc,
  odbija embedded kredencijale; URL ne može početi sa `-` pa nema arg-injectiona
  u browser, `file://`/`javascript:` odbijeni. ✅
- **`computer_open_app`/`browser_open`/gmail** — `subprocess.Popen([...], shell=False)`,
  liste argumenata, allowliste; nigdje `shell=True` ni string komanda. ✅
- **Gmail adapter** — izolovan Chrome profil, loopback debug port biran nasumično,
  nikad korisnički profil; strukturno nikad ne klika Send (`gmail_draft_adapter.py`). ✅
- **Settings ne mogu ugasiti sigurnost** — `UserSettings` ima samo `user_name`,
  `agent_name`, `interface_language`; nema polja za auth/confirmation/computer-mode. ✅
- **Lokalni token fail-closed** — `_resolve_local_token` koristi
  `secrets.token_urlsafe(32)`, nekad je fail-open bio (sada zatvoreno, `config.py:39`). ✅
- **Thumbnails save-as path-traversal zaštita** — izvor mora biti unutar
  `dataDir` (`startsWith(resolvedDataDir + path.sep)`, `ipc_handlers/thumbnails.cjs:52`). ✅
- **Nema `eval`/`exec`/`pickle`/`yaml.load`/`__import__`** dinamičke egzekucije
  igdje u backendu. ✅
- **email split-tool dizajn** — `email_draft_stage` (low, bez potvrde) drži
  sadržaj samo u memoriji; `email_prepare_draft` (high, potvrda, computer mode)
  prima samo `draft_id`, pa potvrda nikad ne sadrži stvarni sadržaj mejla. ✅

---

## Ograničenje ovog pregleda

Puni pregled je pokrio: sva 103 backend `.py` fajla kroz ciljane pattern-pretrage
(SQL, subprocess, deserijalizacija, HTTP), plus ručno čitanje sigurnosne granice
(permission engine, tool executor, oba runtime puta), svih API endpointa, tool
kataloga, `core/`, ključnih storage repozitorija i Electron sloja (`main.cjs`,
`preload.cjs`, `ipc_handlers/`). **Nije** ručno pročitan svaki od 103 fajla
liniju-po-liniju (npr. pojedinačni UI React kod, svaki repo metod) — fokus je
bio na bezbjednosno relevantnim putevima. Postojeći interni auditi
(`PI_SECURITY_AUDIT_BRIEF.md`, `SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md`,
XSS sink audit, email security review) dopunjeni su, ne zamijenjeni. Zaključak
punog pregleda: **arhitektura je zrela i dosljedno osigurana; preostali nalazi
(P1–P3, K–M) su dubinska odbrana i robusnost, ne temeljni propusti.**
