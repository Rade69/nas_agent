# Agent report — companion orb auto-show/hide na minimize/restore glavnog prozora

**Datum:** 2026-07-13
**Scope:** `electron/main.cjs`, `docs/ORB_PRESENCE_SPEC.md`.

**Povod:** Korisnik je prijavio: desni klik radi na oba orba (potvrda da je
prethodni context-menu lokalizacioni fix ispravan), ali kad minimizira
aplikaciju, oba orba nestanu — očekivao je da mali orb ostane na ekranu.

## Istraga

- `handleAppMinimize()` (`electron/ipc_handlers/app.cjs`) je samo pozivao
  `win.minimize()` — ništa nije diralo orb prozore.
- Grep kroz cijeli `electron/` nije našao nijedan `minimize`/`blur`/`hide`
  listener koji bi eksplicitno sklanjao orbove.
- `docs/ORB_PRESENCE_SPEC.md` (pisan 2026-07-09) je unaprijed dokumentovao
  tačno ovo kao poznatu, nikad implementiranu prazninu: "Mali orb se
  auto-pojavi kad minimiziraš prozor" — status ⬜ (samo ručni toggle).
- Companion orb VEĆ ima auto-show/hide, ali samo vezan za `set_mode`
  (Computer Mode uključi/isključi), ne za minimize/restore glavnog prozora
  (`electron/main.cjs:344-354`, postojeći kod) — objašnjava zašto je orb
  ponekad radio (kad korisnik uđe u Computer Mode) a ponekad ne (kad samo
  minimizira prozor u Display modu).

## Šta je urađeno

`electron/main.cjs`, odmah nakon `createWindow()` u `app.whenReady()`
callback-u: `mainWindow.on("minimize", () => showCompanion())` i
`mainWindow.on("restore", () => hideCompanion())`. Simetrično sa postojećim
Computer Mode obrascem, samo vezano za nativni minimize/restore umjesto
`set_mode`.

Korisnik je eksplicitno potvrdio (AskUserQuestion) obje odluke iz spec
dokumenta:
1. Implementirati auto-show na minimize — da.
2. Ponašanje na restore — orb automatski nestaje (simetrično), ne ostaje dok
   ga korisnik ručno ne zatvori.

`docs/ORB_PRESENCE_SPEC.md` gap tabela ažurirana — oba reda označena ✅
umjesto ⬜.

## Zašto ovako

- Listener je vezan direktno na `BrowserWindow` instancu (`.on("minimize"/"restore")`)
  umjesto na `handleAppMinimize()` IPC handler, jer se `minimize`/`restore`
  Electron eventi okidaju bez obzira da li je minimize pokrenut kroz app-ov
  custom title bar (IPC) ili native Windows mehanizam (taskbar, tipkovnički
  prečac) — hvatanje na nivou window eventa je robusnije od hvatanja samo na
  IPC pozivu.
- `hide()`/`show()` (Computer Mode tranzicije) i `minimize()`/`restore()`
  (native window state) su odvojeni Electron event parovi — provjereno da se
  ne preklapaju/duplo-okidaju (ulazak u Computer Mode zove `.hide()`, ne
  `.minimize()`, pa ne pokreće moj novi `"minimize"` listener).

## Šta nije dirano

- `MiniComputerWindow`/`miniWindow` (veliki orb, Computer Mode) — taj prozor
  je `minimizable: false`, van obima ovog fix-a (situacija #2 iz spec-a je
  već riješena postojećim `set_mode`-vezanim show/hide).
- `handleAppMinimize()` — nepromijenjen, i dalje samo `win.minimize()`.

## Verifikacija

- `node --check electron/main.cjs` — čisto.
- `mcp__gitnexus__impact(target: "createWindow", direction: "upstream")` —
  risk LOW, jedini pozivalac je `main.cjs` (gdje je i izmjena).
- Runtime NIJE testiran — Electron desktop app, nema browser-automation alata
  u ovom okruženju.

## Rizici/ograničenja

- Ako je korisnik RUČNO uključio companion orb prije minimize-a, restore će
  ga svejedno sakriti (simetrično ponašanje, korisnikov izabran odgovor) —
  ručni toggle se ne pamti kao "trajna" preferenca kroz minimize/restore
  ciklus. Ovo je namjerno, ne bug.

## Potreban follow-up

Runtime test korisnika — minimize glavnog prozora treba prikazati mali orb,
restore ga treba sakriti. Ako korisnik primijeti neočekivano ponašanje kod
kombinacije Computer Mode + minimize (rubni slučaj koji nije eksplicitno
testiran jer je glavni prozor u Computer Mode-u već `.hide()`-ovan, ne
minimiziran), prijaviti kao zaseban nalaz.

## Potrebna korisnička potvrda

Runtime test prije nego se ovo smatra potpuno gotovim.
