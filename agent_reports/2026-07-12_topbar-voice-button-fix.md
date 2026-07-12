# Agent report — TopBar "Glas" dugme (mrtvo dugme popravljeno)

**Datum:** 2026-07-12
**Scope:** `src/components/pixel/TopBar.tsx`, `src/components/pixel/PixelMockupBoard.tsx`.

**Povod:** FABLE-5 GUI pregled (2026-07-12), tačka #6 — "provjeri da mic ikonica i
Diktiranje dugme nemaju preklapajuću funkciju". Provjerom u kodu nađeno gore od
pretpostavke: mic ikonica (`title="Glas"`) je imala **nula** funkcije, ne
preklapajuću — `<button>` bez `onClick`, čist mockup ostatak.

## Šta je urađeno

- `TopBar.tsx` dobio nove opcione propove: `isActive`, `isConnected`,
  `onVoiceToggle`, `onStop`.
- Dugme sad radi tačno isto kao centralno mic dugme u `IdleScreen.tsx` —
  isti `isActive ? onStop : onVoiceToggle` toggle, ista ikonica-po-stanju
  logika (Stop/MicOff/Mic), isti i18n key-evi (`idle.stop`/`idle.disconnect`/
  `idle.startVoice` — reuse, nema novih prevoda).
- Namjerno uslovno renderovano (`onVoiceToggle && onStop ? ... : null`),
  isti obrazac kao `onEnterDictation`/`onStopAll` — ako neki budući pozivalac
  ne proslijedi handlere, dugme se jednostavno ne prikazuje, umjesto da opet
  postoji vidljivo-ali-mrtvo.
- `PixelMockupBoard.tsx` prosljeđuje `isActive`/`isConnected`/`onVoiceToggle`/
  `onStop` (već postojeći propovi na `PixelMockupBoard` nivou, korišteni za
  `IdleScreen`) do `TopBar`-a u idle grani.

## Zašto ovako

Postojala je već kompletna toggle logika za glasovnu sesiju (centralno mic
dugme u `IdleScreen.tsx`) — ne treba nova, samo je trebalo TopBar dugme
povezati na iste handlere umjesto da izmišlja paralelnu logiku.

## Šta NIJE dirano

- Dictation-mode `TopBar` poziv (`PixelMockupBoard.tsx` linija ~121) — ne
  prima `onStopAll`, pa se `.pixel-top-actions` (uklj. i ovo dugme) uopšte
  ne renderuje u dictation ekranu. Nema potrebe za izmjenom tamo.
- "Diktiranje" dugme pored njega — ostaje odvojena funkcija (ulazak u
  Dictation Mode), sad jasno različito od glasovnog toggle-a jer oba imaju
  smislene, različite title-ove.

## Verifikacija

- `npm run typecheck` — čisto.
- `npm run build` — čisto.
- Runtime NIJE testiran — Electron desktop app, nema browser-automation
  alata u ovom okruženju. Potreban korisnički test: klik na mic ikonicu u
  top baru treba da pokrene/prekine glasovnu sesiju isto kao centralno mic
  dugme.

## Potreban follow-up

Nema — ovo je bio izolovan, samostalan bug.

## Potrebna korisnička potvrda

Runtime test prije nego se smatra potpuno gotovim.
