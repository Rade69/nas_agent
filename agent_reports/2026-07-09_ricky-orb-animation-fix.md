# Agent report - Ricky orb animation fix

**Datum:** 2026-07-09

## Scope

Popravka regresije nakon prelaska velikog Ricky orb-a na zajednicki
`Riki-avatar.png` asset: orb je izgledao staticno i opticki nije bio dobro
centriran u krugu.

## GitNexus impact

Prije izmjene je pokrenut `gitnexus_impact` za `RickyOrb`
(`src/components/RickyOrb.tsx`). Rezultat: `LOW` risk. Direktno zavisi
`IdleScreen`, indirektno `PixelMockupBoard` i `App`.

Prije commita je pokrenut `gitnexus_detect_changes(scope="all",
repo="nas_agent")`. Rezultat: `risk_level: low`, 2 promijenjena indeksirana
fajla, bez promijenjenih simbola i bez pogodjenih execution flow-ova.

## Sta je uradjeno

- Vraceni su animirani `.ricky-orb__ring` elementi kao overlay preko zajednickog
  avatar asseta.
- Avatar crop je opticki spusten preko `object-position: center 53%`.
- Pixel hero outer ring je pomjeren unutar kruznog cropa (`inset: 5%`) da ne
  bude odsijecan.

## Zasto je uradjeno

Da veliki orb ponovo djeluje ziv/animiran kao u racunarskom modu, bez vracanja
state-specific PNG asseta, i da vizuelni centar avatara bolje sjedne u krug.

## Kako je uradjeno

Promjena je CSS-only i ogranicena na orb/pixel shell stilove:

- `src/styles/09-ricky-orb.css`
- `src/styles/11-pixel-shell.css`

Nije dodavana nova poslovna logika, agent runtime logika, storage logika, AI
logika niti izmjene u `electron/main.cjs`.

## Sta nije dirano

- Nije diran `RickyOrb.tsx` ni voice-state mapping.
- Nisu dirani Electron main/preload tokovi.
- Nisu dirani legacy PowerShell computer-use toolovi.
- Nije diran nevezani untracked fajl `_old_app_tmp.tsx`.

## Verifikacija

- `npm run build` - prolazi; Vite prijavljuje samo postojece upozorenje o
  velikim chunkovima.
- `git diff --check` - bez whitespace gresaka; samo LF -> CRLF upozorenja.
- `gitnexus_detect_changes` - low risk, bez pogodjenih flow-ova.

## Rizici/ogranicenja

Ring overlay sada koristi `mix-blend-mode: screen`, pa vizuelni intenzitet moze
malo varirati zavisno od pozadine i GPU renderinga. Promjena je namjerno
ogranicena na postojeci orb prikaz.

## Potreban follow-up

Vizuelno provjeriti idle/listening/speaking state-ove u aplikaciji i po potrebi
fino podesiti `object-position` izmedju `52%` i `54%`.

## Potrebna korisnicka potvrda

Nije potrebna za commit; korisnik je eksplicitno zatrazio commit mojih promjena.
