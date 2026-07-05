# Agent report — Dovršetak FAZE 3: core/ipc.cjs IPC wiring sloj

**Datum:** 2026-07-05

## Scope

- Novi: `electron/core/ipc.cjs`.
- Izmjena: `electron/main.cjs` (4 `ipcMain.handle(...)` inline registracije pretvorene u imenovane funkcije + jedan `registerIpcHandlers(...)` poziv; `ipcMain` uklonjen iz top-level require destructure jer se više ne koristi direktno u ovom fajlu).
- Izmjena: `docs/MIGRATION_PLAN.md` (FAZA 3 status → ✅ urađeno; ažurirana napomena o preduslovu za Security PR-1 u "Security Gates" sekciji).

## GitNexus impact

`gitnexus_impact({target: "setWindowMode", direction: "upstream", repo: "nas_agent"})` → risk LOW, jedini pozivalac `electron/main.cjs` (fajl-nivo granularnost, kao i ranije primijećeno u FAZA 3 izvještaju — GitNexus ne razlaže dobro inline callback-ove u ovom fajlu).

`gitnexus_detect_changes({repo: "nas_agent", scope: "all"})` nakon izmjene → `risk_level: "low"`, `affected_count: 0` (nijedan downstream execution flow nije pogođen).

## Šta je urađeno

Korisnik je tražio da nastavim sa poslom koji sam sâm predložio dok Codex radi FAZU 4: dovršetak FAZE 3 (izdvajanje `core/ipc.cjs`), koji je bio namjerno odgođen u prvobitnoj FAZI 3 (vidi `agent_reports/2026-07-05_split-main-cjs-faza3.md`, sekcija "Šta nije dirano") jer bi tada zahtijevao diranje neisprepletenog `tools:execute` bloka.

Prije izmjene pročitan je cijeli `electron/main.cjs` (1457 linija) i `electron/preload.cjs`. Otkriveno je da `preload.cjs` **već** poštuje allowlist princip iz `SECURITY_HARDENING_PLAN.md` (samo 4 imenovane funkcije: `createRealtimeToken`, `executeTool`, `getToolSpecs`, `quitApp`; nema generic `ipcRenderer.invoke` prolaza niti `window.require`). Dakle stvarni sigurnosni rizik ("generic IPC invoke") nije postojao — nedostajao je samo fizički odvojen fajl koji čini IPC allowlist eksplicitnim i lakim za audit (Security PR-1 zahtjev iz `SECURITY_HARDENING_PLAN.md`).

Da bi se izbjegao "veliki refaktor u jednom koraku" (CLAUDE.md pravilo), obim je namjerno **sužen** na čisto mehaničku promjenu:

1. 4 `ipcMain.handle(channel, callback)` inline poziva u `main.cjs` (`tools:list`, `app:quit`, `realtime:create-token`, `tools:execute`) pretvorena u imenovane funkcije (`handleToolsList`, `handleAppQuit`, `handleRealtimeCreateToken`, `handleToolsExecute`) — **tijela funkcija nisu mijenjana ni za slovo**, samo omotač (`ipcMain.handle("x", async () => {...})` → `async function handleX() {...}`).
2. Novi `electron/core/ipc.cjs` izvozi `registerIpcHandlers(handlers)` — generička ali eksplicitna wiring funkcija (`Object.entries(handlers).forEach(([channel, handler]) => ipcMain.handle(channel, handler))`), pozvana jednom u `main.cjs` sa mapom sva 4 kanala neposredno prije `app.whenReady()`.
3. Business logika (web search, image generation, thumbnail board, notes/records CRUD, computer-use pozivi) **ostaje u `main.cjs`, netaknuta** — namjerno, isto obrazloženje kao u prvobitnoj FAZI 3 (ta logika pripada kasnijim fazama: FAZA 7/8 storage, FAZA 11 tool registry, FAZA 15 AI integracije).

## Zašto je urađeno

FAZA 3 acceptance kriterijum (razbiti `main.cjs` bez promjene ponašanja) je ostao nezavršen zbog `core/ipc.cjs`. Ovo je sad i formalni preduslov za Security PR-1 iz `SECURITY_HARDENING_PLAN.md` ("generic IPC zabrana", "preload API inventory") — ta provjera treba jedno mjesto gdje se vidi tačno koji kanali postoje, umjesto da se skenira cijeli 1400+ linijski fajl.

## Kako je urađeno

`Read` cijelog `main.cjs` i `preload.cjs`/`window.cjs`/`env.cjs`. `Edit` u main.cjs: (1) require blok — dodat `core/ipc.cjs`, uklonjen `ipcMain` iz destructure, (2) 4 mjesta gdje su `ipcMain.handle(...)` pozivi zamijenjeni imenovanim funkcijama (uz ispravku zatvarajućih zagrada `});` → `}`), (3) dodat `registerIpcHandlers({...})` poziv pred `app.whenReady()`. `Write` za novi `core/ipc.cjs`.

## Šta nije dirano

- Sva business logika unutar handler tijela (web search, image/thumbnail generacija, notes/records, computer-use pozivi) — bukvalno identičan kod, samo premješten iz anonimne arrow funkcije u imenovanu function deklaraciju.
- `preload.cjs` — nije mijenjan (već ispravan).
- DB/storage logika, `RICKY_INSTRUCTIONS`, `toolSpecs` — netaknuti.
- Tool input/output formati — identični kao prije.

## Verifikacija

1. `node --check electron/main.cjs electron/core/ipc.cjs` — sintaksa OK.
2. Pokušaj pokretanja `npx electron .` u ovoj sesiji prvo je pukao sa `TypeError: Cannot read properties of undefined (reading 'handle')` — **potvrđeno da je identična greška prisutna i na originalnom, neizmijenjenom `main.cjs`-u** (testirano sa `git stash`/`git stash pop`), dakle riječ je o poznatom ograničenju sandbox okruženja (`ELECTRON_RUN_AS_NODE` postavljen u ovoj Bash sesiji tjera Electron da se pokrene kao plain Node proces bez pravog `ipcMain` API-ja — isti root cause dokumentovan u `agent_reports/2026-07-05_split-main-cjs-faza3.md`), ne regresija iz ove izmjene.
3. `env -u ELECTRON_RUN_AS_NODE npx electron .` — pravi Electron proces, **bez `ipcMain` greške**. Jedina greška je očekivan `ERR_FILE_NOT_FOUND` za `dist/index.html` (nema build artifakta u ovoj sesiji — `npm run build` nije pokretan, van obima ovog zadatka). Ovo potvrđuje da `registerIpcHandlers(...)` ispravno registruje sva 4 kanala pod stvarnim Electron runtime-om.
4. `gitnexus_detect_changes` (scope "all") → risk LOW, 0 affected execution flows.

## Rizici / ograničenja

- `core/ipc.cjs` je namjerno "glup" wiring sloj (generic loop nad `Object.entries`) — ovo NIJE sam allowlist-enforcement (ne odbija nepoznate kanale iz rendererskog koda), samo čini eksplicitnim koji kanali postoje. Stvarni allowlist/permission engine dolazi tek u FAZA 10 (permission layer) i Security PR-1/2 implementaciji.
- Handler tijela i dalje sadrže svu poslovnu logiku pomiješanu zajedno (npr. `handleToolsExecute` je i dalje ~220 linija if/else) — ovo ostaje netaknuto namjerno, po istom obrazloženju kao prvobitna FAZA 3 (izdvajanje te logike je poseban budući korak, vezan za FAZA 7/8/11/15).

## Potreban follow-up

- Sljedeći aktivan korak po planu ostaje FAZA 4 (Python backend skeleton, Codex, već u toku).

## Potrebna korisnička potvrda

Riješeno — korisnik je pokrenuo app preko `Ricky (Nas-agent).lnk` (desktop prečica, cilja `Pokreni-Ricky.bat`) i poslao screenshot: Ricky lice renderovano ispravno, `set_mode` tool call je prošao kroz cijeli IPC lanac (`tools:execute` → `handleToolsExecute` → `core/window.cjs` `setWindowMode`) i artifact panel je ispravno prikazao "Mode switched to display mode." Ovo potvrđuje da `core/ipc.cjs` wiring sloj radi identično kao prije refaktora, u stvarnoj desktop sesiji (van sandbox ograničenja). FAZA 3 se sada smatra u potpunosti verifikovanom za ovaj obim (IPC registracija); Notepad computer-use smoke test iz prvobitnog FAZA 3 izvještaja ostaje odvojen, nepromijenjen follow-up.
