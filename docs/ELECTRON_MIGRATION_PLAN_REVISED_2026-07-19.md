# Revidirani plan dovrsetka Electron migracije

**Datum:** 2026-07-19  
**Status:** prijedlog za usvajanje  
**Scope:** zavrsno razdvajanje Electron shell-a i Python backend-a, uklanjanje legacy runtime puteva i migracija thumbnail podsistema  
**Polazni dokument:** `docs/ELECTRON_MIGRATION_ANALYSIS.md`

## 1. Svrha i status izvora

Ovaj dokument nadogradjuje pocetnu analizu preostalog Electron koda. Ne tretira
broj linija kao glavni cilj. Primarni cilj je da svaki aktivni tok ima jednog
vlasnika, dokazani ugovor, testni gate i siguran rollback prije uklanjanja
legacy implementacije.

Izvori su vrednovani ovim redoslijedom:

1. `docs/MIGRATION_PLAN.md` je jedini izvor istine za status faza 0-19.
2. Trenutni kod i testovi su izvor istine za stvarno runtime ponasanje.
3. `docs/SECURITY_HARDENING_PLAN.md` je izvor sigurnosnih pravila.
4. `docs/SECURITY_HARDENING_ROADMAP_REVISED_2026-07-19.md` je operativni
   sigurnosni roadmap; ovaj plan mu ne smije protivrjeciti.
5. Datirani `agent_reports/` objasnjavaju odluke, ali tvrdnje u njima nisu dokaz
   ako ih trenutni kod ili puni test suite ne potvrde.
6. `docs/ELECTRON_MIGRATION_ANALYSIS.md` je istorijski pocetni nalaz, ne
   autoritativan plan za brisanje.

Postojeci dokument sadrzi datum 2026-07-26 iako je napravljen 2026-07-19. Taj
datum treba ispraviti kada se dokument formalno oznaci kao istorijski izvor.

## 2. Verifikovani baseline

### 2.1 Arhitektura koja stvarno postoji

```text
React renderer
    -> allowlisted preload IPC
    -> Electron main / IPC handleri
    -> Python localhost API sa session tokenom
    -> Python agent, alati, permission engine i SQLite
```

Ovaj model je realizovan za vecinu agent alata. Izuzetak je thumbnail board,
koji je i dalje hibridan:

```text
Realtime tool poziv
    -> src/lib/realtime.ts
    -> tools:execute
    -> electron/main.cjs
    -> legacyMedia.cjs
    -> OpenAI Image API + legacy JSON DB

Referentna slika:
React -> native Electron file picker -> Python validacija/opaque ID
      -> Electron legacy JSON board
```

Zato je ispravna statusna formulacija:

> Core Python migracija je zavrsena; produkcijsko zatvaranje legacy puta,
> thumbnail migracija i Electron decommissioning nisu zavrseni.

### 2.2 Aktivni i privremeni Electron slojevi

| Oblast | Trenutni vlasnik | Ciljni vlasnik | Odluka |
| --- | --- | --- | --- |
| BrowserWindow, tray, companion, native dialog | Electron | Electron | ostaje |
| Python process lifecycle i lokalni auth token | Electron | Electron | ostaje |
| Preload allowlist i IPC registracija | Electron | Electron | ostaje |
| Agent runtime, permission, storage, computer-use | Python | Python | ostaje |
| Realtime tool specifikacije | Electron/data-only | ugovoreni manifest | ostaje, ali dobija drift test |
| Tool dispatch | `main.cjs` + Python | tanak Electron router | refaktor |
| PowerShell computer-use fallback | Electron legacy | nema | ukloniti nakon parity gatea |
| Web search i generic image fallback | Electron legacy + Python | Python | ukloniti duplikat |
| Notes/records legacy JSON fallback | Electron legacy + Python | Python | ukloniti duplikat |
| Thumbnail Image API pozivi | Electron | Python | migrirati |
| Thumbnail board stanje | legacy JSON | Python SQLite | migrirati |
| Thumbnail file picker / Save As | Electron | Electron | ostaje kao native shell funkcija |

### 2.3 Dokazani problemi u pocetnoj analizi

1. Legacy kod nije mrtav. `RICKY_USE_LEGACY_POWERSHELL_TOOLS=1` ga moze
   aktivirati, a `electron-builder.yml` trenutno pakuje `electron/**/*`.
2. Frontend testovi postoje: 4 Vitest fajla i 244 testa. Problem je sto
   `test:voice` nije dio obaveznog `quality` toka.
3. `quality` neutralise npm audit sa `|| true`; operator precedence dodatno
   cini rezultat skripte nepouzdanim.
4. `thumbnail_generate`, `thumbnail_edit`, `thumbnail_select` i
   `thumbnail_grid` su aktivni model-facing alati bez Python ekvivalenta.
5. `legacyMedia.cjs` direktno cita `OPENAI_API_KEY`/`EXA_API_KEY` i poziva
   spoljne API-je iz Electron procesa. Migracija donosi sigurnosnu dobit jer
   tajne i outbound policy prelaze pod Python kontrolu.
6. `handleToolsExecute()` ima oko 330 linija i istovremeno radi routing,
   fallback, UI side effect, response adaptaciju i legacy business logiku.
7. `legacyTools.cjs` ima zastarjele komentare i prazan skup alata bez Python
   ekvivalenta, iako runtime fallback jos postoji.
8. Pocetni prijedlog za redukciju `legacyMedia.cjs` je kontradiktoran i mogao
   bi ukloniti funkcije koje aktivno koriste Realtime, renderer i IPC handleri.

### 2.4 Test baseline od 2026-07-19

| Provjera | Rezultat |
| --- | --- |
| `npm run test:voice` | 244 passed |
| `npm run check` | prolazi |
| `npm run smoke` | prolazi, 7/7 koraka |
| `npm test` | 384 passed, 3 failed |

Tri pada moraju biti razrijesena prije migracionih izmjena:

- `test_browser_open_is_listed` ocekuje `requires_computer_mode=True`, dok je
  commit `c58d6eb` namjerno promijenio politiku na `False`; test i puni report
  nisu uskladjeni.
- dva FAZA 16 testa ocekuju nedostajuci API kljuc, ali dobijaju uspjesan HTTP
  odgovor uprkos fixture postavci praznog env-a; test nije hermeticki izolovan
  od lokalne konfiguracije ili settings cache-a.

Ovo nisu dozvoljeni "poznati crveni testovi" tokom migracije. Gate 0 zahtijeva
zeleni puni suite i dokumentovanu odluku o ocekivanom ponasanju.

## 3. Ciljna arhitektura

### 3.1 Electron smije posjedovati

- app/window lifecycle;
- native file/open/save dialoge;
- tray, companion orb i globalni kill-switch;
- preload allowlist i IPC transport;
- start/stop/health Python sidecar-a;
- ciste UI adaptacije koje ne citaju tajne, ne pisu poslovno stanje i ne
  pozivaju spoljne AI/search API-je.

### 3.2 Python mora posjedovati

- sve model-facing tool definicije koje imaju poslovno ili sigurnosno
  ponasanje;
- permission, confirmation, cancellation i action receipt;
- OpenAI/Exa i druge spoljne integracije;
- notes, records, artifacts i thumbnail stanje;
- generisanje/uredjivanje thumbnaila i pristup referentnim slikama;
- storage migracije, retention i oporavak.

### 3.3 Router pravilo

Krajnji router ne treba listu "faza 11" koja se rucno siri. Ciljno pravilo je:

1. mali eksplicitni allowlist Electron-native operacija;
2. `set_mode` kao dvokoracni tok: Python permission odluka, zatim Electron UI
   side effect;
3. svi ostali model-facing alati idu u Python;
4. Python `UNKNOWN_TOOL` je konacan strukturirani odgovor, bez implicitnog
   pada u legacy implementaciju;
5. backend outage je fail-closed za model-facing alate.

### 3.4 Ugovor alata

Realtime schema i Python `ToolDefinition` trenutno dupliciraju naziv, schema,
risk i opis. Plan ne zahtijeva veliki generator u prvom koraku, ali zahtijeva
automatski drift test koji prijavljuje:

- tool postoji samo na jednoj strani;
- razliku u required poljima i `additionalProperties`;
- razliku u risk/confirmation/computer-mode pravilima;
- Electron-native izuzetke sa eksplicitnim razlogom.

## 4. Invarijante koje se ne smiju slomiti

1. Voice i text put moraju dobijati isti rezultat i sigurnosnu odluku.
2. Nijedan high-risk alat ne smije pasti na neprovjereni fallback.
3. Kill-switch mora raditi i kada renderer, voice sesija ili Python poziv
   zapne.
4. Electron renderer nikad ne dobija API kljuc ili proizvoljni lokalni path.
5. Native file picker ostaje jedini nacin dodavanja thumbnail reference.
6. Permanentni thumbnail broj se ne mijenja nakon restarta ili migracije.
7. Edit cuva parent/child vezu; select i 3x3 paginacija ostaju identicni.
8. Postojeci thumbnail fajlovi se ne brisu dok migracija nije verifikovana.
9. Produkcijski paket ne sadrzi legacy PowerShell ili tajni fallback.
10. Nema brisanja modula samo zato sto je feature flag podrazumijevano nula.
11. Svaka faza ima zaseban commit, agent report, tracker update i rollback.
12. Broj linija je metrika odrzavanja, ne acceptance kriterij.

## 5. Faze realizacije

## EM-0. Zeleni i hermeticki baseline

### Cilj

Uspostaviti pouzdan testni signal prije refaktora ili brisanja.

### Koraci

1. Uskladiti `test_browser_open_is_listed` sa usvojenom politikom i dodati
   negativne URL/credential testove kao sigurnosnu zastitu.
2. Izolovati FAZA 16 testove od `.env.local`, process env cache-a i globalnog
   settings singletona. Test ne smije pozvati stvarni Exa/OpenAI API.
3. Dodati `npm run test:voice` u obavezni `quality` tok.
4. Prepraviti audit korak tako da high/critical nalaz obara CI; privremeni
   exception mora biti zaseban dokumentovan korak, ne `|| true`.
5. Dodati syntax provjeru svih `.cjs` fajlova ili eksplicitno dokazati zasto je
   svaki izostavljeni fajl van runtime paketa.
6. Sacuvati baseline rezultata i spisak trenutno zapakovanih fajlova.

### Gate

- Python suite je potpuno zelen.
- Vitest, typecheck, build, Electron check i smoke su zeleni.
- Test bez API kljuceva daje isti rezultat na cistoj masini i developer masini.
- Nema mreznog poziva u unit testu bez eksplicitnog integration markera.

### Rollback

Samo test/config izmjene; rollback je vracanje jednog EM-0 commita.

### Velicina i delegiranje

`M`; test/CI agent, obavezna provjera sigurnosnog reviewera.

## EM-1. Inventar i executable contract freeze

### Cilj

Pretvoriti pretpostavke o paritetu u masinski provjerljivu matricu.

### Koraci

1. Napraviti tabelu svih Realtime toolova sa kolonama: owner, renderer call,
   Electron handler, Python definition, permission, storage, outbound, test.
2. Klasifikovati alate u `python`, `electron_native`, `temporary_hybrid`.
3. Dodati drift test Electron tool specs naspram Python `/tools` odgovora.
4. Dodati contract fixtures za `adaptPythonToolResponse`: success, artifact,
   structured error, cancellation, timeout i unknown tool.
5. Evidentirati svaki legacy DB key i stvarnog citaoca/pisca.
6. Evidentirati svaki API key i outbound endpoint koji Electron jos koristi.
7. Snimiti paket inventar iz unpacked builda, ne samo source tree.

### Gate

- Svaki model-facing tool ima jednog deklarisanog ciljnog vlasnika.
- Svaka razlika u Electron/Python specifikaciji je ili popravljena ili upisana
  kao odobreni Electron-native izuzetak.
- Nema "vjerovatno mrtve" funkcije bez call-site dokaza.

### Rollback

Nema runtime promjene; uklanjanje contract testa vraca prethodno stanje.

### Velicina i delegiranje

`M`; arhitektonski agent + nezavisni reviewer.

## EM-2. Izdvajanje testabilnog tool routera bez promjene ponasanja

### Cilj

Smanjiti rizik kasnijeg uklanjanja tako sto se routing izdvaja iz
`main.cjs`, ali legacy put jos ne brise.

### Ciljna struktura

```text
electron/ipc_handlers/tools.cjs
electron/core/toolRoutingPolicy.cjs
electron/services/toolResponseAdapter.cjs
```

`adaptPythonToolResponse` pripada adapteru, ne generickom HTTP klijentu.
`PHASE11_DELEGATED_TOOLS` treba preimenovati prema stvarnoj ulozi ili zamijeniti
policy klasifikacijom; ne premjestati ga u `legacyTools.cjs`.

### Koraci

1. Dependency-inject Python executor, mode getter/UI side effect i privremene
   legacy handlere u `createToolsHandler()`.
2. Premjestiti routing verbatim, bez preimenovanja IPC kanala ili response
   oblika.
3. Dodati Node/Vitest testove za Python success/failure, legacy disabled,
   fail-closed high-risk, `set_mode`, unknown tool i timeout.
4. `main.cjs` samo registruje `tools:execute` i prosljedjuje zavisnosti.

### Gate

- Golden contract test prije i poslije refaktora daje isti rezultat.
- Voice testovi ostaju 244+ i puni quality gate prolazi.
- Rucni smoke: note, web search, image, set_mode, screenshot i jedan
  computer-use alat.

### Rollback

Novi handler je jedan izolovan commit; vratiti wiring na staru funkciju.

### Velicina i delegiranje

`L`, visoki blast radius; obavezni GitNexus impact, project room, mandatory
review i test gate.

## EM-3. Trajno uklanjanje PowerShell fallbacka

### Preduslov

EM-0 do EM-2 su zeleni, a parity matrica potvrdi Python ekvivalente za click,
type, key, scroll, open-app, snapshot i UI inspect.

### Koraci

1. Za svaki legacy alat provjeriti permission, confirmation, active-window,
   cancellation, timeout i action-receipt paritet.
2. Ukloniti fallback grane, PowerShell importe i runtime env flag.
3. Obrisati `electron/tools_legacy/powershell/` i `legacyTools.cjs` tek kada
   vise nemaju pozivaoce.
4. Produkcijski build eksplicitno odbija legacy fajlove.
5. Security self-test pada ako se legacy modul, flag ili generic PowerShell
   executor ponovo pojavi u paketu.
6. Backend outage vraca strukturiranu Python-unavailable gresku; nikad ne
   izvrsava lokalni fallback.

### Gate

- Env manipulacija ne moze aktivirati legacy put.
- Unpacked i NSIS artifact ne sadrze legacy PowerShell fajlove.
- Nema generic shell/PowerShell alata dostupnog modelu.
- Parity i packaged smoke prolaze na cistoj Windows masini.

### Rollback

Samo release/source rollback. Runtime feature flag se ne vraca jer bi ponovo
otvorio produkcijski bypass.

### Velicina i delegiranje

`L`; Electron + Python agent, sigurnosni reviewer obavezan.

## EM-4. Uklanjanje dupliranih non-thumbnail implementacija

### Cilj

Ostaviti legacy JSON i `legacyMedia.cjs` privremeno samo za thumbnail board.

### Koraci

1. Ukloniti Electron fallback za `web_search` i `image_generate`; Python je
   jedini owner tajni i outbound poziva.
2. Ukloniti Electron notes/records CRUD fallback i pripadajuce JSON polje
   citanje/pisanje.
3. Klasifikovati presentation-only operacije:
   `artifact_show`, `show_menu` i `mermaid_render` mogu ostati Electron-native
   samo ako contract matrica potvrdi da ne citaju tajne, ne pisu poslovno
   stanje i ne zaobilaze permission odluke.
4. Smanjiti `legacyMedia.cjs` samo do stvarnog thumbnail dependency closure-a,
   utvrdjenog import/call grafom i testovima.
5. Dodati staticku provjeru da Electron source vise ne cita
   `OPENAI_API_KEY` ili `EXA_API_KEY` izvan privremeno odobrenog thumbnail
   modula.

### Gate

- Web/image/note/record tokovi rade kada `legacyMedia.cjs` eksportuje samo
  thumbnail funkcije.
- Electron vise nema Exa poziv ni generic image generation poziv.
- Legacy JSON poslije faze sadrzi samo thumbnail podatke koji jos nisu
  migrirani.

### Rollback

Vratiti samo EM-4 commit; Python podaci se ne mijenjaju.

### Velicina i delegiranje

`M-L`; dva manja commita: routing cleanup i media/DB cleanup.

## EM-5. Python thumbnail domen i ugovor

### Cilj

Napraviti Python ekvivalent prije prebacivanja aktivnog toka.

### Model podataka

Minimalno razmotriti tabele/repozitorijume:

- `thumbnail_references`: postojeci opaque ID, label, validirani path metadata;
- `thumbnail_images`: permanent number, path/asset ID, prompt, parent number,
  created_at, status;
- `thumbnail_board_state`: selected number i current page;
- `thumbnail_runs`: execution ID, mode, status, error i cancellation metadata.

Tacna schema se zakljucava tek nakon inventara svih polja iz legacy JSON-a.

### Tool/API ugovor

Python postaje vlasnik:

- `thumbnail_generate`;
- `thumbnail_edit`;
- `thumbnail_select`;
- `thumbnail_grid`;
- internog loading/run cleanup toka.

Native `add-reference` i `save-as` dijalozi ostaju u Electronu. Electron salje
opaque ID ili korisnikov odobreni destination; ne salje tajne rendereru.

### Sigurnosna pravila

1. OpenAI kljuc se cita samo u Python backendu.
2. Generate/edit su `outbound=True`, prolaze permission/prompt-injection
   eskalaciju, timeout, cancellation i action receipt.
3. Reference se resolve-uju neposredno prije citanja i ponovo validiraju protiv
   path sandboxa.
4. Renderer dobija opaque asset ID ili autorizovani lokalni endpoint, ne
   proizvoljnu filesystem putanju.
5. Svaki output ima size/type limit i atomican upis.

### Gate

- Python contract testovi pokrivaju generisanje, edit, selection, pagination,
  permanent numbering, parent vezu, reference resolve, timeout i cancellation.
- Test koristi fake HTTP transport; nema stvarnog OpenAI troska.
- Jedan eksplicitni integration smoke sa testnim kljucem je dokumentovan, ali
  nije dio svakog CI pokretanja.

### Rollback

Python implementacija je u shadow stanju i nije jos primarni runtime put.

### Velicina i delegiranje

`XL`; podijeliti na schema/repository, service/API i tool-contract PR-ove.

## EM-6. Shadow parity i migracija thumbnail stanja

### Cilj

Dokazati funkcionalni paritet i bez gubitka prevesti legacy JSON stanje u
Python SQLite.

### Koraci

1. Napraviti read-only dry-run importer koji prijavljuje broj referenci,
   slika, permanentnih brojeva, parent veza, loading zapisa i nedostajucih
   fajlova.
2. Definisati migration marker: `not_started`, `in_progress`, `verified`,
   `committed`, `rollback_required`.
3. Kopirati/importovati stanje idempotentno; nikad ne renumerisati slike.
4. Stare reference sa sirovom putanjom ne prihvatati tiho. Ako nemaju Python
   opaque ID, oznaciti ih za korisnicko ponovno dodavanje kroz file picker.
5. Uporediti legacy i Python board summary na istim fixture podacima.
6. Shadow poziv moze porediti rezultat bez duplog outbound generisanja:
   business odluke i board transformacije se porede lokalno, dok se stvarni
   Image API poziv izvrsava samo jednom.
7. Nakon verifikacije sacuvati read-only backup legacy JSON-a sa kratkom,
   dokumentovanom retention politikom.

### Gate

- Restart ili prekid u svakoj migration fazi je oporavljiv.
- Broj slika, permanentni brojevi, selection, page i parent veze su identicni.
- Missing/corrupt fajl daje izvjestaj, ne tihi gubitak.
- Korisnik rucno potvrdi: generate, edit selected, edit by number, grid page,
  add reference i Save As.

### Rollback

Dok se Gate ne potvrdi, Electron cita legacy stanje. Nakon switcha rollback
koristi read-only backup i release rollback, bez dual-write rezima.

### Velicina i delegiranje

`XL`; storage/migration agent + nezavisni reviewer i korisnicki runtime test.

## EM-7. Prebacivanje thumbnail toka i brisanje legacy media/DB

### Preduslov

EM-5 i EM-6 su kompletno verifikovani, ukljucujuci korisnicki runtime test.

### Koraci

1. `tools:execute` salje thumbnail alate Pythonu.
2. Realtime instructions dobijaju compact board state iz Python endpointa.
3. Renderer zadrzava isti artifact/board contract ili prolazi kontrolisanu
   verzionisanu migraciju.
4. `thumbnails:add-reference` ostaje native Electron dialog, ali poslije
   Python registracije vise ne pise legacy JSON.
5. `thumbnails:save-as` ostaje native; source se resolve-uje preko opaque asset
   ID-a ili strogo validiranog aplikacijskog data root-a.
6. Ukloniti startup loading cleanup iz `main.cjs` i prebaciti recovery u
   Python thumbnail run servis.
7. Kada call-site pretraga i GitNexus potvrde nula aktivnih pozivalaca, obrisati
   `legacyMedia.cjs` i `legacyDb.cjs`.
8. Ukloniti Electron direktne OpenAI/Exa API pozive i env citanje.

### Gate

- Source i packaged artifact ne sadrze `legacyMedia.cjs`, `legacyDb.cjs`,
  direktni Image/Exa endpoint ili citanje njihovih kljuceva iz Electrona.
- Thumbnail acceptance matrica je potpuno zelena.
- Realtime voice tok i reconnect poslije restarta cuvaju board state.

### Rollback

Release rollback + migracioni backup. Ne vracati runtime dual-write ili
feature flag u produkciju.

### Velicina i delegiranje

`L`; mandatory review i packaged test gate.

## EM-8. Finalno stanjenje `main.cjs` i IPC organizacija

### Cilj

Nakon uklanjanja legacy ponasanja, `main.cjs` ostaje composition root i app
lifecycle, bez business logike.

### Koraci

1. Premjestiti kill-switch u `electron/core/killSwitch.cjs`, uz dependency
   injection za backend cancellation, companion stop i renderer event.
2. Premjestiti preostale inline IPC handlere u tematske handler module.
3. `main.cjs` zadrzava kreiranje prozora, Python process lifecycle, handler
   wiring, app events i shutdown.
4. Ukloniti prazne/zastarjele komentare faza i imena koja vise ne opisuju
   ponasanje.
5. Ne premjestati logiku samo radi LOC cilja; modul se izdvaja kada ima jasnu
   odgovornost i samostalan test.

### Gate

- `main.cjs` nema storage, AI/outbound, permission ili tool business logiku.
- Svaki IPC kanal ima jednog handler vlasnika i preload allowlist test.
- Kill-switch prolazi backend-up, backend-down i renderer-unresponsive test.
- Ciljna velicina je okvirno 200-350 linija, ali arhitektonske invarijante su
  vaznije od broja.

### Rollback

Svaki modul se izdvaja u zasebnom malom commitu.

### Velicina i delegiranje

`M-L`; Electron refactor agent, bez funkcionalnih promjena u istom PR-u.

## EM-9. Produkcijski paket i release dokaz

### Cilj

Dokazati da source cleanup stvarno postoji i u distribuiranom artefaktu.

### Koraci

1. `electron-builder.yml` koristi eksplicitni allowlist ili provjerene exclude
   obrasce; samo `electron/**/*` vise nije dovoljan dokaz.
2. Dodati skriptu koja pregleda `app.asar`/unpacked artifact i pada ako nadje
   legacy PowerShell, legacy DB/media, `.env`, API kljuc, korisnicku bazu ili
   screenshot podatke.
3. Pokrenuti production security self-test na packaged buildu.
4. Testirati instalaciju, prvi startup, backend health, Realtime, tool
   execution, thumbnail i uninstall na cistoj Windows masini.
5. Code signing, dependency audit i update chain ostaju obavezni gateovi iz
   sigurnosnog roadmapa; ovaj plan ih ne duplira niti proglasava zavrsenim.

### Gate

- Potpisani packaged artifact prolazi funkcionalni i sigurnosni smoke.
- Nema legacy runtime bypassa ni tajni u paketu.
- `npm run quality` i dependency gate su stvarni hard fail.
- `docs/MIGRATION_PLAN.md` dobija novu Electron decommission sekciju sa
  statusom EM-0 do EM-9 zasnovanim na dokazima.

### Rollback

Povuci release; vratiti prethodni potpisani artifact. Ne popravljati produkciju
runtime env flagom.

### Velicina i delegiranje

`L`; packaging/release agent + provjera na nezavisnoj masini.

## 6. Zavisnosti i redoslijed

```text
EM-0 -> EM-1 -> EM-2 -> EM-3 -> EM-4
                   |             |
                   |             +-> EM-5 -> EM-6 -> EM-7
                   |                                  |
                   +---------------------------------> EM-8 -> EM-9
```

- EM-0 je apsolutni blocker za sve ostalo.
- EM-3 ne ceka thumbnail migraciju; PowerShell fallback je odvojen problem.
- EM-4 odvaja duplikate od aktivnog thumbnail dependency closure-a.
- EM-7 ne pocinje prije potpunog pariteta i korisnicke potvrde iz EM-6.
- EM-8 se radi tek kada router vise ne nosi privremene legacy grane.
- EM-9 je release dokaz, ne administrativna formalnost.

## 7. Commit i handoff strategija

Svaka faza mora biti zaseban paket rada. EM-5 i EM-6 se dodatno dijele na male
PR/commit cjeline. Za svaki paket agent mora ostaviti:

1. scope lock i listu fajlova koje ne dira;
2. GitNexus impact prije izmjene simbola;
3. test plan prije implementacije;
4. ciljane testove i puni quality gate;
5. `gitnexus_detect_changes` prije commita;
6. `agent_reports/YYYY-MM-DD_*.md` sa odlukama, rizicima i rollbackom;
7. update `docs/MIGRATION_PLAN.md` u istom commitu, ali tek kada je gate
   stvarno zelen;
8. korisnicku runtime potvrdu kada agent nema GUI/API-key pristup.

Ne prihvatati report koji kaze "svi testovi prolaze" ako je pokrenut samo
ciljani podskup. Report mora navesti tacnu komandu i broj testova.

## 8. Globalna test matrica

### Svaki PR

- `npm run typecheck`;
- `npm run test:voice`;
- `npm run check`;
- `npm run build`;
- `npm test`;
- `npm run smoke`;
- GitNexus detect-changes;
- provjera da nema nenamjernih network poziva u unit testovima.

### Tool router

- Python success i structured error;
- timeout i cancellation;
- unknown tool;
- backend unavailable fail-closed;
- confirmation payload binding;
- voice/text paritet;
- `set_mode` permission + Electron side effect;
- renderer dobija isti artifact shape.

### Thumbnail

- generate, edit selected i edit by permanent number;
- parent/child veza i permanent numbering;
- grid page i selection persistence;
- loading recovery poslije crasha;
- reference add/resolve/delete/missing fajl;
- prompt i image size limit;
- outbound policy, cancellation i timeout;
- Save As path validation;
- legacy JSON migration, ponovljeni startup i rollback;
- test bez pravog API troska + odvojeni manual integration smoke.

### Packaged build

- nema legacy fajlova, `.env` ili runtime podataka;
- env flag ne vraca fallback;
- Python sidecar auth i health;
- production self-test hard fail;
- kill-switch sa fokusiranim i nefokusiranim prozorom;
- potpis i checksum prema sigurnosnom roadmapu.

## 9. Rizici i odluke

| Rizik | Posljedica | Kontrola |
| --- | --- | --- |
| Brisanje thumbnail funkcija kao "dead" | gubitak aktivne funkcije | EM-1 call/contract matrica + EM-5/6 paritet |
| Dva izvora tool schema | permission/schema drift | automatski drift test |
| Testovi citaju lokalne kljuceve | lazno zelen/crven suite i moguc trosak | hermeticki EM-0 fixtures |
| Legacy flag u paketu | produkcijski bypass | EM-3 fizicko uklanjanje + artifact test |
| Dual-write JSON/SQLite | divergencija i teski rollback | idempotent snapshot migracija, bez dugog dual-writea |
| Renumerisanje thumbnaila | korisnicki podaci i glasovne reference pucaju | permanent number invariant |
| Premjestanje koda bez testa | manji fajl, isti rizik | behavior characterization prije refaktora |
| Veliki rewrite | teska dijagnostika i rollback | mali fazni commitovi |
| Report se oslanja na podskup testova | lazna tvrdnja o zavrsetku | tacna komanda i test count obavezni |

## 10. Sta se svjesno ne migrira

- BrowserWindow i window mode;
- companion orb, tray i native context menu;
- native file/open/save dialog;
- globalni kill-switch hotkey;
- Python process manager i lokalni token bootstrap;
- preload allowlist i tanak IPC transport;
- Electron-specific security self-test dio;
- Realtime data contract, osim ako posebna odluka uvede generisani manifest.

Ovo nije neuspjela migracija. To je ispravna granica desktop shell-a.

## 11. Definicija zavrsetka

Electron migracija je zavrsena tek kada svi uslovi postoje istovremeno:

```text
zeleni hermeticki testovi
+ jedan owner za svaki model-facing tool
+ nema runtime legacy fallbacka
+ nema Electron AI/search tajni ili outbound poziva
+ thumbnail stanje i Image API su u Pythonu
+ legacy JSON je migriran i verifikovan
+ main.cjs je composition root, ne business sloj
+ packaged artifact ne sadrzi legacy kod ili tajne
+ korisnicki runtime smoke je potvrdjen
+ tracker, agent report i kod imaju isti status
= Electron decommissioning zavrsen
```

## 12. Neposredni sljedeci korak

Ne pocinjati uklanjanjem `legacyMedia.cjs`. Prvi implementacioni paket je
**EM-0: zeleni i hermeticki baseline**, zatim **EM-1: executable contract
freeze**. Tek nakon toga je bezbjedno izdvajati router i uklanjati fallback.
