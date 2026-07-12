# Agent report — "Otkaži diktiranje" dugme sad ima vizuelnu afordansu

**Datum:** 2026-07-12
**Scope:** `src/styles/11-pixel-shell.css` (`.pixel-dictation-head button`).

**Povod:** Korisnik je poslao screenshot — "Otkaži diktiranje" tekst u zaglavlju Diktiranje ekrana ne izgleda kao dugme (nema ivicu, pozadinu ni hover), iako jeste pravi `<button onClick={onCancel}>` element (`DictationScreen.tsx:54-56`).

## Šta je urađeno

`.pixel-dictation-head button` je imalo `background: transparent`, bez border-a, bez padding-a, bez hover stanja — funkcionalno dugme, nula vizuelnog signala da je klikabilno. Dodano: suptilna ivica, pozadina, border-radius, `cursor: pointer`, i `:hover` stanje (jača ivica/pozadina/boja teksta), u skladu sa vizuelnim jezikom ostalih "ghost" dugmadi u aplikaciji (`.pixel-secondary` obrazac, lakša varijanta).

## Verifikacija

- `npm run build` — čisto.
- Korisnik je vizuelno potvrdio uživo (`npm run dev`) — hover se vidi.

## Šta nije dirano

`.pixel-card header button` (npr. "Prikaži sve" dugme u Activity kartici) ima isti "transparent, bez hover-a" obrazac — namjerno ostavljeno, korisnik nije prijavio problem tamo i to je niže-frekventna sekundarna akcija pored naslova, ne primarna akcija na dnu toka kao Cancel dictation.
