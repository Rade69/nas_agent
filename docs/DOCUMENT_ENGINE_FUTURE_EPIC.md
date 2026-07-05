# Future Epic — Document / Paperwork Engine

## Status

**Nije aktivna MVP faza.** Ovo je backlog/future epic — opisan sa zavisnostima i redoslijedom koraka, ali **bez brojeva faza**. Konačan broj faze dodjeljuje isključivo `docs/MIGRATION_PLAN.md`, i to tek kad korisnik eksplicitno odluči da ovaj epic ulazi u aktivan rad.

Razlog za ovo pravilo: svaki prethodni arhitektonski dokument koji je sam sebi dodjeljivao "FAZA 11-17" sudarao se sa već postojećom numeracijom u `MIGRATION_PLAN.md`. Od sada, arhitektonski/epic dokumenti smiju definisati samo naziv, zavisnosti i redoslijed koraka unutar epica — ne brojeve faza.

## Trenutni MVP prioritet (ne ovaj dokument)

```text
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

Vidi [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) FAZA 4-12 za trenutni aktivan rad.

## Namjena

Document/Paperwork Engine služi da Ricky od neurednih fajlova, dokumenata, PDF-ova, screenshotova, email attachmenta i bilješki napravi:

```text
Review Packet
+ Action Receipt
+ Citation Map
+ Missing Items Checklist
+ Human Approval Gate
```

Glavni princip: **agent ne klikće finalno dugme** — agent priprema pregledan, citiran i provjerljiv paket za čovjeka.

Ricky ne smije samostalno: poslati email, predati obrazac, potpisati dokument, platiti, poslati osjetljive dokumente trećoj strani, napraviti nepovratnu akciju.

## Generički skeleton

Isti skeleton kroz različite domene (računi, ugovori, porezi, osiguranje, medicinska dokumentacija, carinska dokumentacija, poslovna evidencija, obrazovni formulari, administrativni zahtjevi):

```text
Context Pack → Ingest → Chunk → Normalize → Store → Retrieve → Cite → Export → Gate
```

## Zavisnosti (dependency pravila)

Document/Paperwork Engine **ne ulazi u aktivan rad** dok nisu stabilni:

```text
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

Konkretno, prije implementacije moraju postojati: (1) backend koji može čuvati activity, (2) `confirmation_id` mehanizam, (3) plan/proposal storage, (4) permission/risk layer, (5) jasan UI za Output/Activity/Plans.

---

## Privacy Model za dokumente (obavezan dio ovog epica)

Dokumenti mogu sadržavati: medicinske podatke, poreske podatke, bankovne podatke, lične identifikacione podatke, ugovore, carinske dokumente, poslovne tajne, podatke trećih lica.

### Context Pack mora imati `privacy_mode`

```text
cloud_allowed     — dokument/sadržaj smije ići cloud modelu, korisnik eksplicitno dozvolio
redacted_cloud    — prije slanja cloud modelu pokušati ukloniti/zamijeniti osjetljive podatke
local_only        — sadržaj ne smije napustiti lokalnu mašinu
ask_each_time     — korisnik potvrđuje po dokumentu/operaciji (dobar default za nepoznate dokumente)
```

Primjeri redakcije za `redacted_cloud`:

```text
ime i prezime       -> [PERSON]
JMBG / ID broj      -> [ID_NUMBER]
telefon             -> [PHONE]
email               -> [EMAIL]
broj računa         -> [ACCOUNT_NUMBER]
adresa              -> [ADDRESS]
medicinski detalj   -> [MEDICAL_DETAIL]
```

Napomena: redakcija nije savršena zaštita — UI mora jasno reći da je ovo pomoćna mjera, ne garancija.

`local_only` dozvoljava: lokalno čuvanje fajla, lokalnu metadata analizu, lokalni OCR ako postoji, lokalnu pretragu, ručno korisničko pregledanje, lokalni model ako bude podržan. **Ne dozvoljava**: slanje raw sadržaja ili kompletnog dokumenta cloud API-ju, slanje osjetljivih chunkova van mašine.

### Default privacy pravila

Za osjetljive kategorije (medicinski dokumenti, poreski dokumenti, bankovni izvodi, lični dokumenti, ugovori sa osjetljivim podacima, dokumenti sa podacima trećih lica) — default mora biti `ask_each_time` ili strože `local_only`. Za manje osjetljive dokumente `ask_each_time` je prihvatljiv default. **Ne smije postojati globalno pravilo "sve dokumente šalji cloud modelu bez jasne korisničke dozvole."**

### UI zahtjevi za privacy

Prije obrade foldera/dokumenata, UI mora prikazati scope, privacy mode, i šta konkretno napušta računar (ništa / samo redigovan tekst / odabrani chunkovi / kompletan tekst), sa opcijama Otkaži / Promijeni privacy / Pokreni. Za osjetljive dokumente — eksplicitno upozorenje i izbor: Lokalno samo / Rediguj pa obradi / Dozvoli cloud obradu / Otkaži.

### Storage za privacy (future design, ne implementirati sada)

```text
context_packs:      id, name, goal, allowed_sources, forbidden_actions, privacy_mode, created_at, status
source_documents:   id, context_pack_id, path, file_type, sensitivity_label, cloud_processing_allowed, redaction_status, ingested_at
document_chunks:    id, document_id, chunk_text_local_ref, page, section, paragraph, can_send_to_cloud, redacted_text_ref, created_at
privacy_decisions:  id, context_pack_id, document_id, decision, user_confirmed, confirmed_at
```

---

## Review Packet

Glavni rezultat epica. Sadrži: kratak sažetak, ključne datume, ključne iznose, osobe/firme, dokumente koji su korišteni, citate i izvore, listu nedostajućih dokumenata, rizike/nejasnoće, pitanja za korisnika ili stručnjaka, predložene korake, nacrt dokumenta ako je potreban, Action Receipt.

Review Packet **nije** isto što i finalna predaja, finalni email, finalni potpis ili plaćanje.

## Action Receipt

Svaki ozbiljan zadatak mora završiti sa Action Receipt-om koji sadrži: šta je Ricky uradio, koje izvore je koristio, koje fajlove je pročitao, **koji privacy mode je korišten, da li je nešto poslato cloud modelu, šta je redigovano**, šta je zaključio, šta nije siguran, koji dokazi nedostaju, šta korisnik mora provjeriti, koja akcija je blokirana ili čeka potvrdu.

## Gate pravila

Dozvoljeno: pripremi, objasni, organizuj, normalizuj, napravi checklistu, napravi nacrt, citiraj izvore, napravi Review Packet, predloži sljedeće korake.

Blokirano po defaultu: pošalji, plati, potpiši, predaj obrazac, obriši bitne fajlove, pošalji dokument trećoj strani, izvrši nepovratnu akciju.

Hard-block (dok korisnik ručno ne uradi van Ricky-ja): digitalni potpis, plaćanje, poreska predaja, slanje medicinskih/osjetljivih dokumenata, masovno brisanje fajlova.

## Ingest / Export — inkrementalan tehnički opseg

Ne obećavati sve formate odmah:

```text
Ingest redoslijed:  TXT/MD → PDF (selectable tekst) → slike (file reference) → DOCX → CSV/Excel → OCR (skenirani) → email attachments
Export redoslijed:  Markdown → CSV (tabele) → JSON → DOCX → PDF → ZIP packet (izvori + izvještaj)
```

PDF/OCR/DOCX/Excel nisu "još par Python fajlova" — posebne biblioteke, testovi i edge case-ovi.

---

## Epic koraci (bez brojeva faza — zavisnost određuje redoslijed)

### Epic Step — Context Pack MVP

Depends on: Plans/Confirmations, Activity timeline, SQLite storage.
Scope: korisnik bira folder/fajlove, definiše cilj, definiše `privacy_mode`, definiše zabranjene akcije.

### Epic Step — Document Ingest MVP

Depends on: Context Pack MVP, storage za `source_documents`.
Scope: TXT/MD, PDF text extraction, osnovni metadata.

### Epic Step — Chunk + Normalize MVP

Depends on: Document Ingest MVP.
Scope: `document_chunks`, datumi, iznosi, osobe/firme, `document_type`, `missing_items`.

### Epic Step — Citation Map

Depends on: Chunk + Normalize MVP.
Scope: svaka tvrdnja u Review Packet-u ima source reference; link iz Output-a do source dijela.

### Epic Step — Review Packet Builder

Depends on: Citation Map, Plans/Confirmations.
Scope: summary, timeline, checklist, missing docs, questions, risks, draft section ako treba.

### Epic Step — Action Receipt + Gate

Depends on: Review Packet Builder, privacy decisions, confirmation system.
Scope: šta je urađeno, izvori, privacy mode, cloud/redaction status, šta čeka korisnika, šta je blokirano.

### Epic Step — Runbooks

Depends on: Review Packet Builder, Action Receipt + Gate.
Scope: "Sredi folder", "Pripremi dokumente za knjigovođu", "Pregled carinskog paketa", drugi reusable workflow-i.

---

## Vidi i

- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) — sekcija "Backlog / Future Epics" referencira ovaj fajl, bez dodijeljenog broja faze.
- [ARCHITECTURE_VOICE_FIRST_REVISED.md](./ARCHITECTURE_VOICE_FIRST_REVISED.md) — voice-first arhitektura koju ovaj epic ne smije remetiti.
- [SECURITY_MODEL.md](./SECURITY_MODEL.md) — opšti risk/permission model; privacy_mode iznad je specifičan dodatak za sadržaj dokumenata, ne zamjena.
