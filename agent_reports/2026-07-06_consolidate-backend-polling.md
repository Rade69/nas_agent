# Agent report — Konsolidacija backend polling-a u src/App.tsx

**Datum:** 2026-07-06

## Scope

- Izmjena: `src/App.tsx` (dva odvojena `setInterval` polling efekta spojena u jedan).

## GitNexus impact

`gitnexus_detect_changes({repo: "nas_agent", scope: "all"})` → risk **HIGH**, 8 pogođenih procesa, sve preko simbola `App` (root komponenta). Ovo je artefakt širine grafa — `App` funkcija okuplja mnogo nepovezanih pomoćnih funkcija (audio meter, event parsing, itd.) koje GitNexus prikazuje kao "pogođene" jer dijele isti roditeljski simbol, ne zato što su stvarno mijenjane. Potvrđeno da nijedna od njih nije dirana — samo dva `useEffect` bloka su spojena u jedan.

## Šta je urađeno

Korisnik je ranije primijetio (preko log-a iz `npm run dev`) da se `/confirmations/pending` i `/events` pozivaju vrlo učestalo, i tražio istragu. Nađeno: dva nezavisna `useEffect`/`setInterval` para u `src/App.tsx` — confirmations poll na 2500ms (FAZA 9), events poll na 3000ms (FAZA 11) — rade paralelno otkad su faze uvedene, svaki sa svojim ciklusom. Zaključak istrage: nije bug (obje su unutar preporučene granice iz `SECURITY_HARDENING_PLAN.md` sekcije 25.4), samo dva odvojena tajmera čija se gustina akumulira u dugom terminal logu. Korisnik je zatražio konsolidaciju "bolje sada nego kasnije".

Spojeno u jedan `useEffect`:
- Jedan `cancelled` flag i jedan `cursor` (za events cursor) dijele se između `refreshPending()` i `pollEvents()`.
- Nova `pollBoth()` funkcija zove oboje preko `Promise.allSettled([...])` — ako jedno padne, drugo se ipak izvrši (isto ponašanje kao prije, gdje je svaka funkcija imala svoj try/catch).
- Jedan `setInterval(pollBoth, 3000)` umjesto dva odvojena (2500ms + 3000ms).
- Stari, sad-suvišan FAZA 11 `useEffect` blok obrisan.

## Zašto je urađeno

Manje HTTP poziva (2 tajmera → 1), jedan effect lifecycle umjesto dva, bez gubitka funkcionalnosti — čist cleanup na korisnikov zahtjev.

## Kako je urađeno

Pročitan cijeli relevantni dio `App.tsx` (oba efekta + njihove zavisnosti) prije izmjene. Dva `Edit` poziva: prvi zamjenjuje FAZA 9 blok sa spojenom verzijom (sadrži i confirmations i events logiku), drugi briše sad-duplirani stari FAZA 11 blok. `npm run typecheck` i `npm run build` pokrenuti nakon izmjene.

## Šta nije dirano

- Logika unutar `refreshPending()` i `pollEvents()` — identična, samo premještena/spojena, bez promjene ponašanja.
- Python backend strana (`/confirmations/pending`, `/events` rute) — nedirane, ovo je čisto frontend polling cleanup.
- Interval za confirmations je sad 3000ms umjesto 2500ms (poravnat sa events intervalom) — 500ms razlika je neprimjetna za "pending confirmation" UI tok.

## Verifikacija

1. `npm run typecheck` — prošao bez grešaka.
2. `npm run build` — prošao (postojeća upozorenja o veličini chunk-ova su nepovezana, iz Mermaid dijagram biblioteke, ne od ove izmjene).
3. `gitnexus_detect_changes` — risk HIGH, objašnjeno iznad kao artefakt širine grafa preko root `App` simbola.

## Rizici / ograničenja

- Nije urađena vizuelna/runtime provjera u pravoj Electron sesiji (agent nema GUI pristup) — typecheck/build potvrđuju ispravnost koda, ne ponašanje u pregledaču. Preporučen ručni test: pokrenuti `npm run dev`, potvrditi da se pending confirmation dialog i dalje pojavljuje, i da se artifact/activity event-i i dalje ažuriraju iz `/events`.
- Kombinovani HTTP volumen je smanjen samo blago (~44/min → ~40/min) jer su oba tajmera već bila slična po frekvenciji — stvarna korist je pojednostavljen kod (jedan effect/interval umjesto dva), ne dramatično manje mrežnog saobraćaja.

## Potreban follow-up

Nema neposrednog. Ako se u budućnosti pokaže da je čak i 3s prečest interval (npr. za produkcijski self-test iz Security Gate 2), razmotriti sporiji interval ili prelazak sa polling-a na WebSocket push (već pomenuto kao budući follow-up u FAZA 11 izvještaju).

## Potrebna korisnička potvrda

Preporučeno: ručno pokrenuti `npm run dev` i potvrditi da confirmation dialog i activity/artifact ažuriranja i dalje rade kao prije.
