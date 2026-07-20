# FlowOS — detaljan plan realizacije

## 1. Vizija proizvoda

FlowOS je lični operativni sistem za upravljanje radom koji prati način rada jednog korisnika, umjesto da korisnika prisiljava na unaprijed definisan proces. Sistem brzo pretvara misli, obaveze i ideje u strukturirane zadatke, održava kontekst projekata i predlaže realan sljedeći korak.

Osnovna vrijednost proizvoda:

> FlowOS pretvara ono što korisnik ima u glavi u konkretan sljedeći korak i pamti radni kontekst umjesto njega.

FlowOS nije zamjena za Naš-agent. FlowOS je organizacijski i operativni sloj, dok je Naš-agent napredni izvršilac za složene, višekoračne zadatke.

## 2. Glavni ciljevi

1. Omogućiti unos zadatka ili ideje prirodnim jezikom za nekoliko sekundi.
2. Organizovati rad kroz Inbox, Danas, Projekte i Review.
3. Većinu operacija izvršavati bez AI modela ili jeftinim modelom.
4. Uključivati Naš-agent samo kada zadatak zahtijeva napredno rezonovanje, rad s računarom ili više koraka.
5. Sačuvati potpunu kontrolu korisnika nad važnim izmjenama i vanjskim akcijama.
6. Omogućiti lokalni rad i kasnije opcionalnu sinhronizaciju.

## 3. Principi proizvoda

- Minimalan unos, maksimalno korisna struktura.
- Samo informacije relevantne za trenutni rad.
- Jedan jasan sljedeći korak za svaki aktivni projekat.
- AI predlaže; korisnik potvrđuje važne odluke.
- Obični kod obavlja sve determinističke operacije.
- Jeftini model obrađuje jezik, klasifikaciju i kratke sažetke.
- Naš-agent se koristi samo kada njegova dodatna sposobnost opravdava cijenu.
- Sve agentske akcije moraju biti vidljive, provjerljive i evidentirane.
- Modeli nikada ne dobijaju proizvoljan shell ili direktan pristup bazi.

## 4. Ciljni korisnik i početni opseg

Početni korisnik je vlasnik aplikacije: osoba koja paralelno vodi razvojne, poslovne i lične projekte, koristi Naš-agent i želi jednostavniji sistem od ClickUpa.

Prva verzija je single-user desktop aplikacija. Timovi, javni workspaceovi, napredne dozvole, Gantt prikaz i veliki broj integracija nisu dio MVP-a.

## 5. Ključni korisnički tok

Osnovni ciklus:

`Uhvati → Razjasni → Planiraj → Uradi → Pregledaj`

Primjer:

1. Korisnik unese: „Sutra provjeri zašto PZT-EX03 vraća timeout.“
2. Operativni model predloži naslov, datum, projekat, vrstu i prioritet.
3. Backend validira prijedlog i prikazuje ga korisniku.
4. Korisnik potvrdi ili izmijeni stavku.
5. Stavka se pojavljuje u prikazu Danas kada postane relevantna.
6. Ako korisnik zatraži istragu uzroka, zadatak se može predati Naš-agentu.
7. Agentov rezultat se vraća kao izvještaj povezan sa zadatkom i projektom.

## 6. Funkcionalni opseg MVP-a

### 6.1 Inbox

- Brzi tekstualni unos.
- Ručno dodavanje bez AI-ja.
- Opcionalna AI klasifikacija unosa.
- Prijedlog projekta, roka, prioriteta i tipa stavke.
- Prihvatanje, izmjena ili odbijanje AI prijedloga.
- Lista nerazjašnjenih stavki.
- Pretvaranje unosa u zadatak, ideju, bilješku ili podsjetnik.

### 6.2 Danas

- Sekcije Sada, Sljedeće i Kasnije danas.
- Najviše tri preporučene sljedeće aktivnosti.
- Procijenjeno trajanje i prioritet.
- Pokretanje i zaustavljanje fokusne sesije.
- Završavanje, odlaganje ili označavanje blokade.
- Ručno planiranje dana.
- AI prijedlog plana koji korisnik mora potvrditi.

### 6.3 Projekti

- Kreiranje i uređivanje projekta.
- Cilj, status, rok i opis projekta.
- Jedan obavezni sljedeći korak za aktivan projekat.
- Pregled zadataka, bilješki, odluka, fajlova i izvještaja.
- Indikator napretka zasnovan na završenim relevantnim zadacima.
- Evidencija blokada.

### 6.4 Review

- Završeno, blokirano, odloženo i bez sljedećeg koraka.
- Dnevni i sedmični pregled.
- Ručni zaključci i plan za naredni period.
- Kratki AI sažetak aktivnosti.
- Prijedlozi za projekte koji stoje ili zadatke koji se stalno odlažu.

### 6.5 Agent Reports

- Lista zadataka predatih Naš-agentu.
- Statusi: predloženo, odobreno, u toku, završeno, neuspjelo i provjereno.
- Prikaz ulaznog zahtjeva, izvršenih akcija i rezultata.
- Povezivanje izvještaja sa zadatkom i projektom.
- Potvrda korisnika prije rizičnih ili vanjskih akcija.

### 6.6 Pretraga

- Lokalna tekstualna pretraga zadataka, projekata, bilješki i izvještaja.
- Filteri po statusu, projektu, roku i tipu.
- Semantička pretraga tek u kasnijoj fazi.

## 7. GUI struktura

### 7.1 Navigacija

Stalni lijevi sidebar:

- Inbox
- Danas
- Projekti
- Agent Reports
- Review
- Pretraga
- Postavke

### 7.2 Univerzalna komandna traka

Na vrhu aplikacije nalazi se polje „Napiši šta želiš uraditi…“ koje omogućava:

- dodavanje zadatka;
- otvaranje projekta;
- pretragu;
- traženje AI prijedloga;
- predavanje složenog zadatka Naš-agentu.

Komandna traka ne izvršava rizične akcije bez pregleda i potvrde.

### 7.3 Fokusni prikaz

Fokusni prikaz sadrži samo:

- trenutni zadatak;
- cilj i kriterij završetka;
- tajmer;
- kratke bilješke;
- povezane fajlove;
- dugmad Završi, Blokirano i Odloži.

### 7.4 Vizuelni sistem

- Tamna tema kao početna tema.
- Ljubičasta samo za primarne akcije i aktivna stanja.
- Zelena za završeno, narandžasta za odloženo, crvena za blokirano.
- Jasna hijerarhija tipografije i visok kontrast teksta.
- Najviše jedno primarno dugme po prikazu.
- Udobni i kompaktni način prikaza.
- Podrška za tastaturu i komandnu paletu.

## 8. Predložena tehnička arhitektura

### 8.1 Desktop klijent

- Electron kao desktop shell.
- React i TypeScript za korisnički interfejs.
- Tailwind CSS ili postojeći dizajn sistem za stilove.
- TanStack Query za serversko stanje.
- Zustand ili Redux Toolkit samo za lokalno UI stanje ako bude potrebno.

### 8.2 Backend

- Python FastAPI kao vlasnik poslovne logike, AI orkestracije, storagea i integracije s agentom.
- Jasno definisan REST API; WebSocket ili Server-Sent Events za praćenje agentskih poslova.
- Pydantic modeli za validaciju svih ulaza i izlaza.
- Background job runner za izvještaje, podsjetnike i agentske zadatke.

### 8.3 Baza podataka

- SQLite za lokalni MVP.
- SQLAlchemy i Alembic za modele i migracije.
- PostgreSQL kao kasnija opcija za cloud sinhronizaciju.
- Fajlovi ostaju na disku; baza čuva metapodatke i putanje.

### 8.4 Distribucija

- Windows installer.
- Python backend se pakuje uz aplikaciju ili se pokreće kao kontrolisani lokalni servis.
- Automatsko ažuriranje tek nakon stabilnog MVP-a.

## 9. AI arhitektura i kontrola troškova

### 9.1 Nivo 0 — bez modela

Koristi se za:

- CRUD operacije;
- filtere i sortiranje;
- pretragu ključnih riječi;
- računanje rokova i napretka;
- ponavljanje zadataka;
- notifikacije;
- otvaranje ekrana i projekata;
- unaprijed definisane komande.

### 9.2 Nivo 1 — jeftini operativni model

Koristi se za:

- pretvaranje prirodnog jezika u strukturiran unos;
- klasifikaciju stavke;
- prijedlog projekta i oznaka;
- izdvajanje roka i trajanja;
- kratke dnevne i sedmične sažetke;
- prepoznavanje blokade ili odsustva sljedećeg koraka;
- izbor jedne od strogo dozvoljenih aplikacijskih akcija.

Model vraća strogo validiran strukturirani odgovor. Backend nikada ne izvršava nepoznatu akciju.

### 9.3 Nivo 2 — Naš-agent

Koristi se za:

- višekoračno istraživanje;
- rad s drugim aplikacijama;
- analizu koda i dokumenata;
- kreiranje izvještaja;
- složeno planiranje;
- izvršavanje zadatka koji zahtijeva širi kontekst.

Naš-agent komunicira s FlowOS-om prvenstveno kroz kontrolisani API. Vizuelno klikanje po GUI-ju ostaje rezervna mogućnost za aplikacije bez integracije.

### 9.4 Router zahtjeva

Svaki zahtjev prolazi kroz sljedeću odluku:

1. Može li ga pouzdano izvršiti običan kod? Ako može, nema AI poziva.
2. Da li je dovoljna ekstrakcija, klasifikacija ili kratak sažetak? Koristi se operativni model.
3. Da li zahtjev traži više koraka, rad izvan FlowOS-a ili dublju analizu? Nudi se Naš-agent.
4. Da li akcija mijenja vanjski sistem, briše podatke ili nosi veći rizik? Traži se potvrda korisnika.

### 9.5 Mjere kontrole troškova

- Ne slati cijelu historiju modelu.
- Slati samo relevantni projekat i nekoliko povezanih stavki.
- Keširati klasifikacije i sažetke.
- Grupisati sedmične sažetke u jedan poziv.
- Postaviti maksimalan broj tokena po vrsti operacije.
- Evidentirati cijenu, latenciju i uspješnost svakog AI poziva.
- Omogućiti mjesečni budžet i upozorenja.
- Omogućiti potpuno isključivanje AI funkcija.

## 10. Kontrolisani aplikacijski alati

Minimalni skup API akcija dostupnih modelu i Naš-agentu:

- `create_task`
- `get_task`
- `update_task`
- `complete_task`
- `defer_task`
- `mark_task_blocked`
- `search_tasks`
- `create_project`
- `get_project_context`
- `set_next_action`
- `attach_note`
- `attach_report`
- `list_today_items`
- `open_application_view`

Svaka akcija mora imati:

- JSON schema ulaza;
- validaciju dozvola;
- idempotency ključ gdje je relevantno;
- audit zapis;
- jasnu grešku;
- opcionalni zahtjev za potvrdu.

## 11. Početni podatkovni model

### Workspace

- id
- name
- settings
- created_at

### Project

- id
- workspace_id
- title
- description
- goal
- status
- priority
- due_date
- progress
- next_action_task_id
- created_at
- updated_at

### Task

- id
- project_id
- title
- description
- type
- status
- priority
- due_at
- scheduled_for
- estimated_minutes
- actual_minutes
- energy_level
- source
- parent_task_id
- created_at
- updated_at
- completed_at

### InboxItem

- id
- raw_text
- classification
- proposed_payload
- processing_status
- created_at

### Note

- id
- project_id
- task_id
- content
- created_at
- updated_at

### Decision

- id
- project_id
- task_id
- title
- context
- decision
- reason
- created_at

### AgentJob

- id
- project_id
- task_id
- request
- status
- risk_level
- provider
- model
- started_at
- completed_at
- error

### AgentReport

- id
- agent_job_id
- summary
- details
- artifacts
- verification_status
- created_at

### AuditEvent

- id
- actor_type
- actor_id
- action
- entity_type
- entity_id
- payload
- created_at

### ModelUsage

- id
- operation_type
- provider
- model
- input_tokens
- output_tokens
- estimated_cost
- latency_ms
- success
- created_at

## 12. Sigurnost i privatnost

- Lokalna baza kao zadana opcija.
- Tajne se čuvaju u Windows Credential Manageru ili sigurnom keychain sloju.
- API ključevi se nikada ne čuvaju u repozitoriju ili običnim konfiguracijskim fajlovima.
- Backend prihvata zahtjeve samo od lokalnog desktop klijenta uz autentikacijski token sesije.
- Model dobija najmanji mogući kontekst.
- Osjetljiva polja se mogu označiti kao „ne šalji modelu“.
- Sve agentske akcije se evidentiraju.
- Brisanje, masovne izmjene i vanjske akcije zahtijevaju potvrdu.
- Ne postoji proizvoljni shell tool dostupan modelu.
- Backup i restore moraju biti testirani prije produkcijske upotrebe.

## 13. Faze realizacije

### Faza 0 — otkrivanje stvarnog workflowa (1–2 sedmice)

Cilj: dokumentovati kako korisnik zaista radi.

Aktivnosti:

- Bilježiti sve ulaze, odluke, odlaganja i blokade tokom najmanje sedam dana.
- Popisati postojeće alate i mjesta gdje se informacije gube.
- Definisati deset najčešćih komandi prirodnim jezikom.
- Definisati minimalna obavezna polja zadatka i projekta.
- Validirati GUI tokove na klikabilnom prototipu.

Rezultat:

- workflow mapa;
- prioritetni user stories;
- potvrđen MVP opseg;
- početni dizajn sistem.

Kriterij završetka: najmanje 80% svakodnevnih radnih situacija može se mapirati na Inbox, Danas, Projekti ili Review.

### Faza 1 — tehnički temelj (1 sedmica)

Aktivnosti:

- Postaviti Electron/React/TypeScript shell.
- Postaviti FastAPI backend.
- Dodati SQLite, SQLAlchemy i Alembic.
- Definisati API ugovor i standard grešaka.
- Dodati health check i kontrolisano pokretanje backenda.
- Postaviti testove, lint, formatiranje i CI.

Kriterij završetka: desktop aplikacija pouzdano pokreće backend, provjerava njegovo stanje i izvršava osnovni read/write poziv.

### Faza 2 — funkcionalni MVP bez AI-ja (3–4 sedmice)

Aktivnosti:

- Implementirati Inbox.
- Implementirati zadatke i projekte.
- Implementirati prikaz Danas.
- Implementirati Review.
- Dodati lokalnu pretragu.
- Dodati fokusnu sesiju.
- Dodati osnovne postavke, backup i restore.
- Dodati audit događaje za izmjene.

Kriterij završetka: korisnik može najmanje dvije sedmice voditi svakodnevni rad bez drugog task managera i bez AI funkcija.

### Faza 3 — operativni AI model (2–3 sedmice)

Aktivnosti:

- Uvesti provider-neutralan AI adapter.
- Implementirati strukturiranu klasifikaciju Inbox unosa.
- Dodati ekstrakciju datuma, projekta, prioriteta i procjene trajanja.
- Dodati pregled i potvrdu prije upisa.
- Implementirati router nivoa 0/1/2.
- Dodati dnevni i sedmični sažetak.
- Dodati evidenciju tokena, troška, latencije i grešaka.
- Napraviti evaluacijski skup stvarnih korisničkih unosa.

Kriterij završetka: najmanje 90% testnih unosa proizvodi validan JSON, najmanje 85% dobija ispravnu klasifikaciju, a nijedna nepoznata akcija se ne izvršava.

### Faza 4 — integracija Naš-agenta (3–4 sedmice)

Aktivnosti:

- Definisati kontrolisani FlowOS API za agenta.
- Implementirati AgentJob i AgentReport tok.
- Dodati korisničko odobrenje delegiranja.
- Prikazivati status rada u realnom vremenu.
- Omogućiti agentu povezivanje izvještaja, bilješki i artefakata.
- Dodati provjeru završetka i ručnu potvrdu rezultata.
- Testirati prekide, timeout, ponavljanje i djelimični uspjeh.

Kriterij završetka: agent može primiti zadatak, ažurirati status i vratiti provjerljiv izvještaj bez direktnog pristupa bazi i bez oslanjanja na GUI automatizaciju FlowOS-a.

### Faza 5 — pamćenje konteksta i inteligentni Review (3 sedmice)

Aktivnosti:

- Dodati odluke i razloge kao zasebne entitete.
- Generisati projektni kontekst iz relevantnih podataka.
- Dodati detekciju projekata bez sljedećeg koraka.
- Dodati detekciju ponovljenog odlaganja.
- Uvesti semantičku pretragu samo ako obična pretraga nije dovoljna.
- Dodati mjerenje kvaliteta preporuka.

Kriterij završetka: sistem može objasniti iz kojih podataka je nastao prijedlog i korisnik može ispraviti ili odbiti zaključak.

### Faza 6 — stabilizacija i distribucija (2–3 sedmice)

Aktivnosti:

- Optimizovati vrijeme pokretanja i odziv GUI-ja.
- Testirati instalaciju, nadogradnju i deinstalaciju.
- Testirati migracije baze.
- Uvesti automatske i ručne backup procedure.
- Dodati recovery nakon pada procesa.
- Završiti pristupačnost i keyboard navigaciju.
- Pripremiti privatnu beta verziju.

Kriterij završetka: aplikacija prolazi instalacijski, migracijski, backup/restore i smoke test na čistom Windows okruženju.

## 14. Prioritetni user stories

### P0 — obavezno za MVP

- Kao korisnik mogu brzo unijeti misao bez popunjavanja forme.
- Mogu razjasniti Inbox stavku i pretvoriti je u zadatak.
- Mogu vidjeti realan plan za danas.
- Mogu označiti zadatak završenim, odloženim ili blokiranim.
- Mogu kreirati projekat i postaviti sljedeći korak.
- Mogu pregledati završene, blokirane i zaboravljene stavke.
- Mogu pronaći zadatak ili projekat lokalnom pretragom.
- Mogu napraviti i vratiti backup.

### P1 — AI i agent

- Mogu unijeti zadatak prirodnim jezikom i dobiti strukturiran prijedlog.
- Mogu prihvatiti ili ispraviti AI klasifikaciju.
- Mogu tražiti prijedlog dnevnog plana.
- Mogu delegirati složen zadatak Naš-agentu.
- Mogu pratiti šta agent radi i pregledati rezultat.
- Mogu vidjeti procijenjeni AI trošak.

### P2 — kasnije

- Semantička pretraga.
- Cloud sinhronizacija.
- Mobilni capture klijent.
- GitHub, Drive, email i kalendar integracije.
- Više workspaceova.
- Personalizacija preporuka na osnovu ponašanja.

## 15. Test strategija

### Backend

- Unit testovi poslovnih pravila.
- API integracijski testovi.
- Testovi migracija baze.
- Testovi idempotentnosti agentskih akcija.
- Testovi validacije nepoznatih i rizičnih akcija.

### Frontend

- Testovi ključnih komponenti.
- Testovi navigacije i formi.
- End-to-end testovi za Inbox → Danas → Završeno.
- End-to-end testovi za delegiranje agentu.
- Testovi keyboard navigacije.

### AI evaluacija

- Verziran skup stvarnih unosa s očekivanim strukturiranim izlazom.
- Mjerenje tačnosti klasifikacije i ekstrakcije.
- Mjerenje stope ručnih ispravki.
- Testovi prompt injection pokušaja.
- Testovi praznih, dvosmislenih i kontradiktornih zahtjeva.
- Regresijski test prije promjene modela ili prompta.

### Operativni testovi

- Pad backenda tokom upisa.
- Prekid mreže tokom modelskog poziva.
- Timeout agentskog zadatka.
- Duplo slanje iste akcije.
- Oštećena ili zastarjela baza.
- Backup i potpuni restore.

## 16. Metrike uspjeha

### Produktne metrike

- Vrijeme od unosa do organizovane stavke: manje od 10 sekundi.
- Najmanje 80% Inbox stavki razjašnjeno u 24 sata.
- Najmanje 90% aktivnih projekata ima sljedeći korak.
- Smanjenje broja stalno odlaganih zadataka.
- Sedmični Review završen u manje od 15 minuta.

### AI metrike

- Validan strukturirani odgovor u najmanje 99% poziva.
- Tačnost klasifikacije najmanje 85% prije šire upotrebe.
- Stopa prihvatanja AI prijedloga najmanje 70%.
- Nula izvršenih akcija izvan dozvoljenog registra alata.
- Praćen trošak po operaciji i po mjesecu.

### Tehničke metrike

- Lokalna CRUD operacija ispod 200 ms u uobičajenom radu.
- Pokretanje aplikacije ispod 5 sekundi na ciljnom računaru.
- Nula gubitka potvrđenih podataka u testovima oporavka.
- Uspješnost agentskih poslova mjerena po vrsti zadatka.

## 17. Upravljanje troškovima

Troškovi se dijele na razvoj, AI korištenje, hosting i održavanje.

Za MVP treba izbjegavati cloud infrastrukturu gdje nije neophodna:

- lokalni Electron i FastAPI;
- SQLite;
- korisnikov API ključ ili strogo ograničen projektni ključ;
- bez stalno aktivnog cloud backenda;
- bez vektorske baze dok ne postoji izmjerena potreba;
- bez skupog modela za rutinske operacije.

U postavkama prikazati:

- broj poziva po modelu;
- procijenjeni dnevni i mjesečni trošak;
- limit potrošnje;
- mogućnost isključivanja sažetaka i automatske klasifikacije;
- pravila kada je dozvoljeno ponuditi Naš-agent.

## 18. Glavni rizici i ublažavanje

### Preširok opseg

Rizik: proizvod preraste u novi ClickUp prije nego što riješi osnovni problem.

Ublažavanje: svaka nova funkcija mora direktno poboljšati ciklus Uhvati → Razjasni → Uradi → Pregledaj.

### Pretjerano oslanjanje na AI

Rizik: veća cijena, sporiji odziv i nepredvidive odluke.

Ublažavanje: deterministički kod kao zadani put; model samo za jezičke zadatke.

### Pogrešne agentske akcije

Rizik: izmjena pogrešnog zadatka ili vanjskog sistema.

Ublažavanje: dozvoljeni alati, validacija, audit, idempotency i potvrda korisnika.

### Nekvalitetne preporuke

Rizik: korisnik prestaje vjerovati sistemu.

Ublažavanje: prikaz razloga prijedloga, jednostavna ispravka i mjerenje prihvatanja.

### Gubitak lokalnih podataka

Rizik: aplikacija postaje nepouzdana za svakodnevni rad.

Ublažavanje: transakcije, migracije, automatski backup i testiran restore.

### GUI automatizacija

Rizik: klikovi zavise od rasporeda elemenata i lako se kvare.

Ublažavanje: Naš-agent upravlja FlowOS podacima preko API-ja; GUI automatizacija se koristi samo za vanjske aplikacije bez integracije.

## 19. Predloženi razvojni backlog za prvi sprint

1. Potvrditi naziv i granice MVP-a.
2. Dokumentovati deset stvarnih dnevnih scenarija.
3. Definisati entitete Project, Task i InboxItem.
4. Definisati API ugovor za Inbox i zadatke.
5. Napraviti navigacijski shell prema mockupu.
6. Implementirati lokalno kreiranje Inbox stavke.
7. Implementirati pretvaranje stavke u zadatak.
8. Implementirati prikaz Danas.
9. Dodati osnovne backend i end-to-end testove.
10. Provesti petodnevni dogfooding i zapisati sva trenja.

## 20. Odluke koje treba donijeti prije početka razvoja

- Da li FlowOS nastaje kao modul postojećeg Naš-agent repozitorija ili kao zaseban repozitorij?
- Da li je aplikacija isključivo lokalna u prvoj godini ili se planira rana sinhronizacija?
- Koji operativni model i provider daju najbolji odnos cijene, latencije i strukturiranog izlaza?
- Da li korisnik koristi vlastiti API ključ?
- Koje akcije Naš-agent smije izvršiti bez dodatne potvrde?
- Koji podaci se nikada ne smiju slati modelu?
- Da li je mobilni capture potreban nakon desktop MVP-a?

## 21. Preporučeni redoslijed odluka

1. Validirati lični workflow bez pisanja kompleksnog koda.
2. Izgraditi potpuno upotrebljiv MVP bez AI-ja.
3. Izmjeriti gdje AI stvarno štedi vrijeme.
4. Dodati jeftini model samo na ta mjesta.
5. Integrisati Naš-agent kroz kontrolisani API.
6. Tek nakon višesedmičnog svakodnevnog korištenja razmatrati cloud, mobilnu aplikaciju i vanjske integracije.

## 22. Definicija uspješnog MVP-a

MVP je uspješan kada korisnik tokom dvije uzastopne sedmice može:

- sve nove obaveze uhvatiti u FlowOS;
- planirati i izvršavati dnevni rad;
- održavati jasan sljedeći korak za svaki aktivni projekat;
- završiti sedmični Review;
- pronaći prethodne odluke i izvještaje;
- delegirati najmanje jednu složenu aktivnost Naš-agentu;
- vratiti podatke iz backupa;
- sve navedeno raditi bez potrebe za paralelnim task managerom.

## 23. Okvirna procjena trajanja

Za jednog developera koji radi fokusirano:

- validacija i dizajn: 1–2 sedmice;
- tehnički temelj: 1 sedmica;
- MVP bez AI-ja: 3–4 sedmice;
- operativni model: 2–3 sedmice;
- integracija Naš-agenta: 3–4 sedmice;
- stabilizacija i installer: 2–3 sedmice.

Ukupno: približno 12–17 sedmica do stabilne privatne beta verzije. Prva korisna lokalna verzija bez AI-ja može biti spremna za 4–7 sedmica.

Procjena pretpostavlja mali, disciplinovan opseg i ne uključuje timske funkcije, cloud sinhronizaciju, mobilnu aplikaciju ni veliki broj integracija.

## 24. Konačna preporuka

FlowOS treba prvo dokazati da je odličan lični sistem rada, a tek zatim postati širi proizvod. Najvažnija tehnička odluka je zadržati tri jasno odvojena sloja:

`Deterministički backend → jeftini operativni model → Naš-agent za složene zadatke`

Ovakva podjela smanjuje cijenu, poboljšava brzinu i čini sistem predvidivijim. Naš-agent dobija ulogu naprednog izvršioca, dok FlowOS ostaje pouzdano mjesto na kojem korisnik vidi, planira i kontroliše svoj rad.
