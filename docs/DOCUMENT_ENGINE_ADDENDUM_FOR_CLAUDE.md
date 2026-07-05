# ADDENDUM — Document/Paperwork Engine kao Future Epic

## Svrha dodatka

Ovaj dodatak treba ubaciti u postojeći plan/arhitekturu bez razbijanja trenutnog `MIGRATION_PLAN.md` trackera.

Cilj dodatka nije da odmah pokrene implementaciju Document/Paperwork Engine-a, nego da pravilno smjesti tu ideju u plan kao **future epic** sa jasnim zavisnostima, privacy pravilima i bez konflikta numeracije faza.

---

# Ključna odluka

Document/Paperwork Engine je legitiman i vrijedan smjer, ali **nije dio trenutnog MVP-a**.

Trenutni prioritet ostaje:

```txt
Core Ricky MVP:
- postojeći src/lib/realtime.ts ostaje voice/audio pipeline,
- Python backend skeleton,
- Realtime session security,
- voice-first UI,
- Activity timeline,
- Plans/Confirmations,
- safe local tools,
- Companion orb voice integration.
```

Document/Paperwork Engine dolazi poslije toga kao zaseban future epic.

---

# Problem koji treba ispraviti

U prethodnom dodatku su predložene faze:

```txt
FAZA 11 — Context Pack MVP
FAZA 12 — Document Ingest MVP
FAZA 13 — Chunk + Normalize MVP
FAZA 14 — Citation Map
FAZA 15 — Review Packet Builder
FAZA 16 — Action Receipt + Gate
FAZA 17 — Runbooks
```

Ovo ne treba zadržati kao numerisane faze.

Razlog:

```txt
docs/MIGRATION_PLAN.md već ima svoju postojeću numeraciju.
Ako svaki novi arhitektonski dokument dodaje svoje FAZA 11-17,
faze će se stalno sudarati i plan će postati neodrživ.
```

Nova pravila:

```txt
1. Samo MIGRATION_PLAN.md smije dodjeljivati konačne brojeve faza.
2. Arhitektonski dodatak smije definisati future epic, zavisnosti i redoslijed unutar epica.
3. Ne uvoditi nove brojeve faza u ARCHITECTURE dokumentu.
4. Document Engine treba opisati kao Future Epic / Backlog item.
5. Konačne brojeve dodijeliti tek kada se epic stvarno spaja u MIGRATION_PLAN.md.
```

---

# Šta treba promijeniti u postojećem dokumentu

## 1. Zamijeniti numerisane faze future epic-om

Ako dokument sadrži sekciju:

```txt
# Dodatne faze za Document/Paperwork Engine
FAZA 11...
FAZA 12...
...
FAZA 17...
```

zamijeni je sa:

```txt
# Future Epic — Document / Paperwork Engine

Document/Paperwork Engine je budući proizvodni sloj, ne aktivna MVP faza.

Ne dodjeljivati mu brojeve faza u ovom dokumentu.
Konačnu numeraciju određuje MIGRATION_PLAN.md kada korisnik/integrator odluči da epic ulazi u aktivan rad.
```

---

# Future Epic — Document / Paperwork Engine

## Namjena

Document/Paperwork Engine služi da Ricky od neurednih fajlova, dokumenata, PDF-ova, screenshotova, email attachmenta i bilješki napravi:

```txt
Review Packet
+ Action Receipt
+ Citation Map
+ Missing Items Checklist
+ Human Approval Gate
```

Glavni princip:

```txt
Agent ne klikće finalno dugme.
Agent priprema pregledan, citiran i provjerljiv paket za čovjeka.
```

Ricky ne smije samostalno:

```txt
- poslati email,
- predati obrazac,
- potpisati dokument,
- platiti,
- poslati osjetljive dokumente trećoj strani,
- napraviti nepovratnu akciju.
```

---

# Generički skeleton

Document Engine koristi isti skeleton kroz različite domene:

```txt
Context Pack
→ Ingest
→ Chunk
→ Normalize
→ Store
→ Retrieve
→ Cite
→ Export
→ Gate
```

Ovo nije specifično za jedan domen.

Primjeri domena:

```txt
- računi,
- ugovori,
- porezi,
- osiguranje,
- medicinska dokumentacija,
- carinska dokumentacija,
- poslovna evidencija,
- obrazovni formulari,
- administrativni zahtjevi.
```

---

# Dependency pravila

Document/Paperwork Engine ne ulazi u aktivan rad dok nisu stabilni:

```txt
- Python backend skeleton,
- Realtime session security,
- voice-first UI,
- Activity timeline,
- transcript/activity persistence,
- Plans/Confirmations,
- osnovni SQLite storage,
- basic permission/risk policy,
- safe local tool execution,
- Companion orb voice integration ako se koristi u UX-u.
```

Drugim riječima:

```txt
Document Engine zavisi od stabilnog voice/control/storage temelja.
```

Ne implementirati Document Engine prije nego što postoje:

```txt
1. backend koji može čuvati activity,
2. confirmation_id mehanizam,
3. plan/proposal storage,
4. permission/risk layer,
5. jasan UI za Output/Activity/Plans.
```

---

# Privacy Model za dokumente

Ovo je obavezna dopuna.

Document/Paperwork Engine mora imati jasan privacy model, jer dokumenti mogu sadržati:

```txt
- medicinske podatke,
- poreske podatke,
- bankovne podatke,
- lične identifikacione podatke,
- ugovore,
- carinske dokumente,
- poslovne tajne,
- podatke trećih lica.
```

## Context Pack mora imati privacy_mode

Svaki Context Pack mora imati polje:

```txt
privacy_mode
```

Dozvoljene vrijednosti:

```txt
cloud_allowed
redacted_cloud
local_only
ask_each_time
```

## cloud_allowed

```txt
Dokument ili njegov sadržaj smije ići cloud modelu.
Korisnik je eksplicitno dozvolio obradu.
```

Koristiti za manje osjetljive dokumente ili kada korisnik zna šta radi.

## redacted_cloud

```txt
Prije slanja cloud modelu pokušati ukloniti ili zamijeniti osjetljive podatke.
```

Primjeri redakcije:

```txt
ime i prezime       -> [PERSON]
JMBG / ID broj      -> [ID_NUMBER]
telefon             -> [PHONE]
email               -> [EMAIL]
broj računa         -> [ACCOUNT_NUMBER]
adresa              -> [ADDRESS]
medicinski detalj   -> [MEDICAL_DETAIL]
```

Napomena:

```txt
Redaction nije savršena zaštita.
UI mora jasno reći da je ovo pomoćna mjera, ne garancija.
```

## local_only

```txt
Sadržaj dokumenta ne smije napustiti lokalnu mašinu.
```

Dozvoljeno:

```txt
- lokalno čuvanje fajla,
- lokalna metadata analiza,
- lokalni OCR ako postoji,
- lokalna pretraga,
- ručno korisničko pregledanje,
- lokalni model ako bude podržan.
```

Nije dozvoljeno:

```txt
- slanje raw sadržaja cloud modelu,
- slanje kompletnog dokumenta cloud API-ju,
- slanje osjetljivih chunkova van mašine.
```

## ask_each_time

```txt
Za svaki dokument ili operaciju korisnik mora potvrditi da li sadržaj smije ići cloud modelu.
```

Ovo je dobar default za nepoznate dokumente.

---

# Default privacy pravila

Za osjetljive kategorije default treba biti:

```txt
ask_each_time
```

ili strožije:

```txt
local_only
```

Posebno za:

```txt
- medicinske dokumente,
- poreske dokumente,
- bankovne izvode,
- lične dokumente,
- ugovore sa osjetljivim podacima,
- dokumente koji sadrže podatke trećih lica.
```

Za manje osjetljive dokumente može biti:

```txt
ask_each_time
```

Ne smije postojati globalno pravilo:

```txt
sve dokumente šalji cloud modelu bez jasne korisničke dozvole
```

---

# UI zahtjevi za privacy

Prije obrade foldera ili dokumenata, UI mora prikazati:

```txt
Ricky želi obraditi ove dokumente:

Scope:
- folder/fajlovi

Privacy mode:
- cloud_allowed / redacted_cloud / local_only / ask_each_time

Šta može napustiti računar:
- ništa
- samo redacted tekst
- odabrani chunkovi
- kompletan tekst dokumenta

[Otkaži] [Promijeni privacy] [Pokreni]
```

Za osjetljive dokumente prikazati jasnije upozorenje:

```txt
Ovaj dokument može sadržati osjetljive podatke.
Da li dozvoljavaš cloud obradu?
```

Opcije:

```txt
- Lokalno samo
- Rediguj pa obradi
- Dozvoli cloud obradu
- Otkaži
```

---

# Storage za privacy

Dodati kasnije u Document Engine storage:

```txt
context_packs:
- id
- name
- goal
- allowed_sources
- forbidden_actions
- privacy_mode
- created_at
- status

source_documents:
- id
- context_pack_id
- path
- file_type
- sensitivity_label
- cloud_processing_allowed
- redaction_status
- ingested_at

document_chunks:
- id
- document_id
- chunk_text_local_ref
- page
- section
- paragraph
- can_send_to_cloud
- redacted_text_ref
- created_at

privacy_decisions:
- id
- context_pack_id
- document_id
- decision
- user_confirmed
- confirmed_at
```

Ne implementirati sve odmah. Ovo je future design.

---

# Review Packet

Review Packet je glavni rezultat Document Engine-a.

Sadrži:

```txt
- kratak sažetak,
- ključne datume,
- ključne iznose,
- osobe/firme,
- dokumente koji su korišteni,
- citate i izvore,
- listu nedostajućih dokumenata,
- rizike/nejasnoće,
- pitanja za korisnika ili stručnjaka,
- predložene korake,
- nacrt dokumenta ako je potreban,
- Action Receipt.
```

Review Packet nije isto što i finalna predaja, finalni email, finalni potpis ili plaćanje.

---

# Action Receipt

Svaki ozbiljan Document Engine zadatak mora završiti sa Action Receipt.

Action Receipt mora sadržati:

```txt
- šta je Ricky uradio,
- koje izvore je koristio,
- koje fajlove je pročitao,
- koji privacy mode je korišten,
- da li je nešto poslato cloud modelu,
- šta je redigovano,
- šta je zaključio,
- šta nije siguran,
- koji dokazi nedostaju,
- šta korisnik mora provjeriti,
- koja akcija je blokirana ili čeka potvrdu.
```

Ovo je obavezno za povjerenje.

---

# Gate pravila

Gate je hard safety granica.

Allowed:

```txt
- pripremi,
- objasni,
- organizuj,
- normalizuj,
- napravi checklistu,
- napravi nacrt,
- citiraj izvore,
- napravi Review Packet,
- predloži sljedeće korake.
```

Blocked by default:

```txt
- pošalji,
- plati,
- potpiši,
- predaj obrazac,
- obriši bitne fajlove,
- pošalji dokument trećoj strani,
- izvrši nepovratnu akciju.
```

Za neke akcije treba hard-block dok korisnik ručno ne napravi radnju van Ricky-ja:

```txt
- digitalni potpis,
- plaćanje,
- poreska predaja,
- slanje medicinskih/osjetljivih dokumenata,
- masovno brisanje fajlova.
```

---

# Ingest / Export tehnički opseg

Ne obećavati sve formate odmah.

Implementirati inkrementalno.

## Ingest redoslijed

```txt
1. TXT / MD
2. PDF sa selectable tekstom
3. slike kao file reference
4. DOCX
5. CSV / Excel
6. OCR za skenirane dokumente
7. email attachments
```

## Export redoslijed

```txt
1. Markdown
2. CSV za tabele
3. JSON za strukturisane podatke
4. DOCX
5. PDF
6. ZIP packet sa izvorima i izvještajem
```

Napomena:

```txt
PDF/OCR/DOCX/Excel nisu "još par Python fajlova".
To su posebne biblioteke, testovi i edge case-ovi.
```

---

# Future Epic redoslijed bez numeracije

Ne koristiti FAZA brojeve ovdje.

Koristiti nazive i dependencies.

## Epic Step — Context Pack MVP

Depends on:

```txt
- Plans/Confirmations,
- Activity timeline,
- SQLite storage.
```

Scope:

```txt
- korisnik bira folder/fajlove,
- definiše cilj,
- definiše privacy_mode,
- definiše zabranjene akcije.
```

## Epic Step — Document Ingest MVP

Depends on:

```txt
- Context Pack MVP,
- storage za source_documents.
```

Scope:

```txt
- TXT/MD,
- PDF text extraction,
- osnovni metadata.
```

## Epic Step — Chunk + Normalize MVP

Depends on:

```txt
- Document Ingest MVP.
```

Scope:

```txt
- document_chunks,
- datumi,
- iznosi,
- osobe/firme,
- document_type,
- missing_items.
```

## Epic Step — Citation Map

Depends on:

```txt
- Chunk + Normalize MVP.
```

Scope:

```txt
- svaka tvrdnja u Review Packet-u ima source reference,
- link iz Output-a do source dijela.
```

## Epic Step — Review Packet Builder

Depends on:

```txt
- Citation Map,
- Plans/Confirmations.
```

Scope:

```txt
- summary,
- timeline,
- checklist,
- missing docs,
- questions,
- risks,
- draft section ako treba.
```

## Epic Step — Action Receipt + Gate

Depends on:

```txt
- Review Packet Builder,
- privacy decisions,
- confirmation system.
```

Scope:

```txt
- šta je urađeno,
- izvori,
- privacy mode,
- cloud/redaction status,
- šta čeka korisnika,
- šta je blokirano.
```

## Epic Step — Runbooks

Depends on:

```txt
- Review Packet Builder,
- Action Receipt + Gate.
```

Scope:

```txt
- "Sredi folder",
- "Pripremi dokumente za knjigovođu",
- "Pregled carinskog paketa",
- drugi reusable workflow-i.
```

---

# Instrukcija za Claude Code

Implementiraj ovaj dodatak kao izmjenu dokumentacije, ne kao novi backend feature.

## Uradi

```txt
1. U postojećem ARCHITECTURE dokumentu zadrži Document/Paperwork Engine ideju.
2. Ukloni ili zamijeni sve samostalne brojeve FAZA 11-17 iz Document Engine sekcije.
3. Zamijeni ih sa "Future Epic — Document / Paperwork Engine".
4. Dodaj dependency-based epic steps bez faznih brojeva.
5. Dodaj Document Privacy Model.
6. Dodaj privacy_mode vrijednosti:
   - cloud_allowed
   - redacted_cloud
   - local_only
   - ask_each_time
7. Dodaj default privacy pravila za osjetljive dokumente.
8. Dodaj Action Receipt proširenje koje uključuje privacy/cloud/redaction status.
9. Dodaj napomenu da ingest/export formati idu inkrementalno.
10. Dodaj jasno upozorenje da Document Engine nije MVP i ne smije blokirati core voice/control rad.
```

## Ne radi

```txt
- Ne implementirati Python kod za Document Engine.
- Ne praviti nove SQLite migracije sada.
- Ne dodavati nove endpoint-e sada.
- Ne renumerisati postojeći MIGRATION_PLAN.md bez posebne odluke.
- Ne uvoditi FAZA 11-17 iz ovog dodatka u arhitekturu.
- Ne mijenjati src/lib/realtime.ts.
- Ne uvoditi Python STT/TTS.
```

## Ako diraš MIGRATION_PLAN.md

Ako bude potrebno spomenuti Document Engine u `MIGRATION_PLAN.md`, dodaj ga samo kao backlog/future epic:

```txt
Backlog / Future Epic:
Document / Paperwork Engine

Status:
Not active MVP work.

Depends on:
- Python backend skeleton,
- Realtime session security,
- Voice-first UI,
- Activity timeline,
- Plans/Confirmations,
- safe local tools,
- Companion voice integration.

Final phase number:
TBD by integrator.
```

Ne dodjeljuj konačan broj faze osim ako korisnik izričito traži.

---

# Acceptance Criteria

Dokumentacija je ispravno ažurirana kada važi:

```txt
- Document Engine postoji kao Future Epic, ne kao aktivna numerisana faza.
- Nema konflikta sa postojećim MIGRATION_PLAN.md fazama.
- Privacy model za dokumente je eksplicitno definisan.
- Osjetljivi dokumenti ne idu implicitno u cloud obradu.
- Action Receipt uključuje privacy/cloud/redaction informacije.
- Gate pravila jasno blokiraju plaćanje, potpis, predaju i slanje osjetljivih dokumenata.
- Ingest/export opseg je označen kao inkrementalan.
- Nema implementacije backend koda u ovoj izmjeni.
- Core voice/control MVP ostaje prioritet.
```
