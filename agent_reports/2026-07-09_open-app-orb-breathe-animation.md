# Agent report - Open app orb breathe animation

**Datum:** 2026-07-09

## Scope

Popravka vizuelne razlike izmedju mini racunarskog moda i otvorene aplikacije:
mini avatar je imao jasno breathe/talk pulsiranje, dok veliki orb u otvorenoj
aplikaciji nije djelovao animirano na isti nacin.

## GitNexus impact

Prije izmjene je pokrenut `gitnexus_impact` za `RickyOrb`
(`src/components/RickyOrb.tsx`). Rezultat: `LOW` risk. Direktno zavisi
`IdleScreen`, indirektno `PixelMockupBoard` i `App`.

## Sta je uradjeno

- `src/styles/09-ricky-orb.css` sada animira veliki avatar istim breathe/talk
  ritmom kao mini computer avatar.
- Idle state koristi `ricky-avatar-breathe`.
- Listening i speaking state koriste brzi `ricky-avatar-talk`.
- Thinking state koristi malo brzi breathe tempo.
- Stari suptilni `ricky-soft-float` i raniji speaking image keyframe su
  zamijenjeni animacijama koje mijenjaju i `transform` i glow `filter`.

## Zasto je uradjeno

Da otvorena aplikacija vizuelno ima isti "zivi" orb osjecaj kao ukljuceni
racunarski mod, bez uvodjenja nove logike ili zasebnih asseta.

## Kako je uradjeno

Promjena je CSS-only i ogranicena na `src/styles/09-ricky-orb.css`. Vrijednosti
za scale i drop-shadow preuzete su iz postojeceg `src/styles/13-mini-avatar.css`
ritma, uz male state-specific razlike za veliki orb.

## Sta nije dirano

- Nije diran `RickyOrb.tsx`.
- Nije diran voice-state mapping.
- Nisu dirani Electron main/preload tokovi.
- Nisu dirane postojece nevezane izmjene u `docs/refactor_plan.md`,
  `electron/main.cjs`, `electron/core/legacyDb.cjs`, niti `_old_app_tmp.tsx`.

## Verifikacija

- `npm run build` - prolazi; Vite prijavljuje samo postojece upozorenje o
  velikim chunkovima.

## Rizici/ogranicenja

Animacija sada koristi `filter` unutar keyframe-a na velikoj slici, sto je
vizuelno uskladjeno sa mini modom, ali moze imati malo veci GPU trosak od
prethodnog staticnog prikaza.

## Potreban follow-up

Vizuelno provjeriti u otvorenoj aplikaciji da breathe/talk ritam odgovara
snimku iz mini racunarskog moda.

## Potrebna korisnicka potvrda

Potrebna je vizuelna potvrda korisnika da je intenzitet animacije sada dovoljno
blizu snimku.
