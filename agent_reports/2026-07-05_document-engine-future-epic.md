# Agent report — Document/Paperwork Engine kao Future Epic (bez brojeva faza)

**Datum:** 2026-07-05

## Scope

- Novi: `docs/DOCUMENT_ENGINE_FUTURE_EPIC.md`.
- Izmjena: `docs/MIGRATION_PLAN.md` (nova sekcija "Backlog / Future Epics").
- Izmjena: `docs/ARCHITECTURE_VOICE_FIRST_REVISED_WITH_DOCUMENT_ENGINE.md` (dodana napomena "zamijenjeno", uputa na dva kanonska fajla).

## GitNexus impact

Nije relevantno — samo dokumentacioni fajlovi, bez izmjene koda.

## Šta je urađeno

Korisnik je dostavio `DOCUMENT_ENGINE_ADDENDUM_FOR_CLAUDE.md` — dodatak pisan direktno kao instrukcija meni, koji rješava oba problema koja sam ranije flagovao u analizi Document Engine dokumenta: (1) sudar brojeva faza (FAZA 11-17 se sudaralo sa već postojećim FAZA 11-19 u `MIGRATION_PLAN.md`), (2) nedostatak privacy modela za osjetljive dokumente (medicinski, poreski, carinski). Dodatak je eksplicitno tražio da se numeracija ukloni i zamijeni "Future Epic" konceptom (naziv + zavisnosti + koraci, bez brojeva), i da se doda `privacy_mode` model.

Implementirano tačno po uputama dodatka:

1. **Nov fajl `docs/DOCUMENT_ENGINE_FUTURE_EPIC.md`** — sadrži cijeli Document Engine sadržaj (generic skeleton, Review Packet, Action Receipt, Gate pravila, ingest/export inkrementalni opseg) plus **Privacy Model** sekciju (`privacy_mode`: `cloud_allowed`/`redacted_cloud`/`local_only`/`ask_each_time`, default pravila za osjetljive kategorije, UI zahtjevi, storage polja za `context_packs`/`source_documents`/`document_chunks`/`privacy_decisions`) i **Epic koraci** sekciju (Context Pack MVP → Document Ingest MVP → Chunk+Normalize MVP → Citation Map → Review Packet Builder → Action Receipt+Gate → Runbooks) — svaki sa "Depends on" umjesto broja faze.
2. **`docs/MIGRATION_PLAN.md`** dobija novu sekciju "Backlog / Future Epics" — tabela sa jednim redom (Document/Paperwork Engine, status "Not active MVP work", zavisnosti FAZA 4-12, link na novi fajl). Eksplicitno piše da samo ovaj fajl smije dodjeljivati brojeve faza.
3. **Stari `ARCHITECTURE_VOICE_FIRST_REVISED_WITH_DOCUMENT_ENGINE.md`** — dobio napomenu "zamijenjeno" koja objašnjava da je voice-first dio identičan `ARCHITECTURE_VOICE_FIRST_REVISED.md`, a Document Engine dio je premješten (i ispravljen) u novi fajl. Sadržaj fajla nije brisan (istorijski zapis), samo dodata napomena na vrhu.

## Zašto je urađeno

Ovo je treći put da se numeracija faza sudarila (prvo VF-1..VF-6, pa "FAZA 11-17" za document engine) — korisnikov dodatak eksplicitno uvodi pravilo da ubuduće samo `MIGRATION_PLAN.md` dodjeljuje brojeve, a arhitektonski/epic dokumenti opisuju samo zavisnosti i redoslijed koraka. Ovo pravilo je sada zapisano u `MIGRATION_PLAN.md` samom (sekcija "Backlog / Future Epics") tako da važi i za buduće epice, ne samo za ovaj.

## Kako je urađeno

`Write` za novi `DOCUMENT_ENGINE_FUTURE_EPIC.md` (sadržaj preuzet i reorganizovan iz korisnikovog dodatka — generic skeleton, privacy model, epic steps bez brojeva). `Edit` na `MIGRATION_PLAN.md` (dodata Backlog/Future Epics sekcija odmah nakon Status faza tabele). `Edit` na starom kombinovanom fajlu (banner na vrhu, sadržaj ispod netaknut).

## Šta nije dirano

- Nema backend koda — nijedan Python fajl, nijedna SQLite migracija, nijedan endpoint (eksplicitno zabranjeno u dodatku, "Ne radi" sekcija).
- `src/lib/realtime.ts` — netaknut.
- `docs/MIGRATION_PLAN.md` FAZA 0-19 numeracija — nepromijenjena, Document Engine NIJE dobio broj faze (kako je dodatak eksplicitno tražio).
- `docs/ARCHITECTURE_VOICE_FIRST_REVISED.md` — netaknut (kanonski voice-first dokument ostaje kakav je bio).

## Verifikacija

Ručna provjera da `docs/MIGRATION_PLAN.md` FAZA tabela (0-19) nema nijedan novi red za Document Engine — samo referenca u zasebnoj "Backlog / Future Epics" sekciji bez broja. Provjereno da su svi linkovi između tri fajla (MIGRATION_PLAN.md ↔ DOCUMENT_ENGINE_FUTURE_EPIC.md ↔ stari WITH_DOCUMENT_ENGINE.md) konzistentni.

## Rizici / ograničenja

- Ovo je i dalje samo dokumentacija/planiranje — kad se epic stvarno aktivira, treba svjesno odlučiti broj faze (nakon FAZE 19, po trenutnom stanju) i tek tada dodati u glavnu Status faza tabelu.
- Privacy model (`privacy_mode`) je dizajn, ne implementacija — kad Document Engine stvarno počne, treba provjeriti da li se `SECURITY_MODEL.md` risk-level sistem i ovaj privacy_mode model preklapaju ili trebaju biti eksplicitno povezani (trenutno su opisani kao odvojeni, komplementarni slojevi).

## Potreban follow-up

Nema neposrednog — ovo je backlog, ne aktivan rad. Sljedeći aktivan korak po planu je i dalje FAZA 4 (Python backend skeleton).

## Potrebna korisnička potvrda

Nema ničeg za ručnu provjeru na uređaju — dokumentacioni zadatak.
