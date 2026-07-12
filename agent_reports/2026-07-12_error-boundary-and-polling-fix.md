# Agent report — React Error Boundary + polling redundancy fix

**Datum:** 2026-07-12
**Scope:** `src/components/ErrorBoundary.tsx` (novo), `src/main.tsx`, `src/App.tsx`.

**GitNexus impact:** MEDIUM — `App`, `pollEvents`, `pollHealth` (uklonjen),
`replayingHistory` dotaknuti. Sve tačno namjeravane izmjene, nema iznenađenja.

## Šta je urađeno i zašto

Dva "brza dobitka" iz `agent_reports/2026-07-12_app-review-findings.md`
(nalazi #2 i #6), oba nezavisno potvrđena u kodu prije implementacije, ne
uzeta na pi-jevu riječ:

1. **React Error Boundary** (`src/components/ErrorBoundary.tsx`) — potvrđeno
   da ne postoji nijedan `componentDidCatch`/`getDerivedStateFromError` u
   projektu prije ovoga (`grep` bez rezultata), znači svaka greška u render-u
   bilo koje komponente je ranije rušila cijelu aplikaciju u prazan ekran.
   Class komponenta (React error boundary nema hook ekvivalent), namjerno
   samostalna (inline stilovi, bez i18n/CSS fajl zavisnosti) — ako je nešto
   gore u stablu puklo dovoljno loše da stigne dovde, sam fallback ne smije
   moći pući na isti način. Prikazuje poruku o grešci + dugme "Ponovo pokreni"
   (`window.location.reload()`). Wire-ovan u `src/main.tsx` oko cijelog
   render stabla (i `<App />` i `<CompanionOrb />`).

2. **Polling redundancy** (`src/App.tsx` `pollAll` useEffect, oko linije
   213-289) — potvrđeno u kodu: `pollHealth()` je pravio identičan
   `listEvents()` poziv kao `pollEvents()`, samo bez cursor parametra, isključivo
   da provjeri konekciju — treći HTTP zahtjev po ciklusu od 3s koji ništa
   novo ne radi. `pollEvents()` sad sam postavlja `backendConnected(true)`
   na uspjeh / `false` na grešku (koristeći svoj već postojeći poziv),
   `pollHealth()` uklonjen u potpunosti. 3 zahtjeva/3s → 2 zahtjeva/3s.

## Zašto ovako

- Error boundary fallback je namjerno "glup" (inline CSS, srpski hardkodiran
  tekst, ne koristi i18n) — ovo je posljednja linija odbrane, ne smije
  zavisiti od bilo čega što bi moglo biti uzrok originalne greške.
- `pollEvents()` je logično mjesto za health signal jer već radi tačno onaj
  HTTP poziv koji bi `pollHealth()` inače duplirao — nema potrebe za drugim
  identičnim pozivom.

## Šta NIJE dirano

- Ostatak `app-review-findings.md` liste (#1, #3-5, #7-18) — van obima ovog
  koraka, planirano zasebno.
- `pollEvents()`-ova logika obrade eventa (`artifact.created`,
  `tool.completed` itd.) — nepromijenjena, samo dodato postavljanje
  `backendConnected`.

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto.
- `cd python_backend && python -m pytest -q` — nerelevantno za ovu izmjenu
  (frontend-only), nije ponovo pokretano nakon prošlog commit-a u istoj sesiji.
- Runtime NIJE testiran — Electron desktop app, nema browser-automation alata
  u ovom okruženju. Potreban korisnički test: (1) namjerno izazvati grešku u
  render-u (npr. privremeno baciti exception u nekoj komponenti) da se
  potvrdi da se fallback ekran prikazuje umjesto bijelog ekrana; (2) provjeri
  da Backend status u sidebar-u i dalje ispravno prikazuje "OK"/"offline".

## Potreban follow-up

Ostatak `app-review-findings.md` liste, po dogovorenom prioritetu.

## Potrebna korisnička potvrda

Runtime test prije/poslije commita — vidi "Verifikacija" iznad.
