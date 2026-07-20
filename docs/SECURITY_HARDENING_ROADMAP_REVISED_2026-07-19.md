# Revidirani Security Hardening Roadmap

**Datum:** 2026-07-19  
**Status:** prijedlog za usvajanje  
**Nadovezuje se na:** `docs/SECURITY_HARDENING_ROADMAP.md`  
**Autoritativni izvor pravila:** `docs/SECURITY_HARDENING_PLAN.md`  
**Izvor statusa migracije:** `docs/MIGRATION_PLAN.md`

Ovaj dokument ne briše niti mijenja originalni roadmap. On ga revidira na osnovu
ponovnog čitanja sigurnosnih planova, trenutnog koda i ranije tehničke analize.
Ako bude usvojen, originalni roadmap ostaje istorijski zapis, a ovaj dokument
postaje operativni plan za preostali sigurnosni rad.

---

## 1. Zašto je revizija potrebna

Originalni roadmap ima dobru osnovnu strukturu i ispravno prepoznaje četiri
važna područja: podatke u mirovanju, široku pretragu diska, legacy PowerShell i
kontinualno održavanje Electron surface-a. Međutim, drugi pregled je pronašao
nekoliko odluka koje bi u implementaciji proizvele ozbiljan rizik:

1. Trajni ključ baze ne smije biti izveden iz `local_token` vrijednosti.
   `local_token` je namjerno kratkoživući token po procesu/sesiji. Promjena
   tokena pri ponovnom pokretanju učinila bi šifrovanu bazu nečitljivom.
2. Isti sirovi ključ ne smije se direktno koristiti i za bazu i za screenshot
   fajlove. Potrebni su odvojeni izvedeni ključevi sa različitim kontekstima.
3. Produkcijsko čuvanje API ključeva nije bilo u operativnom roadmapu, iako ga
   autoritativni plan eksplicitno zahtijeva kroz DPAPI ili Windows Credential
   Manager.
4. Code signing, installer signing i politika update-a nisu bili faza roadmapa,
   iako su obavezni dio Security Gate 2.
5. `filesystem_search` trenutno ima statičku definiciju rizika. Jedan alat sa
   parametrom `scope` ne može pouzdano postati `medium` tek kada model pošalje
   `all_drives`, bez promjene permission arhitekture.
6. Cijeli `Path.home()` nije siguran podrazumijevani sandbox. U njemu se mogu
   nalaziti SSH ključevi, browser profili, cloud sync folderi i tajne.
7. CSP i sigurni Electron `webPreferences` već postoje i provjeravaju se u
   production self-testu. Njih ne treba ponovo "dodavati", nego održavati i
   regresijski provjeravati.
8. Trenutni `quality` izraz sadrži `npm run audit || true`, pa sigurnosni audit
   nije stvarni gate. Uz to, redoslijed operatora može prikriti pad ranijeg
   koraka.
9. Nedostaju precizna pravila za oporavak ključa, prekinutu migraciju, rollback,
   rotaciju ključa, backup i reinstalaciju Windows profila.
10. Formalni audit je planiran samo na kraju. Kriptografski dizajn treba dobiti
    nezavisan review prije implementacije, a završni audit poslije nje.

---

## 2. Trenutna procjena i zaštitna granica

### 2.1 Procjena zrelosti

- **Lokalna razvojna arhitektura:** približno 7.5/10.
- **Spremnost za produkcijsku distribuciju:** približno 6.5-7/10.

Razlika postoji zato što su osnovne runtime granice uglavnom dobre, ali Security
Gate 2 još nije zatvoren: produkcijske tajne, podaci u mirovanju, potpisivanje,
recovery i završni audit nisu kompletni.

### 2.2 Šta ovaj plan štiti

- API ključeve i druge dugotrajne tajne;
- SQLite podatke, razgovore, planove, potvrde i credential metapodatke;
- screenshot fajlove i privremene osjetljive artefakte;
- integritet Electron i Python produkcijskih binarnih fajlova;
- korisnika od preširoke pretrage lokalnog fajl sistema;
- permission granicu od zaobilaženja kroz legacy runtime put.

### 2.3 Realna ograničenja

Enkripcija u mirovanju štiti prije svega od čitanja ukradenog diska, kopirane
baze ili offline pristupa drugog procesa/profila. Ne štiti podatke kada je
aplikacija otključana i ključ se nalazi u memoriji. DPAPI u user scope-u ne
štiti od malware-a koji već radi kao isti prijavljeni Windows korisnik.

BitLocker, DPAPI, SQLCipher i AES-GCM su slojevi odbrane, a ne zamjena za
permission engine, prompt-injection zaštitu, OS zaštitu i siguran update.

---

## 3. Obavezne arhitektonske odluke

### 3.1 Stabilni master key

- Generisati 256-bitni nasumični master key pri prvom produkcijskom pokretanju.
- Master key zaštititi Windows DPAPI-em ili spremiti u Windows Credential
  Manager. Ne spremati ga kao čist tekst, env vrijednost ili dio SQLite baze.
- `local_token` ostaje kratkoživući autentikacioni token i nikad se ne koristi
  za enkripciju podataka.
- `OPENAI_API_KEY`, `EXA_API_KEY` i druge dugotrajne tajne u produkciji čuvati u
  istom Windows secret-storage sloju, ali ne kao master key.
- `.env.local` ostaje isključivo razvojni mehanizam.

### 3.2 Odvojeni izvedeni ključevi

Iz master key-a izvesti posebne ključeve, na primjer HKDF-SHA-256 kontekstima:

```text
ricky/database-encryption/v1
ricky/screenshot-encryption/v1
ricky/export-encryption/v1
```

Metadata mora sadržati verziju ključa. Nema ponovne upotrebe istog sirovog
ključa između različitih formata i namjena.

### 3.3 Recovery odluka prije implementacije

Prije H3/H4 mora se izabrati i dokumentovati jedan model:

- **Model A:** podaci su vezani za Windows korisnički profil; gubitak profila
  znači gubitak lokalnih podataka;
- **Model B:** korisnik može napraviti eksplicitni password-protected recovery
  paket;
- **Model C:** organizacijski recovery key pod kontrolom administratora.

Ne smije postojati skriveni fallback na plaintext ključ. UI mora jasno objasniti
posljedice reinstalacije ili brisanja Windows profila.

### 3.4 Migracija je transakcija, ne skripta za brisanje

- Plaintext izvor se ne briše dok nova šifrovana kopija nije otvorena pravim
  ključem i dok nisu provjereni schema, integritet i broj ključnih redova.
- Migracija koristi privremeni fajl, atomic rename i rollback marker.
- Ako SQLCipher podržava `ATTACH ... KEY` i `sqlcipher_export`, koristiti taj
  put umjesto učitavanja cijele baze u memoriju.
- Prekid procesa, pogrešan ključ i nedostatak prostora moraju ostaviti čitljivu
  izvornu bazu ili provjeren backup.
- Sigurno fizičko brisanje na SSD-u nije moguće garantovati; dokumentacija ne
  smije tvrditi suprotno.

---

## 4. Revidirani redoslijed faza

| Faza | Tema | Prioritet | Zavisnost | Produkcijski gate |
|---|---|---:|---|---|
| R0 | Baseline, threat model i acceptance freeze | Kritičan | - | Sve naredne faze |
| R1 | Ograničenje `filesystem_search` | Kritičan | R0 | Gate 1 |
| R2 | Legacy PowerShell containment u produkciji | Kritičan | R0 | Gate 0/2 |
| R3 | Windows secret storage + master-key servis | Kritičan | R0 + design review | Gate 2 |
| R4 | SQLCipher baza i bezbjedna migracija | Visok | R3 + SQLCipher go/no-go | Gate 2 |
| R5 | Enkripcija screenshot fajlova | Visok | R3 | Gate 2 |
| R6 | Potpisivanje, update i supply-chain gate | Kritičan | R0 | Gate 2 |
| R7 | BitLocker/FDE detekcija i dokumentacija | Srednji | R0 | Defense in depth |
| R8 | Potpuno uklanjanje legacy puta | Visok | R2 + parity testovi | Gate 2 |
| R9 | Kontinualni Electron i dependency program | Visok | R6 | Kontinualno |
| R10 | Završni nezavisni audit i release odluka | Kritičan | R1-R9 | Production release |

Faze se vode prema zavisnostima i gate-ovima, ne prema kvartalima. R1, R2 i R6
mogu se izvoditi paralelno nakon R0. R4 i R5 ne počinju prije R3.

---

## 5. Faze realizacije

## R0. Baseline, threat model i acceptance freeze

### Cilj

Zaključati stvarno početno stanje prije sigurnosnih izmjena i spriječiti da se
već implementirane kontrole ponovo rade ili oslabe.

### Koraci

1. Ažurirati GitNexus indeks; trenutni indeks je dva commita iza HEAD-a.
2. Evidentirati Security Gate 0/1/2 status prema `MIGRATION_PLAN.md`.
3. Napraviti test-baseline za Python, TypeScript, Electron check, smoke i build.
4. Popisati osjetljive podatke i njihove stvarne lokacije na disku.
5. Popisati produkcijske i razvojne načine pokretanja.
6. Potvrditi threat model iz sekcije 2 i recovery model iz sekcije 3.3.
7. Zabilježiti postojeće kontrole koje se samo održavaju: CSP, secure
   `webPreferences`, localhost auth i production self-test.

### Kriterij prihvatanja

- Baseline izvještaj sadrži rezultate svih provjera i poznata odstupanja.
- Jasno su označeni production blocker-i.
- Recovery model je eksplicitno odobren.
- Nema kodnih izmjena bez zasebnog scope-a i impact analize.

---

## R1. Ograničenje `filesystem_search`

### Odluka dizajna

Ne koristiti jedan alat koji dinamički mijenja rizik na osnovu `scope`
argumenta dok permission engine ima statički `ToolDefinition`. Umjesto toga:

1. `filesystem_search` ostaje restricted alat niskog rizika;
2. zaseban `filesystem_search_extended` je medium risk i uvijek traži potvrdu.

### Default dozvoljeni korijeni

- aplikacijski `data_dir`;
- Desktop, Documents i Downloads;
- korisnički folderi eksplicitno dodani kroz file/folder picker.

Cijeli `Path.home()` i svi diskovi nisu default. Sistem, AppData, browser
profili, SSH, password manager, `.env` i credential lokacije ostaju zabranjeni.

### Koraci

1. Uvesti centralni registry korisnički odobrenih root foldera.
2. Canonicalize/resolve svaku putanju; odbiti symlink/junction escape, UNC i
   zabranjene lokacije.
3. Extended alat prije izvršenja prikazuje tačan spisak rootova i razlog
   pretrage u confirmation dijalogu.
4. Saglasnost vezati za konkretan query i rootove; ne davati trajnu globalnu
   saglasnost preširokog opsega.
5. Rezultate minimizirati: model prvo dobija naziv, tip i relativni/redigovani
   identifikator; puna putanja se otkriva tek kada korisnik izabere rezultat ili
   kada je potrebna za narednu odobrenu radnju.
6. Ograničiti broj rezultata, vrijeme, dubinu, veličinu i broj pregledanih
   čvorova.

### Test gate

- Restricted alat nikad ne napušta allowlisted roots.
- Extended alat se ne izvršava bez validne potvrde.
- Payload hash potvrde obuhvata query i rootove.
- Symlink/junction, UNC, sensitive-dir i cancellation testovi prolaze.
- Model ne dobija pune putanje iz zabranjenih ili neodobrenih lokacija.

---

## R2. Legacy PowerShell containment u produkciji

### Cilj

Odmah zatvoriti mogućnost da se stari runtime put uključi u produkciji, prije
punog brisanja i parity analize.

### Koraci

1. Produkcijski build fizički ne pakuje `electron/tools_legacy/` niti
   `legacyTools.cjs` ako više nisu potrebni za bootstrap.
2. Produkcija ignoriše `RICKY_USE_LEGACY_POWERSHELL_TOOLS`; env flag ne može
   ponovo uključiti legacy OS kontrolu.
3. Security self-test pada ako legacy tool handler ili generic PowerShell put
   postoji/registruje se u packaged buildu.
4. Development fallback ostaviti samo privremeno i eksplicitno označen, dok R8
   ne potvrdi funkcionalni paritet.
5. Rollback je moguć samo kroz source control/release rollback, ne kroz runtime
   feature flag.

### Test gate

- Packaged artifact ne sadrži legacy alate.
- Manipulacija env varijablom ne aktivira legacy put.
- Python permission engine ostaje jedini produkcijski tool executor.

---

## R3. Windows secret storage i master-key servis

### Preduslov: arhitektonski review

Prije implementacije drugi sigurnosni inženjer/agent pregleda samo key lifecycle,
recovery i process boundary. Ovo je prvi, uski nezavisni audit.

### Koraci

1. Uvesti mali Python secret-storage servis sa DPAPI ili Windows Credential
   Manager backendom i testabilnim interfejsom.
2. Generisati i zaštititi stabilni master key; dodati key-id i verziju.
3. Implementirati HKDF izvedene ključeve po namjeni.
4. Premjestiti produkcijske OpenAI/Exa i druge API ključeve iz env-only toka u
   Windows secret storage.
5. Electron ne čita niti prima plaintext API ključ; Python backend je jedini
   vlasnik secret-storage pristupa.
6. Ne logovati ključeve, njihove plaintext dužine, derivirane ključeve ni DPAPI
   blob sadržaj.
7. Implementirati UX za nedostupan/oštećen ključ i odabrani recovery model.
8. Dodati key rotation/re-wrap proceduru bez masovne dekripcije ako backend to
   podržava.

### Test gate

- Tajne nisu u rendereru, localStorage-u, bundlu, `.env` produkcijskog paketa,
  logovima ni crash reportu.
- Restart aplikacije zadržava pristup podacima.
- Drugi Windows korisnik ne može otključati user-scoped DPAPI blob.
- Oštećen/nedostupan ključ daje kontrolisanu grešku, bez kreiranja nove prazne
  baze preko postojeće.
- Recovery test odgovara odabranom modelu.

---

## R4. SQLCipher i bezbjedna migracija SQLite baze

### Go/no-go prije kodiranja

Provjeriti podržan, održavan i redistributabilan SQLCipher paket za stvarnu
Windows/Python verziju produkcijskog sidecar-a. Ako nema pouzdanog wheel-a:

- pinovati podržanu Python verziju za sidecar; ili
- bundle-ovati testiranu SQLCipher biblioteku sa jasnom licencom; ili
- odložiti R4 i privremeno osloniti defense-in-depth na BitLocker + DPAPI.

Ne uvoditi improvizovani `ctypes` binding kao brzi fallback.

### Koraci

1. Apstrahovati otvaranje baze tako da svi repository slojevi koriste jedan
   connection factory.
2. Odmah nakon connect-a postaviti key i provjeriti `cipher_version`.
3. Implementirati migracioni state marker: not-started, in-progress, verified,
   committed, rollback-required.
4. Migrirati kroz SQLCipher export ili drugi streaming mehanizam.
5. Verifikovati `integrity_check`, schema verziju i kontrolne brojeve redova.
6. Tek nakon verifikacije atomically zamijeniti bazu; plaintext backup zadržati
   samo prema eksplicitnoj kratkoj retention politici.
7. Dodati kontrolisan rekey/rotation tok.
8. Definisati backup/export format: šifrovan ili password-protected, nikad
   neoznačeni plaintext.

### Test gate

- Obični `sqlite3` ne može otvoriti bazu.
- Ispravan ključ otvara sve repozitorijume i postojeće podatke.
- Pogrešan ključ ne stvara novu bazu i ne briše postojeću.
- Testovi pokrivaju prekid u svakoj migracionoj fazi, nedostatak prostora,
  oštećen source, ponovljeni startup i rollback.
- Test podaci dokazuju da nema izgubljenih razgovora, potvrda, planova,
  credential metapodataka i screenshot zapisa.

---

## R5. Enkripcija screenshot fajlova

### Format

Koristiti AES-256-GCM i verzionisani envelope, na primjer:

```text
magic | format_version | key_id | nonce | ciphertext | auth_tag
```

Šifrovani fajl ne treba ostaviti sa `.png` ekstenzijom ako ostatak sistema time
pretpostavlja da je validna slika.

### Koraci

1. Screenshot prvo nastaje u memoriji, zatim se šifrovano i atomically upisuje.
2. Dešifrovanje je samo in-memory pri autorizovanom serviranju.
3. Endpoint šalje `Cache-Control: no-store` i ne pravi plaintext temp fajl.
4. Uvesti per-file key derivation ili najmanje unikatan nonce uz strogu zabranu
   nonce reuse-a.
5. Migracija podržava mješovito staro/novo stanje dok se svaki fajl pojedinačno
   ne verifikuje.
6. Retention i delete-on-exit rade nad oba formata tokom migracionog perioda.
7. Plaintext izvor se uklanja tek nakon decrypt-and-compare provjere.

### Test gate

- Fajl na disku nije validan PNG i izmjena jednog bajta pada autentikaciju.
- Endpoint vraća identičan PNG autorizovanom klijentu.
- Pogrešan ključ, prekinuta migracija, mixed-format restart i retention testovi
  prolaze.
- Nema plaintext screenshotova u temp, cache ili log lokacijama.

---

## R6. Code signing, update i supply-chain gate

### Cilj

Zatvoriti veći produkcijski rizik koji originalni roadmap nije uključio:
korisnik mora moći dokazati da installer, Electron aplikacija i Python sidecar
dolaze od očekivanog izdavača i nisu izmijenjeni.

### Koraci

1. Definisati signing certificate, čuvanje privatnog ključa i release pristup.
2. Potpisati Electron executable, Python sidecar i NSIS installer.
3. CI/release provjera odbija nepotpisan ili nevažeće potpisan artifact.
4. Ako auto-update ne može verifikovati HTTPS izvor i potpis manifest/artifacta,
   ostaje potpuno isključen.
5. Generisati checksum manifest i arhivirati ga uz release metadata.
6. Koristiti `npm ci`, lockfile integrity i clean build bez `.env`/runtime data.
7. Dodati `pip-audit` i stvarni `npm audit --audit-level=high` gate.
8. Ispraviti `quality` skriptu tako da audit failure ne bude neutralisan sa
   `|| true` i da operator precedence ne preskače ostatak pipeline-a.
9. Pinovati kritične runtime verzije i dokumentovati kontrolisani dependency
   update proces.
10. Razmotriti SBOM za komercijalnu distribuciju.

### Test gate

- Windows validira potpis svih distribuiranih izvršnih fajlova.
- Izmijenjen artifact ili manifest se odbija.
- Paket ne sadrži `.env`, development token, izvornu bazu, screenshotove ni
  korisničke podatke.
- High/critical npm ili Python nalaz zaustavlja release ili ima formalno
  dokumentovan, vremenski ograničen exception.
- Production self-test je hard fail; DevTools, remote debugging i remote JS su
  isključeni.

---

## R7. BitLocker/FDE detekcija i dokumentacija

### Odluka

Ovo je defense-in-depth indikator, ne hard blocker za startup. Status mora biti
trostan ili četverostan, ne običan bool:

```text
active | inactive | unknown | unavailable
```

### Koraci

1. Detektovati stvarni volumen na kojem se nalazi `data_dir`, ne pretpostaviti
   `C:`.
2. Preferirati strukturirani Windows API/CIM rezultat. Ako se koristi
   PowerShell, koristiti `shell=False`, argument listu, timeout i strukturirani
   izlaz, bez parsiranja lokalizovanog prikaza tabele.
3. Nedostatak privilegija ili nepodržano izdanje Windowsa mapirati na `unknown`
   ili `unavailable`, ne na lažno `inactive`.
4. UI i dokumentacija objašnjavaju šta BitLocker štiti, a šta ne.
5. Detekcija ne blokira startup i ne aktivira legacy/model-facing shell put.

### Test gate

- Testovi pokrivaju active, inactive, unknown, timeout i command unavailable.
- Nema lažnog upozorenja zbog lokalizovanog PowerShell outputa.

---

## R8. Potpuno uklanjanje legacy PowerShell puta

### Koraci

1. Napraviti matricu legacy alat -> Python ekvivalent -> parity status -> test.
2. Ručno i automatski provjeriti click, type, key, scroll, open-app i relevantne
   safety kontrole.
3. Potvrditi da svi Python ekvivalenti prolaze permission engine, active-window,
   confirmation, cancellation, timeout i action receipt tok.
4. Obrisati legacy tool fajlove, registraciju, flagove i zastarjelu dokumentaciju.
5. Security self-test i packaging test trajno provjeravaju da se legacy put ne
   može vratiti slučajnim importom.

### Test gate

- Nema produkcijskog ni development runtime ulaza u legacy PowerShell toolove.
- Nema generičkog shell/PowerShell alata dostupnog modelu.
- Parity matrica je kompletna i testovi prolaze.

---

## R9. Kontinualni Electron i dependency program

### Napomena

CSP i sigurni `webPreferences` već postoje. Ova faza ih ne implementira ponovo,
nego sprečava regresiju.

### Kontrole

1. Mjesečni pregled Electron security release-a i Chromium CVE-a.
2. Kontrolisani update sa punim testovima; ne slijepo automatsko podizanje.
3. Regression self-test za `contextIsolation`, `nodeIntegration`, `sandbox`,
   `webSecurity`, CSP, navigation/window-open i permission handler pravila.
4. Dependency review za nove npm/pip pakete i njihove install skripte.
5. Periodični `npm audit`, `pip-audit`, lockfile review i uklanjanje
   neiskorištenih zavisnosti.
6. Verifikovati Electron fuses i remote module/remote content zabrane u
   produkcijskom artifactu; dodati ih samo gdje provjera pokaže stvaran gap.

### Kriterij prihvatanja

- Postoji vlasnik, ritam i evidencija dependency pregleda.
- Sigurnosne Electron postavke su testirane na stvarnom packaged buildu.
- Audit gate se ne može zaobići operatorom u npm skripti.

---

## R10. Završni nezavisni audit i release odluka

### Dvije audit tačke

1. **R3-design review:** key lifecycle, DPAPI boundary, recovery i migracioni
   protokol prije implementacije R4/R5.
2. **R10 final audit:** code review + ciljano penetraciono testiranje nakon svih
   faza.

### Scope finalnog audita

- Electron renderer/preload/IPC i packaged configuration;
- Python localhost auth i permission engine;
- tool registry, confirmation binding, cancellation i prompt-injection tok;
- filesystem sandbox i extended search;
- secret storage, SQLCipher, screenshot format, backup/recovery;
- legacy containment/removal;
- signing, installer i update chain;
- logging/redaction/retention i production self-test.

Audit paket ne smije sadržati stvarne API ključeve, korisničke baze,
screenshotove, razgovore ili dokumente.

### Release kriterij

Production release je dozvoljen samo kada:

- R1-R9 test gate-ovi prolaze;
- Security Gate 0, 1 i 2 imaju dokumentovan status bez neodobrenog blocker-a;
- nema otvorenog critical/high nalaza bez formalno prihvaćenog rizika;
- incident, recovery, local-data export i delete procedure su testirane;
- potpisani packaged build prolazi production security self-test;
- korisnik/vlasnik projekta odobri release na osnovu završnog izvještaja.

---

## 6. Delegiranje i veličina promjena

Svaka faza je zaseban paket rada i ne smije se spajati u jedan veliki PR.

| Paket | Preporučeni izvođač | Obavezna nezavisna provjera |
|---|---|---|
| R0 | agent za audit/dokumentaciju | vlasnik projekta |
| R1 | Python security agent | permission-engine reviewer |
| R2 | Electron/packaging agent | packaged artifact review |
| R3 | Windows security/crypto agent | nezavisni crypto design review |
| R4 | Python/SQLite agent | migration + recovery review |
| R5 | Python crypto/storage agent | format i endpoint review |
| R6 | Electron release/DevOps agent | signing verification na čistoj mašini |
| R7 | Windows integration agent | test na više Windows izdanja |
| R8 | Electron + Python agent | parity i permission review |
| R9 | održavalac zavisnosti | mjesečni security review |
| R10 | treća strana | vlasnik projekta donosi release odluku |

Za svaki paket obavezni su:

- GitNexus impact prije izmjene simbola;
- scope lock i eksplicitno navedeno šta se ne dira;
- ciljani testovi plus puni quality gate;
- GitNexus detect-changes prije commita;
- agent report sa odlukama, rizicima, testovima i rollbackom;
- ažuriranje `MIGRATION_PLAN.md` samo nakon verifikovanog završetka.

---

## 7. Globalna matrica testiranja

### Obavezno za svaki sigurnosni PR

- Python test suite;
- TypeScript typecheck;
- Electron syntax/check suite;
- React/Vite build;
- voice testovi ako je pogođen Realtime/tool tok;
- smoke test;
- dependency audit;
- packaged-build self-test kada se mijenja Electron, secrets, storage ili
  packaging;
- test da logovi ne sadrže tajne ili plaintext osjetljive podatke.

### Obavezni negativni testovi

- pogrešan i nedostupan ključ;
- restart usred migracije;
- oštećen encrypted fajl;
- symlink/junction escape;
- potvrda za drugi payload/query;
- env pokušaj aktiviranja legacy puta;
- izmijenjen/nepotpisan installer ili sidecar;
- production startup sa oslabljenim CSP/webPreferences;
- audit alat koji nalazi high/critical ranjivost.

---

## 8. Dokumenti koji se ažuriraju nakon usvajanja

Ovaj dokument ne mijenja druge izvore automatski. Nakon korisničkog usvajanja:

1. `docs/SECURITY_INDEX.md` dobija link na ovaj roadmap kao aktivni operativni
   plan, uz napomenu da je `SECURITY_HARDENING_PLAN.md` i dalje izvor pravila.
2. `docs/MIGRATION_PLAN.md` dobija samo potvrđene faze/status, bez unaprijed
   označenih završenih stavki.
3. `docs/SECURITY_MODEL.md` se mijenja samo ako se mijenja risk/permission
   pravilo.
4. Originalni `docs/SECURITY_HARDENING_ROADMAP.md` ostaje sa oznakom
   `superseded`, ali se ne briše.

---

## 9. Šta nije dio ovog roadmapa

- zamjena Electrona drugim GUI stackom;
- ukidanje computer-use funkcionalnosti;
- multi-user RBAC dok proizvod ostaje single-user desktop aplikacija;
- TLS na loopback konekciji, dok backend ostaje striktno na `127.0.0.1` sa
  session auth tokenom;
- cloud backup ključeva bez posebne poslovne i privacy odluke;
- tvrdnja da enkripcija štiti od kompromitovanog aktivnog Windows korisnika.

---

## 10. Definicija završetka cijelog plana

Plan je završen tek kada postoji dokaz, a ne samo implementacija:

```text
sigurne podrazumijevane postavke
+ stabilan i oporavljiv key lifecycle
+ verifikovana migracija bez gubitka podataka
+ minimalan filesystem scope uz eksplicitnu saglasnost
+ nema legacy production bypass-a
+ potpisan i provjeren release chain
+ stvarni dependency gate
+ packaged production self-test
+ nezavisni završni audit
= odluka da je production release dozvoljen
```

