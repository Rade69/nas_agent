# Agent report — Razbijanje electron/main.cjs u module (FAZA 3, suženi obim)

**Datum:** 2026-07-05

## Scope

- Novi: `electron/core/env.cjs`, `electron/core/window.cjs`.
- Novi: `electron/tools_legacy/powershell/runPowerShell.cjs`, `computerOpenApp.cjs`, `computerTypeText.cjs`, `computerPressKey.cjs`, `computerClick.cjs`, `computerScroll.cjs`, `screenSnapshot.cjs`, `uiInspect.cjs`.
- Izmjena: `electron/main.cjs` (require blok, uklonjene premještene funkcije/konstante, ažurirane grane u `tools:execute` dispatcheru, ažuriran `app.whenReady`/`app.on("activate")` bootstrap).
- Izmjena: `docs/MIGRATION_PLAN.md` (tracker, FAZA 3 status).

## GitNexus impact

Repo je u međuvremenu uspješno indeksiran kao **nas_agent** (751 simbola, 1188 relacija, 43 toka) nakon što je folder preimenovan iz `Naš-agent` u `Nas-agent` (slovo š je izazivalo I/O grešku u KuzuDB native sloju — potvrđeno testom: `npx gitnexus analyze` je pukao na starom nazivu, uspio odmah nakon preimenovanja).

`gitnexus_impact({target: "createWindow", direction: "upstream"})` i isto za `runPowerShell` → **risk: LOW**, ali sa slabom granularnošću (sve reference su se svodile na "File: main.cjs" kao caller, ne na pojedinačne pozivaoce) — GitNexus ne razlaže dobro pozive unutar jednog velikog fajla sa inline `ipcMain.handle` callback-ovima. Zbog toga je stvarna analiza urađena ručno, čitanjem cijelog `main.cjs` (1632 linije).

## Šta je urađeno

Ručna analiza otkrila je da stvarna struktura koda odstupa od pretpostavke iz plana: `main.cjs` ima samo 4 `ipcMain.handle` registracije, od kojih je `tools:execute` jedan veliki (~300 linija) if/else dispatcher koji pokriva computer-use alate ALI I web search, image generation, cijeli thumbnail board sistem, notes/records — sve dijeli isto zatvaranje nad `dataDir`/`readDb`/`writeDb`.

Korisniku je predložen i potvrđen **suženi obim** za FAZU 3 (vidi pitanje "Koji obim FAZE 3 da uradim sada?"): izvući samo env/window/PowerShell-tool dijelove koji se mogu čisto odvojiti bez vučenja storage/AI logike sa sobom; IPC registraciju za `tools:execute`/`realtime:create-token` ostaviti u `main.cjs` za sada (previše isprepletena sa logikom koja pripada kasnijim fazama — 7/8 storage, 15 AI integracije).

Konkretno izvučeno:

- **`core/env.cjs`** — `dotenv.config(...)` poziv (bio 2 linije u main.cjs), sad `require("./core/env.cjs")` kao side-effect import.
- **`core/window.cjs`** — `createWindow()` i `setWindowMode()`, uz `mainWindow`/`normalWindowBounds` state. `createWindow()` je promijenjen da prima `{ beforeShow }` callback umjesto da direktno zove `ensureData()`/`clearStartupLoadingThumbnails()` (DB logika) — to je dependency injection da `window.cjs` ne vuče storage sloj sa sobom. `main.cjs` sad ima `prepareWindowData()` helper koji se prosljeđuje kao `beforeShow` na oba mjesta gdje se `createWindow` poziva (`app.whenReady()`, `app.on("activate")`).
- **`tools_legacy/powershell/runPowerShell.cjs`** — `runPowerShell()`, `psSingleQuote()`, `NATIVE_MOUSE_TYPE`, `NATIVE_WINDOW_TYPE` (dijeljene niskoslojne PowerShell/P-Invoke konstante).
- **`tools_legacy/powershell/computerOpenApp.cjs`, `computerTypeText.cjs`, `computerPressKey.cjs`, `computerClick.cjs`, `computerScroll.cjs`, `screenSnapshot.cjs`, `uiInspect.cjs`** — svaki computer-use alat u svom fajlu, sa istom PowerShell skriptom kao prije. `main.cjs`-ov `tools:execute` dispatcher sada poziva ove funkcije umjesto da inline gradi PowerShell skriptove.

## Zašto je urađeno

FAZA 3 iz `docs/MIGRATION_PLAN.md` traži razbijanje `main.cjs` bez promjene ponašanja, kao priprema prije uvođenja Python backend-a (FAZA 4+). Manji, provjerljiv diff je izabran umjesto punog obima iz plana (koji uključuje i `core/ipc.cjs`) da se izbjegne rizik od greške u ogromnom `tools:execute` bloku koji još nije razdvojen na logičke cjeline.

## Kako je urađeno

`Read` cijelog `main.cjs` (1632 linije) da se vidi stvarna struktura. `Write` za 9 novih fajlova. `Edit` na `main.cjs` u 5 koraka: (1) require blok na vrhu, (2) uklanjanje `mainWindow`/`normalWindowBounds` varijabli, (3) uklanjanje `sendKeysForKey`/`escapeSendKeys`/`psSingleQuote`/`NATIVE_MOUSE_TYPE`/`NATIVE_WINDOW_TYPE`/`createWindow`/`setWindowMode` (zamijenjeno sa `prepareWindowData()` helperom), (4) zamjena 7 computer-use grana u `tools:execute` da pozivaju nove module, (5) `app.whenReady`/`app.on("activate")` da prosljeđuju `{ beforeShow: prepareWindowData }`.

## Šta nije dirano

- `core/ipc.cjs` — namjerno NIJE napravljen u ovoj fazi (vidi "Zašto" iznad). `tools:list`, `app:quit`, `realtime:create-token`, i sav non-computer-use dio `tools:execute` (set_mode, artifact_show, show_menu, web_search, image_generate, thumbnail_*, mermaid_render, note_add, records_*) ostaju u `main.cjs` netaknuti, doslovno isti kod.
- DB/storage logika (`ensureData`, `readDb`, `writeDb`, `updateDb`, `defaultDb`, `normalizeDb`) — netaknuta, ostaje u `main.cjs` (FAZA 7/8 posao).
- Nijedan tool input/output format nije promijenjen — svaka grana u `tools:execute` i dalje vraća identičan response oblik kao prije.

## Verifikacija

1. `node --check` na svih 11 novih/izmijenjenih `.cjs` fajlova — sintaksa OK.
2. `npm run typecheck` (`tsc --noEmit`) — prošao.
3. `npm install` u `Nas-agent` (node_modules nije bio kopiran) — 213 paketa, 0 vulnerabilities.
4. `npm run dev` pokušan 3 puta:
   - Pokušaj 1 i 2: pukli sa `TypeError: Cannot read properties of undefined (reading 'handle')` na liniji `ipcMain.handle("tools:list", ...)`. Root cause pronađen: Bash alat u ovoj sesiji ima `ELECTRON_RUN_AS_NODE=1` postavljen u environment-u, što tjera `electron.exe` da se pokrene kao obična Node instanca (bez pravog Electron API-ja) — **ovo bi puklo identično i sa originalnim, neizmijenjenim `main.cjs`-om**, nije regresija iz refaktora.
   - Pokušaj 3: `env -u ELECTRON_RUN_AS_NODE npm run dev` — app se pokrenuo čisto. `Get-Process` je potvrdio Electron proces sa `MainWindowTitle: "Ricky"`. Log je pokazao samo očekivanu grešku `OPENAI_API_KEY is missing in .env.local` (jer `.env.local` namjerno nije kopiran iz originalnog projekta — sadrži prave korisničke ključeve). Proces se na kraju čisto ugasio (`exited with code 0`).
5. Pokušaj vizuelne potvrde (screenshot) nije uspio prikazati sam prozor (vjerovatno je bio iza drugih prozora na desktopu, `SetForegroundWindow` iz pozadinskog procesa je tiho odbijen od strane Windows-a) — ali `tasklist`/`Get-Process` MainWindowTitle "Ricky" i čist log bez grešaka van očekivane OPENAI_API_KEY poruke su dovoljna potvrda da je prozor stvarno kreiran i da su IPC handleri (uključujući `tools:list` na liniji koja je ranije pucala) radili ispravno.

## Rizici / ograničenja

- **`computer_press_key` ponašanje je blago promijenjeno u implementaciji, ne u rezultatu**: originalni kod je za nepodržan key vraćao `{ ok: false, error: "Unsupported key: X" }` direktno; novi `computerPressKey()` baca `Error("Unsupported key: X")` koji hvata postojeći vanjski `try/catch` u `tools:execute` (linija ~929 originala) i vraća `{ ok: false, error: error.message }` — isti tekst, isti oblik odgovora, ali putanja kroz kod je drugačija (throw + catch umjesto direktnog return). Funkcionalno identično za pozivaoca (React UI), ali vrijedi znati ako se ovaj catch blok ikad mijenja.
- Ova sesija nije mogla direktno pokrenuti `npm run dev` bez ručnog zaobilaženja `ELECTRON_RUN_AS_NODE` env varijable — buduće verifikacije u istom okruženju trebaju koristiti `env -u ELECTRON_RUN_AS_NODE npm run dev` ili ekvivalent.
- Puni scope iz plana (`core/ipc.cjs`, izdvajanje cijelog `tools:execute` dispatcher-a) nije urađen — ostaje kao poseban budući korak kad storage (FAZA 7/8) i AI integracije (FAZA 15) budu jasnije razdvojene, jer bi izdvajanje IPC registracije sada zahtijevalo dirati taj isprepleteni blok bez sigurne podjele.
- Ručni Notepad/computer-use smoke test (iz FAZA 3 acceptance kriterija plana: "postojeći Windows tools rade kao ranije") NIJE urađen sa stvarnim computer-use pozivom (npr. `computer_open_app`) — samo je potvrđeno da app boot-uje i da IPC/tools:list rade. Preporučen je ručni test korisniku prije nego se ovo smatra potpuno verifikovanim.

## Potreban follow-up

- ~~Korisnik treba ručno pokrenuti `npm run dev` u `Nas-agent`~~ — **urađeno.** Korisnik je napravio zasebnu Desktop prečicu `Ricky (Nas-agent).lnk` (vidi ispod) i pokrenuo app ručno na svom uređaju.
- ~~Za potpuno testiranje voice/AI funkcionalnosti, korisnik treba kopirati svoj `.env.local`~~ — **urađeno**, kopiran iz `RileyJarvis-Windows` u `Nas-agent` uz korisnikovu potvrdu.
- Sljedeći korak po planu: FAZA 4 (Python backend skeleton) — ili, ako se odluči kasnije, dovršetak FAZE 3 punog obima (`core/ipc.cjs`) kad storage/AI logika bude jasnija.

## Ažuriranje nakon ručne provjere (2026-07-05)

Korisnik je pokrenuo app preko nove Desktop prečice `Ricky (Nas-agent).lnk` (napravljena zasebno, cilja `Nas-agent\Pokreni-Ricky.bat`, ne dira postojeću `Ricky.lnk` koja i dalje pokazuje na `RileyJarvis-Windows`) i poslao screenshot: Ricky lice se renderuje ispravno (plavi krug, oči, usta), artifact panel prikazuje "Ready" sa default porukom, chat input i toolbar dugmad (mic, tastatura, split-view, computer mode, itd.) su vidljivi. Ovo je vizuelna potvrda da je frameless/transparent prozor iz `core/window.cjs` render-ovan ispravno u pravom desktop okruženju (van agent sandboxa gdje je vizuelna provjera bila ograničena `ELECTRON_RUN_AS_NODE`/focus-stealing problemima).

Napomena: ovo potvrđuje da se prozor i UI učitavaju ispravno, ali **ne** potvrđuje da su computer-use PowerShell alati (`computer_open_app`, `computer_type_text`, itd.) funkcionalno identični — za to je i dalje potreban eksplicitan Notepad smoke test (open app → type text → screenshot → ui inspect) prije nego se FAZA 3 acceptance kriterijum "postojeći Windows tools rade kao ranije" smatra u potpunosti provjerenim.

## Potrebna korisnička potvrda

Ručni Notepad computer-use smoke test na stvarnom uređaju (van agent sandbox-a) — vidi "Potreban follow-up" iznad. Agent ne može simulirati/potvrditi stvarno tipkanje u Notepad iz ovog sandboxed okruženja.
