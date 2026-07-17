# Plans Panel product plan

Datum: 2026-07-16
Autor: Codex
Status: arhivirani plan za implementaciju

## Cilj

Panel "Planovi" treba da bude radni prostor gdje korisnik i agent zajedno vode zadatke koji imaju vise od jednog koraka. To nije samo lista podsjetnika. To je kontrolna tabla za namjeru, odobrenje, izvrsenje, status i zavrsni izvjestaj.

Trenutni UI vec pokazuje dobar osnovni model:

- Aktivni
- Predlozeni
- Zavrseni
- Novi plan

Plan je da se taj kostur poveze sa stvarnim agent runtime-om, confirmation sistemom, activity logom i dugorocnom memorijom.

## Zasto panel postoji

Agent trenutno moze izvrsavati pojedinacne komande, traziti potvrde i raditi kroz alate. Problem nastaje kada korisnik trazi nesto sto ima vise koraka, vise odluka ili moze trajati duze od jednog razgovornog okreta.

Primjeri:

- "Povezi Brave, Chrome i Edge sa agentom i testiraj tabove."
- "Napravi plan za C4 hardening i provjeri testove."
- "Podsjeti me sutra da testiram browser ekstenziju."
- "Pripremi dokument, provjeri ga, pa me pitaj prije slanja."
- "Otvori browser, idi na stranicu, napravi izvjestaj i sacuvaj rezultat."

Bez plana, agent moze izgubiti kontekst, korisnik ne vidi sta je vec uradjeno, a potvrde djeluju kao izolovani prekidi. Panel treba da pretvori takve zadatke u vidljiv, kontrolisan tok.

## Osnovni model

Plan ima ove obavezne podatke:

- `plan_id`: stabilni identitet plana.
- `title`: kratki naziv plana.
- `description`: sta korisnik zeli postici.
- `status`: `proposed`, `active`, `paused`, `blocked`, `completed`, `cancelled`, `failed`.
- `risk_level`: `low`, `medium`, `high`, `critical`.
- `created_at`, `updated_at`, `completed_at`.
- `created_by`: `user` ili `agent`.
- `owner_agent`: trenutno ime agenta koji vodi plan.
- `source`: glas, tekst, sistemski event ili rucno kreiran plan.
- `steps`: lista koraka.
- `artifacts`: povezani fajlovi, izvjestaji, screenshotovi ili rezultati.
- `related_confirmations`: potvrde koje su trazene ili iskoristene.
- `activity_refs`: linkovi na activity log dogadjaje.

Korak plana ima:

- `step_id`
- `title`
- `description`
- `status`: `pending`, `running`, `waiting_for_user`, `blocked`, `done`, `skipped`, `failed`
- `tool_name`: opcionalno, ako je korak vezan za tool
- `expected_result`
- `actual_result`
- `requires_confirmation`
- `error_code`
- `started_at`, `finished_at`

## Tabovi u panelu

### Aktivni

Ovdje se prikazuju planovi koje je korisnik prihvatio ili rucno napravio i koji jos nisu zavrseni.

Aktivni plan treba pokazati:

- naziv i kratak opis;
- trenutni status;
- sljedeci korak;
- napredak, npr. "3/7 koraka";
- da li ceka korisnika;
- da li je blokiran;
- dugmad: Nastavi, Pauziraj, Otvori detalje, Otkazi.

Agent smije automatski nastaviti samo korake koji su unutar vec odobrenog plana i ne zahtijevaju novu potvrdu. Ako korak prelazi rizik plana ili mijenja namjeru, plan mora preci u `waiting_for_user`.

### Predlozeni

Ovdje dolaze planovi koje agent predlozi prije vece akcije.

Predlozeni plan treba imati:

- jasan cilj;
- listu koraka;
- rizik;
- sta ce se promijeniti na sistemu;
- koje potvrde ce vjerovatno biti potrebne;
- dugmad: Prihvati, Izmijeni, Odbij.

Agent treba predloziti plan kada:

- zadatak ima vise od 2-3 koraka;
- ukljucuje vanjske aplikacije, browser, fajlove, email ili instalaciju;
- ukljucuje high/critical tool;
- postoji vise mogucih puteva;
- korisnik trazi "napravi plan", "organizuj", "zavrsi ovo", "radi dok ne bude gotovo".

Predlozeni plan ne smije biti samo dekoracija. Dok korisnik ne prihvati plan, agent ne smije izvrsavati njegove akcione korake osim bezopasne analize.

### Zavrseni

Ovdje ide arhiva zavrsenih, otkazanih i neuspjelih planova.

Za zavrseni plan prikazati:

- sta je korisnik trazio;
- sta je uradjeno;
- koji koraci su prosli;
- koji testovi ili provjere su pokrenuti;
- linkove na izvjestaje i artefakte;
- preostale rizike ili follow-up.

Ovo je posebno vazno za razvojne faze projekta. Kada se zavrsi C1, C2, C3 ili C4, plan moze automatski sacuvati mini izvjestaj i povezati ga sa `agent_reports/`.

## Dugme "Novi plan"

`Novi plan` treba otvoriti mali modal ili inline formu:

- Naziv plana
- Opis
- Tip: zadatak, podsjetnik, razvojna faza, provjera, licni plan
- Prioritet
- Rok ili podsjetnik, opcionalno
- Da li agent smije predloziti korake automatski

Nakon kreiranja, agent moze ponuditi generisane korake:

"Napravio sam plan. Predlazem 5 koraka. Da ih dodam?"

Za netehnicke korisnike forma mora biti kratka. Napredna polja treba sakriti iza "Vise opcija".

## Bolji tok od trenutnog

Trenutni panel izgleda kao prazna tabla sa tabovima. To je u redu kao UI kostur, ali treba dodati tri stvari da bi postao stvarno koristan:

1. Vidljiv "next action"

Korisnik uvijek treba znati sta se sada ceka:

- "Ceka tvoje odobrenje."
- "Agent pokrece testove."
- "Plan je blokiran: ekstenzija nije povezana."
- "Sljedeci korak: otvori Brave i potvrdi pairing."

2. Plan povezan sa potvrdama

Ako tool trazi potvrdu, confirmation dialog treba prikazati iz kog plana i kog koraka dolazi.

Primjer:

"Plan: Browser Bridge C2"
"Korak 4: Otvori novi tab u Chrome profilu"

Kada korisnik klikne Approve, plan treba automatski dobiti rezultat tog koraka.

3. Zavrsni receipt

Kada se plan zavrsi, panel treba napraviti kratak "receipt":

- cilj;
- rezultat;
- testovi;
- fajlovi;
- sta je ostalo.

To se moze prikazati u UI i po potrebi sacuvati u `agent_reports/`.

## Integracija sa postojecim sistemom

### Backend

Postojeci plans backend treba biti vlasnik stanja plana. UI ne treba sam odlucivati da li je plan zavrsen. UI samo prikazuje stanje i salje korisnikove odluke.

Potrebni endpointi ili IPC putanje:

- list plans by status;
- create plan;
- update plan title/description;
- accept proposed plan;
- reject proposed plan;
- pause/resume/cancel active plan;
- update step status;
- attach artifact/report;
- complete plan;
- archive plan.

### Agent runtime

Agent treba dobiti pravilo:

- za vece zadatke prvo predlozi plan;
- za prihvacen plan izvrsavaj korak po korak;
- nakon svakog vaznog koraka azuriraj plan;
- kada korisnik odobri akciju, povezi rezultat sa aktivnim korakom;
- ako se okolnosti promijene, pauziraj i pitaj korisnika.

### Activity timeline

Activity timeline ostaje detaljan dnevnik dogadjaja. Plans panel je sazet pregled cilja i napretka.

Ne treba duplirati sve evente u plan. Plan cuva samo relevantne reference.

### Confirmations

Confirmation sistem mora znati:

- `plan_id`
- `step_id`
- `tool_name`
- `payload_hash`

Tako se izbjegava situacija da korisnik odobri jednu stvar, a agent ili backend izvrsi drugu.

### Agent reports

Za razvojne zadatke, zavrseni plan moze ponuditi:

- "Sacuvaj kao agent report"
- "Dodaj u migration tracker"
- "Oznaci fazu kao zavrsenu"

Ovo ne smije biti potpuno automatsko za tracker. Tracker je izvor istine i izmjena treba ici kroz normalnu provjeru.

## UX detalji

Kartica plana treba biti kompaktna:

- naslov;
- status pill;
- napredak;
- sljedeci korak;
- zadnji rezultat;
- jedna primarna akcija.

Detalji plana mogu biti drawer/modal:

- lijevo koraci;
- desno detalji izabranog koraka;
- dno: activity i artefakti.

Za prazan panel, tekst treba biti konkretniji od "Napravi novi plan kada zelis da Ricky prati zadatke."

Bolji prazan state:

"Planovi su za zadatke koji imaju vise koraka. Napravi plan za instalaciju, provjeru, podsjetnik ili razvojnu fazu."

## Sigurnosna pravila

- Plan nije dozvola za sve.
- High/critical alati i dalje traze confirmation.
- Plan ne smije sakriti rizik od korisnika.
- Ako se payload promijeni, potvrda vise ne vazi.
- Ako plan cilja jedan browser/profil, koraci ne smiju preskociti na drugi bez novog odobrenja.
- Zavrseni plan mora prikazati neuspjehe, ne samo uspjehe.

## Implementacione faze

### P0 — stabilizacija postojeceg panela — zavrseno

- Provjeriti da tabovi Aktivni/Predlozeni/Zavrseni stvarno filtriraju backend stanje.
- `Novi plan` mora kreirati stvaran plan, ne samo UI placeholder.
- Prazna stanja napisati jasnije.
- Dodati loading i error stanja.
- Dodati refresh nakon kreiranja/izmjene plana.

Status 2026-07-16: korisnik je prijavio da je P0 zavrsen. Potrebna je jos lokalna verifikacija kroz kod i testove kada shell bude dostupan.

Acceptance:

- korisnik kreira plan;
- plan se pojavi u Aktivni ili Predlozeni;
- refresh aplikacije ne izgubi plan;
- zavrsen plan prelazi u Zavrseni.

### P1 — koraci plana

- Dodati UI za listu koraka.
- Dodati status po koraku.
- Dodati "sljedeci korak".
- Dodati run/pause/cancel komande.
- Backend cuva step state.

Acceptance:

- plan sa 5 koraka prikazuje napredak;
- korak moze preci pending -> running -> done;
- blokiran korak jasno prikazuje razlog.

### P2 — agent proposed plans — završeno

- Agent predlaze plan za visekoracne zadatke.
- Plan ulazi u Predlozeni.
- Korisnik moze prihvatiti, odbiti ili traziti izmjene.
- Agent ne izvrsava akcione korake dok plan nije prihvacen.

Acceptance:

- korisnik kaze "povezi browsere i testiraj";
- agent napravi predlozeni plan;
- nakon prihvatanja plan prelazi u Aktivni.

Status 2026-07-16:

- create_plan je registrovan kao backend tool i dostupan agentu kroz Realtime tool spec;
- alat kreira plan u Predloženi tab bez computer-mode zahtjeva;
- dodani su regression testovi za registry i `/tools/execute` tok.

### P3 — confirmations + plans binding

- Confirmation dialog prikazuje plan i korak.
- Approval rezultat se vraca u odgovarajuci step.
- Odbijanje potvrde blokira ili preskace korak, zavisno od korisnikove odluke.

Acceptance:

- korisnik odobri akciju;
- agent zna da je odobrenje primljeno;
- plan prikazuje rezultat tog koraka.

### P4 — artifacts, reports i receipts

- Plan moze imati povezane artefakte.
- Zavrseni plan dobija receipt.
- Development plan moze ponuditi agent report draft.

Acceptance:

- zavrseni plan prikazuje testove i fajlove;
- korisnik moze otvoriti povezani report;
- neuspjeli koraci ostaju vidljivi.

### P5 — podsjetnici — završeno

- Plan moze imati datum/rok.
- UI prikazuje overdue/upcoming.
- Agent moze podsjetiti korisnika u aplikaciji.

Acceptance:

- korisnik napravi podsjetnik;
- plan se pojavi kao upcoming;
- kad rok prodje, prikazuje se kao overdue.

Status 2026-07-17:

- `due_at` je zasebno plans storage/API polje, ne skriveni title prefix;
- UI prikazuje datum i hitnost roka te sortira planove po roku;
- `create_plan` tool i Realtime prompt podržavaju agentovo kreiranje planova sa rokom/podsjetnikom.

## Prioriteti

Najvaznije prvo:

1. `Novi plan` mora stvarno kreirati i cuvati plan.
2. Aktivni/Predlozeni/Zavrseni moraju prikazivati stvarne podatke.
3. Koraci i status po koraku.
4. Binding sa confirmation sistemom.
5. Agent automatski predlaze planove.
6. Zavrsni receipt i arhiva.
7. Podsjetnici.

## Rizici

- Ako panel ostane samo UI lista, korisnik ce ga ignorisati.
- Ako agent automatski kreira previse planova, panel ce postati spam.
- Ako plan daje presiroku dozvolu, sigurnosni model slabi.
- Ako se ne poveze sa confirmation rezultatima, korisnik nece imati povjerenje da agent zna sta je odobreno.
- Ako nema zavrsnog receipt-a, panel nece pomagati kod razvoja i dugih zadataka.

## Preporuka

Ne praviti od ovoga genericki project management alat. Ovaj panel treba biti "agent task control center": malo, jasno, povezano sa stvarnim radnjama agenta.

Najbolja verzija panela je ona gdje korisnik u svakom trenutku vidi:

- sta agent pokusava uraditi;
- koji je sljedeci korak;
- da li nesto ceka korisnika;
- sta je vec zavrseno;
- gdje su dokazi rezultata.

To direktno rjesava najvecu vrijednost ovog proizvoda: agent nije crna kutija, nego saradnik ciji rad korisnik moze pratiti, odobriti, pauzirati i zavrsiti.
