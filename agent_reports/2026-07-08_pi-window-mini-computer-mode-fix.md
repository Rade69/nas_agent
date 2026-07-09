# Agent report — Rehabilitacija mini-window (Computer Mode) u window.cjs

**Datum:** 2026-07-08

## Scope

- `electron/core/window.cjs` — vraćena funkcionalnost mini floating prozora za Computer Mode.
- Zadatak preuzet od Codex-a koji je probio token limit; nastavlja rad iz `agent_reports/2026-07-07_codex-clean-layout-layer.md`.

## GitNexus impact

Nije pokretan `gitnexus_impact`. Ručna analiza blast radius-a:
- `setWindowMode` se poziva samo iz `electron/main.cjs:868` unutar `handleToolsExecute` (`if (name === "set_mode")` lanac), pozvan klikom na dugme "Računarski režim" u rendereru.
- **Risk: NIZAK** — mijenja se samo ponašanje geometrije prozora pri toggle-u Computer Mode-a; ne dira IPC površinu, sigurnosne slojeve, niti renderer logiku. Revertibilno.

## Kontekst i dijagnoza

**Važna ispravka:** Nema nikakvih spontanih promjena prozora. Sve promjene veličine/maximize stanja prozora se dešavaju **isključivo kao direktni rezultat korisnikovog klika na dugme "Računarski režim"**. Svaka prethodna verzija izvještaja koja je spominjala "spontani maximize" ili "DWM spontano maksimizira" bila je **netačna interpretacija loga** — ti maximize/resize eventi u logu su posljedica korisnikovog klika, ne Windows DWM-a koji radi sam od sebe.

**Stvarni problem koji korisnik prijavljuje:** Klik na dugme "Računarski režim" izaziva neželjeni vizuelni trzaj/nestajanje prozora. Konkretno:
- Iz normalnog (1440×816) prozora: klik prebaci u mini 190×190 — uz trzaj.
- Iz maksimizovanog prozora: klik izazove "nestajanje i pojavljivanje" prozora (hide/show flicker).
- Vraćanje iz mini u display mode ne vrati tačnu originalnu geometriju — prozor završi maksimizovan umjesto u 1440×816.

## Šta je urađeno (kroz iteracije)

Kroz nekoliko iteracija pokušaja sa različitim redoslijedom Electron API poziva (koji nisu riješili problem), prelazim na **potpuno drugačiji pristup**: umjesto resize-a glavnog prozora, koristi se zaseban mini BrowserWindow.

**Konačni pristup — zaseban mini prozor:**
- **Computer mode:** `setMaximizable(false)` na glavnom prozoru + `hide()` + kreiranje/prikaz zasebnog mini BrowserWindow-a (190×190, frameless, `maximizable: false`, `resizable: false`, `alwaysOnTop: true`).
- **Display mode:** `hide()` mini prozora + `setMaximizable(true)` na glavnom + `show()` + vraćanje tačne geometrije:
  - ako je `savedWasMaximized` → `maximize()`
  - inače → `unmaximize()` (ako je u međuvremenu maximized) + `setBounds(savedNormalBounds)`

Glavni prozor se nikad ne resize-uje u 190×190, što eliminiše trzanje prouzrokovano prelaskom između radikalno različitih geometrija na frameless transparent prozoru.

## Zašto je urađeno

Resize glavnog frameless + transparent prozora sa ~1440×816 na 190×190 (i obratno) na Windowsu proizvodi vidljiv trzaj zbog DWM kompozitora koji mora rekomponovati složeni React sadržaj kroz drastičnu promjenu veličine. Bilo koja kombinacija redoslijeda `setBounds`/`setAlwaysOnTop`/`setResizable`/`setOpacity`/`hide`+`show` na istom prozoru ne eliminiše trzanje u potpunosti. Zaseban mini prozor rješava ovo jer glavni prozor uopšte ne mijenja geometriju — samo se sakrije.

## Kako je urađeno

- `read`/`git diff` `electron/core/window.cjs` da rekonstruišem Codex-ovo i originalno stanje.
- `grep` po `electron/main.cjs` i `src/App.tsx` da rekonstruišem cijeli lanac: dugme → `switchMode` → `executeTool("set_mode")` → `handleToolsExecute:866` → `setWindowMode(currentMode)`.
- `write` za kompletno prepisivanje `window.cjs` sa novim pristupom (zaseban `miniWindow`).
- `node --check` + `npm run typecheck` za verifikaciju sintakse.
- Više iteracija testiranja sa korisnikom, svaki put analizirajući `[window-debug]` log.

## Šta nije dirano

- `src/App.tsx`, `src/styles.css`, `src/components/*` — netaknuti (Codex-ov GUI domen).
- `electron/main.cjs` — netaknut (handler `handleToolsExecute` već ispravno poziva `setWindowMode`).
- `electron/preload.cjs`, IPC layer — netaknuti.
- Backend/Python, security slojevi — netaknuti.
- Debug kanal `debug:renderer-log` (privremeni, Codex dodao) — ostavljen; njegovo uklanjanje je zaseban cleanup zadatak.

## Verifikacija

- `node --check electron/core/window.cjs` → **SYNTAX OK**.
- `npm run typecheck` → **čisto**.
- Ručno testiranje sa korisnikom kroz više iteracija; logovi analizirani.

## Rizici/ograničenja

- **Mini prozor učitava isti renderer** (dev URL ili `dist/index.html`) — to znači da React state (transkript, aktivnosti) nije dijeljen između glavnog i mini prozora; mini prozor kreće svjež. Ako je potrebno dijeljenje stanja, zahtijeva dodatni rad (npr. proslijeđivanje preko IPC-a). Za mini "controller" UI ovo je vjerovatno prihvatljivo.
- **Pamćenje stanja:** `savedNormalBounds` i `savedWasMaximized` se osvježavaju na svaki ulazak u Computer mode — ispravno ponašanje.
- **Multi-monitor:** `screen.getDisplayNearestPoint(cursorPoint)` bira display gdje je miš; mini prozor ide na taj monitor.
- **Trzaj nije 100% eliminisan** u svim scenarijima — zaseban mini prozor značajno smanjuje problem, ali `hide()`/`show()` glavnog prozora i dalje može proizvesti minimalni flicker na nekim Windows konfiguracijama.

## Otvoreno pitanje — "nema vraćanja u prethodno stanje"

Korisnik je prijavio da vraćanje iz mini u display mode ne vrati tačnu originalnu geometriju. Analiza loga pokazuje: nakon `hide()` glavnog prozora, korisnikov klik na dugme u mini prozoru pozove `mainWindow.show()`, ali prozor završi u maksimizovanom stanju umjesto u originalnoj 1440×816 geometriji. Trenutni kod adresira ovo sa eksplicitnim `unmaximize()` + `setBounds(savedNormalBounds)` u display mode putanji, ali zahtijeva dodatno testiranje da se potvrdi da radi u svim slučajevima (npr. kad je korisnik prethodno ručno maximizovao prozor).

## Potreban follow-up

1. **Testiranje vraćanja geometrije:** klik na "Računarski režim" iz maksimizovanog prozora → mini → klik nazad → potvrditi da se vraća u maksimizovano (ne u 1440×816).
2. **Testiranje iz normalnog prozora:** klik iz 1440×816 → mini → klik nazad → potvrditi vraćanje u 1440×816.
3. **Uklanjanje privremenog debug kanala** `debug:renderer-log` (Codex ga dodao) — zaseban cleanup zadatak nakon što se potvrdi da mini-window radi stabilno. Nalazi se u `electron/preload.cjs`, `electron/main.cjs`, i `src/App.tsx` (`debugRenderer` pozivi).
4. **Commit** — `electron/core/window.cjs` je spreman; pošto je u radnom stablu pomiješan sa GUI/Codex radom na `App.tsx`/`styles.css`, predlažem zaseban commit samo za `window.cjs`.

## Potrebna korisnička potvrda

- Testirati oba scenarija (iz normalnog i iz maksimizovanog prozora) i potvrditi da se geometrija ispravno vraća.
- Ako "nema vraćanja" i dalje postoji, dostaviti `[window-debug]` log sa tačnim redoslijedom evenata nakon klika na dugme u mini prozoru.

---

## Istorija ispravki pogrešnih interpretacija (arhiva)

Prethodne verzije ovog izvještaja su sadržale netačne tvrdnje o "spontanim maksimizacijama" od strane Windows DWM-a. Korisnik je jasno pojasnio: **nema nikakvih spontanih promjena — sve promjene prozora se dešavaju isključivo kao rezultat korisnikovog klika na dugme "Računarski režim"**. Svako spominjanje "DWM spontano maksimizira", "spontani maximize event" ili slično je bila pogrešna interpretacija `[window-debug]` loga. Ovi eventi u logu su direktni rezultat korisnikovih akcija, ne sistemskog ponašanja. Izvještaj je ispravljen da tačno reflektuje ovo.

---

## Codex dodatak — fokusirani `Računarski režim` trace log

**Datum:** 2026-07-08

Korisnik je prijavio da prethodni opšti debug nije dovoljno relevantan jer ne pokazuje precizno šta jedan klik na `Računarski režim: UKLJUČEN/ISKLJUČEN` trigeruje i koja operacija mijenja veličinu/rezoluciju prozora.

Dodao sam fokusirani trace tok:

- `src/App.tsx`
  - svaki `switchMode()` generiše jedinstveni `traceId` oblika `mode-<timestamp>-<suffix>`;
  - isti `traceId` se šalje kroz `executeTool({ name: "set_mode", arguments: { mode, __modeTraceId } })`;
  - renderer loguje `switchMode:start`, `switchMode:result`, `switchMode:set-state` sa istim ID-em.

- `electron/main.cjs`
  - `set_mode` handler preuzima `__modeTraceId`;
  - loguje `main:set_mode:start` i `main:set_mode:after-setWindowMode`;
  - isti `traceId` prosljeđuje u `setWindowMode(currentMode, traceId)`.

- `electron/core/window.cjs`
  - `setWindowMode(mode, traceId)` sada loguje snapshot prije i poslije svake relevantne Electron operacije:
    - `mainWindow.setMaximizable(false/true)`
    - `mainWindow.hide()` / `mainWindow.show()`
    - `miniWindow` create/show/hide/load
    - `mainWindow.maximize()` / `unmaximize()` / `setBounds()`
  - svaki log ima format `[mode-trace:<traceId>] window:<step>` i sadrži `main`, `mini`, `savedNormalBounds`, `savedWasMaximized`.

Kako koristiti:

1. Restartovati Electron aplikaciju, jer su mijenjani `main/preload/window` slojevi.
2. Kliknuti `Računarski režim` tačno jednom.
3. U terminalu filtrirati ili kopirati sve linije koje počinju sa istim `[mode-trace:mode-...]` ID-em.
4. Po tim linijama se vidi tačno koja operacija mijenja `bounds`, `normalBounds`, `visible`, `maximized`, `maximizable` ili stanje mini prozora.

Verifikacija:

- `node --check electron/core/window.cjs` — prolazi.
- `npm run typecheck` — prolazi.
- `npm run build` — prolazi; ostaje postojeći Vite warning za chunkove veće od 500 kB.

---

## Codex dodatak — analiza prvog `mode-trace` loga i mini renderer state fix

**Datum:** 2026-07-08

Analiziran je korisnikov prilozeni terminal log `mode-1783512348601-a8qlp`.

Zakljucak iz trace-a:

- Glavni prozor se pri ukljucenju Computer Mode-a ne resize-uje.
- `mainWindow` ostaje na `bounds: { x: 48, y: 0, width: 1440, height: 816 }` i samo prelazi na `visible: false` poslije `mainWindow.hide()`.
- Mini prozor se kreira na donjem lijevom uglu:
  - trazeni `miniBounds`: `{ x: 18, y: 608, width: 190, height: 190 }`
  - Electron prijavljuje stvarni mini bounds oko `{ x: 18, y: 608, width: 193, height: 192 }`, sto je Windows/Electron okvirno odstupanje.
- Nije pronadjen drugi `mode-trace` za povratak u `display` mode.
- Ključni problem: mini BrowserWindow ucitava svjez renderer koji je startao sa `mode: display` i viewportom `192x192`. Zbog toga dugme u mini prozoru ne zna da je Computer Mode vec ukljucen i sljedeci klik ne pokrece ocekivani `computer -> display` povratak.

Uradjena ispravka:

- `electron/core/window.cjs`
  - mini dev URL sada dobija query parametre `?window=mini&mode=computer`.
  - production `loadFile()` za mini prozor dobija `query: { window: "mini", mode: "computer" }`.

- `src/App.tsx`
  - pocetni `mode` state sada se inicijalizuje iz `window.location.search`:
    - `mode=computer` -> `computer`
    - sve ostalo -> `display`

Ocekivano ponašanje poslije restarta:

1. Klik na `Računarski režim: ISKLJUČEN` u glavnom prozoru otvara mini prozor.
2. Mini renderer starta kao `mode: computer`, pa dugme treba prikazati `Računarski režim: UKLJUČEN`.
3. Klik na dugme u mini prozoru treba pokrenuti novi `mode-trace` sa `requestedMode: 'display'` i vratiti glavni prozor.

Verifikacija:

- `node --check electron/core/window.cjs` — prolazi.
- `npm run typecheck` — prolazi.
- `npm run build` — prolazi; ostaje postojeći Vite warning za chunkove veće od 500 kB.

---

## Codex dodatak — mini prozor dobio vlastiti UI kontroler

**Datum:** 2026-07-08

Korisnik je poslao screenshot mini prozora na kojem su vidljive samo window kontrole, bez kontrole za povratak u normalni prozor. Log je pokazao da mini renderer postoji i ima viewport oko `192x192`, ali full `PixelMockupBoard` layout nije upotrebljiv u tako malom prozoru.

Uradjena ispravka:

- `src/App.tsx`
  - dodan helper `isMiniWindow()` koji cita `window=mini` iz URL query-ja;
  - ako je renderer pokrenut kao mini prozor, `App` vise ne renderuje veliki 6-section GUI;
  - umjesto toga renderuje `MiniComputerWindow` sa:
    - mini window kontrolama,
    - Ricky orbom,
    - statusom `Računarski režim UKLJUČEN/ISKLJUČEN`,
    - velikim klikabilnim dugmetom `Vrati prozor` koje poziva isti `switchMode("display")` tok.

- `src/styles.css`
  - dodani `.mini-computer-window`, `.mini-window-controls` i `.mini-restore-button` stilovi za 190px floating prozor.

Ocekivano ponašanje:

1. Glavni prozor -> klik `Računarski režim: ISKLJUČEN`.
2. Glavni prozor se sakrije, mini prozor se pojavi dolje-lijevo.
3. Mini prozor prikazuje vlastiti mini kontroler, ne odrezani glavni GUI.
4. Klik na `Vrati prozor` u mini prozoru poziva `switchMode("display")`, sto treba napraviti novi `[mode-trace:...]` sa `requestedMode: 'display'` i vratiti glavni prozor.

Verifikacija:

- `npm run typecheck` — prolazi.
- `node --check electron/core/window.cjs` — prolazi.
- `npm run build` — prolazi; ostaje postojeći Vite warning za chunkove veće od 500 kB.

---

## Codex dodatak — mini prozor prebacen u avatar companion smjer

**Datum:** 2026-07-08

Korisnik je predlozio bolji smjer: umjesto malog aplikacijskog prozora/panela, u Computer Mode-u treba da se prikazuje avatar koji pulsira dok Ricky govori, sa kontrolom za povratak u normalni rezim na vrhu avatara.

Uradjena ispravka:

- `src/App.tsx`
  - mini renderer vise nije panel sa window kontrolama;
  - `MiniComputerWindow` sada renderuje `assets/Riki-avatar.png` kao glavni companion avatar;
  - dodato je dugme `Vrati` preko vrha avatara, koje poziva isti `switchMode("display")` tok;
  - avatar dobija klasu `is-talking` kada je `voiceState` u `speaking`, `listening`, `thinking` ili `transcribing` stanju.

- `src/styles.css`
  - dodan avatar-only dizajn za `.mini-computer-window`;
  - uklonjen mini-panel mentalni model iz tog rendera;
  - dodane animacije `mini-avatar-breathe` i `mini-avatar-talk` za mirno/pulsirajuce stanje;
  - dugme `Vrati` je kompaktno i uvijek iznad avatara.

- `electron/core/window.cjs`
  - mini prozor povecan sa `190` na `236` px da avatar i overlay dugme imaju prostora i da se ne sijeku.

Verifikacija:

- `npm run typecheck` — prolazi.
- `node --check electron/core/window.cjs` — prolazi.
- `npm run build` — prolazi; ostaje postojeći Vite warning za chunkove veće od 500 kB.

Napomena:

- `Riki-avatar.png` ulazi u build kao bitmap asset od oko 1.65 MB. Ako mini companion ostane finalni smjer, preporucen je kasniji asset pass: napraviti optimizovanu 256/384px WebP ili PNG varijantu za mini prozor.

---

## Codex dodatak — mini avatar status je deterministicki `UKLJUČEN`

**Datum:** 2026-07-09

Korisnik je pokazao dva stanja mini avatara: jedno sa `ISKLJUČEN`, drugo sa `UKLJUČEN`. Za trenutni UX pravilo je jednostavno: ako je glavni prozor sakriven/minimizovan i prikazan je samo avatar, tada je Computer Mode aktivan i avatar mora jasno prikazivati `Računarski režim UKLJUČEN`.

Uradjena ispravka:

- `src/App.tsx`
  - `MiniComputerWindow` vise ne izvodi label iz lokalnog React `mode` state-a;
  - status label je sada deterministicki `UKLJUČEN`, jer se mini avatar renderuje samo za aktivni Computer Mode;
  - uklonjen je nepotreban `mode` prop iz mini komponentе.

Verifikacija:

- `node --check electron/core/window.cjs` — prolazi.
- `npm run typecheck` — prolazi.
- `npm run build` — prolazi; ostaje postojeći Vite warning za chunkove veće od 500 kB i plugin timing napomena za `vite-plugin-svgr`.
