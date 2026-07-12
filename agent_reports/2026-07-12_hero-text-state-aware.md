# Agent report — Idle hero tekst je sad state-aware (nije više statičan)

**Datum:** 2026-07-12
**Scope:** `src/components/pixel/IdleScreen.tsx`, `src/i18n/locales/*.json` (5 fajlova).

**Povod:** FABLE-5 GUI pregled (2026-07-12), tačka #1 — "dupli status".
Provjerom u kodu (`IdleScreen.tsx:51-52` prije izmjene) nađeno preciznije od
FABLE-5-ove pretpostavke: nije rizik desinhronizacije dva live indikatora —
veliki centralni naslov ("Ricky je spreman") je bio **potpuno statičan**,
nikad se nije mijenjao sa `voiceState`, dok je header (`voiceStateLabel()`)
već ispravno prikazivao "Slušam"/"Razmišljam"/"Govorim" itd. Znači: dok god
`voiceState` nije "idle", centralni naslov je aktivno pogrešan/kontradiktoran
sa headerom, ne samo teoretski rizik.

## Šta je urađeno

- `IdleScreen.tsx` sad računa `heroTitle`/`heroHint` na osnovu `voiceState`
  umjesto uvijek `t("idle.ready")`/`t("idle.hint")`.
- Novi `idle.state.*` i18n namespace — 8 stanja (listening/transcribing/
  thinking/speaking/waiting_confirmation/interrupted/muted/error), svako sa
  `title`+`hint`. `idle` stanje samo i dalje koristi postojeće
  `idle.ready`/`idle.hint` (netaknuto).
- **Namjerno drugačija formulacija od header-a**, ne kopija istih riječi —
  header ostaje kratka mašinska labela ("Slušam"), hero tekst je ljudskiji i
  u drugom licu ("Slušam te...", "Reci šta ti treba") — tačno FABLE-5-ov
  predlog "header mašinski, orb ljudski, različit sadržaj".
- Prazan `hint` (transcribing/speaking stanja, gdje je kratki `title` sam
  dovoljan) se ne renderuje kao prazan `<p>` — uslovno renderovanje.

## Zašto ovako

- Header i hero tekst NIKAD nisu mogli desinhronizovati se u smislu "dva
  izvora istine koja se moraju ručno sinhronizovati" — oba čitaju isti
  `voiceState` prop, samo je hero tekst dotad ignorisao taj prop za tekst
  (koristio ga je samo za `RickyOrb`-ovu vizuelnu animaciju). Sad oba
  ispravno reaguju na isto stanje, prirodno bez rizika od ručnog raskoraka.
- Izbjegnute gramatički rodno-zavisne fraze u sr-Latn (npr. "spreman/na")
  radi jednostavnosti — sve fraze su rodno neutralne.

## Šta NIJE dirano

- Header (`TopBar.tsx` `voiceStateLabel()`) — ostaje nepromijenjen, i dalje
  kratka mašinska labela.
- `RickyOrb.tsx` — i dalje čisto vizuelan (boja/animacija po stanju), bez
  teksta, nepromijenjen.

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto.
- Runtime NIJE testiran — Electron desktop app, nema browser-automation
  alata u ovom okruženju. Potreban korisnički test: pokrenuti glasovnu
  sesiju i posmatrati da centralni naslov ispravno prati stanja (Slušam
  te.../Razmišljam.../itd.), ne ostaje na "Ricky je spreman".

## Potreban follow-up

Runtime test korisnika. de/es/fr formulacije su best-effort, isti
disclaimer kao svugdje drugo u projektu.

## Potrebna korisnička potvrda

Runtime test prije nego se smatra potpuno gotovim.
