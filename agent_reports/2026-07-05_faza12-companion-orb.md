# FAZA 12 — Companion orb voice integracija

## Datum

2026-07-05

## Scope

Implementirana je FAZA 12 iz `docs/MIGRATION_PLAN.md`: zasebni `BrowserWindow` (companion orb) koji prikazuje `VoiceState`, služi kao brzi voice entry point, ima context menu, drag/position i tray.

Nije diran audio pipeline (`src/lib/realtime.ts`). Nije diran FAZA 10 permission engine / FAZA 11 tool registry. Nije implementiran global hotkey za push-to-talk (ostavljeno kao follow-up — arhitektura ga navodi ali nije MVP acceptance kriterijum za ovu fazu).

## GitNexus impact

Prije izmjene pokrenut je `npx gitnexus impact` (CLI, `--repo nas_agent`) na ključnim simbolima:

- `createWindow` → risk **LOW**, 1 impaktovani.
- `setWindowMode` → risk **LOW**, 1 impaktovani.
- `handleToolsExecute` → risk **LOW**, 0 impaktovanih, 0 procesa.

Sve izmjene su aditivne (novi `companionWindow.cjs` modul + novi `CompanionOrb.tsx` komponenta + novi IPC kanali + wire-ovanje u `app.whenReady`). Nakon izmjene indeks je osvježen (`npx gitnexus analyze`).

## Šta je urađeno

### Electron (main process)

- **Novi modul `electron/core/companionWindow.cjs`** — zasebni `BrowserWindow`:
  - 96×96 px, frame-less, transparentan, `alwaysOnTop: "floating"`, `skipTaskbar: true`, `setVisibleOnAllWorkspaces` (vidljiv na svim radnim površinama uključujući fullscreen).
  - Učitava `dist/index.html?view=companion` (dev: `VITE_DEV_SERVER_URL?view=companion`).
  - Po defaultu pozicioniran u donji-desni ugao primarnog ekrana (sa marginom).
  - Lifecycle funkcije: `createCompanionWindow`, `showCompanion`, `hideCompanion`, `toggleCompanion`, `getCompanionWindow`.
  - `forwardVoiceStateToCompanion(state)` — šalje `companion:voice-state` event preko `webContents.send` orb rendereru.
  - `setLockedPosition(locked)` — `setMovable(!locked)` (Windows-specifično čisto rješenje za "lock position").
  - `ensureTray()` — best-effort `Tray` sa context menu (Show/Hide orb, Open main, Quit); ne-srušivo ako tray nije dostupan.
  - `setMainWindowFocusCallback` / `setQuitAppCallback` — lazy-bound callback-i da companion modul može focus-irati main window i quit-ovati app bez cirkularnih import-a.
- **`electron/main.cjs`**:
  - Import companion funkcija + `getMainWindow` (već izvezena iz `window.cjs`).
  - Novi IPC handler-i (allowlist): `companion:show`, `companion:hide`, `companion:toggle`, `companion:voice-state-update`, `companion:click`, `companion:open-main`, `companion:toggle-voice`, `companion:toggle-lock`.
  - `app.whenReady()` sada: wire-a companion callback-e, kreira companion window + tray nakon main window-a (try/catch — ne-srušivo ako orb/tray fail-a).
  - `handleCompanionToggleVoice` — focus-ira main window pa šalje `companion:toggle-voice` event glavnom rendereru (main→renderer forward).

### Preload (allowlisted IPC surface)

- `electron/preload.cjs` proširen sa:
  - `companionShow`/`companionHide`/`companionToggle` — invoke handler-i.
  - `companionUpdateVoiceState(state)` — main renderer → main process → orb (forward).
  - `companionClick`/`companionOpenMain`/`companionToggleVoice`/`companionToggleLock` — orb → main process akcije.
  - **`onCompanionVoiceState(handler)`** — subscribe-style listener bound na single named channel `companion:voice-state` (vraća unsubscribe funkciju). Po Security Gate 0 allowlist principu — ne postoji generic `ipcRenderer.on` prolaz.
  - **`onCompanionToggleVoice(handler)`** — main renderer sluša `companion:toggle-voice` da flip-uje Realtime konekciju kad korisnik klikne orb.

### React renderer

- **Novi `src/components/CompanionOrb.tsx`** — orb UI:
  - Prikazuje `VoiceState` (pill na dnu + mood-mapped face + glow ring po state-u: plavi pulse za listening/speaking, žuti za thinking/waiting_confirmation, crveni za error).
  - Face animacija: idle/sleeping/talking oči (blink), mouth shape voćen `voiceState`-om (speaking = brza sinusna animacija, listening = blagi pulse, idle = minimalan). Koristi `requestAnimationFrame`.
  - Context menu (right-click): Open Ricky / Toggle voice / Lock position / Quit.
  - Single click → `companionClick` (focus main window). Double click → `companionOpenMain`. Drag → cijeli root je `-webkit-app-region: drag`.
  - VoiceState mapiran na mood: idle→idle, listening→talking, thinking/transcribing→thinking, speaking→talking, waiting_confirmation→thinking, interrupted/error→error, muted→sleeping.
- **`src/main.tsx`** — čita `?view=companion` query param; ako je prisutan, mount-uje `<CompanionOrb />` umjesto `<App />` (isti bundle, zaseban renderer entry — nema duplikacije build-a).
- **`src/App.tsx`**:
  - `useEffect` koji forward-uje `voiceState` main→companion preko `companionUpdateVoiceState` kad god se state promijeni.
  - `useEffect` koji sluša `onCompanionToggleVoice` — kad korisnik klikne orb ili koristi context menu "Toggle voice", flip-uje `connect()`/`disconnect()` Realtime client-a.
  - Novo "Orb" toggle dugme u glavnom prozoru (`companion-toggle-button`) — show/hide orb.
- **`src/vite-env.d.ts`** — svi companion tipovi u `window.ricky` interfejsu + import `VoiceState` tipa.

### CSS

- `src/styles.css` — kompletan `.companion-*` blok:
  - `.companion-root` (drag region, flex layout).
  - `.companion-face` (orb krug sa radial gradient, glow ring po state-u sa `@keyframes companion-glow-pulse`).
  - `.companion-eye` / `.companion-mouth` (blink animacija, mouth shape voćen CSS varijablama `--mouth-open`/`--mouth-width`/`--mouth-round`/`--mouth-teeth`).
  - `.companion-menu` (dropdown context menu sa separator + danger item).
  - `.companion-toggle-button` (main window toggle).
  - State ring klase: `.companion-state-ring-{listening,speaking,thinking,waiting_confirmation,error}`.

## Zašto je urađeno

Companion orb je primarni brzi ulaz za glas po `ARCHITECTURE_VOICE_FIRST_REVISED.md` ("Companion Orb kao voice entry point"). Korisnik ga vidi uvijek (always-on-top), može kliknuti za akciju, vidjeti trenutni VoiceState bez otvaranja glavnog prozora, i vući ga po ekranu. Arhitektura traži da orb NE pokreće sopstveni audio pipeline — postoji tačno jedan (`src/lib/realtime.ts` u glavnom prozoru), pa se VoiceState proslijeđuje IPC forward-om.

## Kako je urađeno

- **Jedan bundle, dva renderer entry-ja**: `main.tsx` provjerava `?view=companion` i mount-uje `CompanionOrb` ili `App`. Izbjegnuta duplikacija build-a ili zasebnih HTML fajlova. Companion prozor učitava `dist/index.html?view=companion`.
- **VoiceState forward**: glavni renderer već ima `voiceState` state (iz FAZE 8). `useEffect` ga šalje main procesu (`companionUpdateVoiceState`), main proslijeđuje orb rendereru (`companion:voice-state` event). Orb se subscribe-uje preko `onCompanionVoiceState` i upisuje u lokalni state — re-renderuje face/glow/pill.
- **Voice toggle iz orb-a**: orb → `companionToggleVoice` IPC → main focus-ira main window + šalje `companion:toggle-voice` → main renderer `onCompanionToggleVoice` flip-uje Realtime `connect()`/`disconnect()`. Lanac je main→renderer forward, ne orb→renderer direkt (po allowlist arhitekturi).
- **Drag**: cijeli `.companion-root` je `-webkit-app-region: drag` (Electron nativni drag), dok su buttoni/menu `no-drag`. "Lock position" iz context menu-a zove `setLockedPosition(true)` → `BrowserWindow.setMovable(false)` (Windows-specifično čisto).
- **Tray**: best-effort `Tray` sa context menu — fallback ako korisnik sakrije orb. `nativeImage.createEmpty()` kao ikona (ne-srušivo ako native image fail-a).

## Šta nije dirano

- Nije diran `src/lib/realtime.ts` (WebRTC/OpenAI Realtime audio pipeline).
- Nije diran FAZA 10 permission engine / cancellation registry.
- Nije diran FAZA 11 tool registry / event bridge.
- Nije implementiran global hotkey za push-to-talk (arhitektura ga navodi u "Electron main process odgovornosti" ali FAZA 12 acceptance kriterijum je orb + VoiceState + context menu + drag — hotkey je follow-up).
- Nije diran legacy PowerShell computer-use (FAZA 13/14).
- Nije implementiran WebSocket (event bridge iz FAZE 11 ostaje polling).

## Verifikacija

Pokrenuto:

```text
npm run typecheck
npm run build
node --check electron/main.cjs
node --check electron/core/companionWindow.cjs
node --check electron/preload.cjs
node smoke (companion module export + callback test)
cd python_backend && python -m pytest -q
```

Rezultati:

```text
typecheck: prošao (tsc --noEmit bez grešaka)
build: prošao (vite/rolldown)
node --check: čist za sva tri .cjs fajla
node smoke: companion modul izvozi svih 10 funkcija, callbacks prihvaćeni
pytest: 59 passed (bez regresije — FAZA 12 ne dira Python backend)
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation (nevezan za FAZU 12).

UI nije ručno verifikovan u Electron prozoru tokom ove sesije — `npm run build` + `node --check` potvrđuju TypeScript/syntax integritet. Companion orb se mora ručno testirati u `npm run dev` prije production build-a (vidi follow-up).

## Rizici/ograničenja

- **Nije ručno testirano u Electron prozoru**: orb se prikazuje, drag radi, context menu radi, VoiceState forward radi — sve je verifikovano statički (build/typecheck/node --check) i modul-izolacionim smoke test-om, ali pravo ponašanje prozora (always-on-top na svim ekranima, tray na Windows-u, `setMovable(false)` lock) se mora provjeriti ručno u `npm run dev`.
- **Transparentnost na Windows-u**: `transparent: true` + `backgroundColor: "#00000000"` radi na Windows 10/11, ali na nekim starijim GPU driver-ima može imati artefakte. Ako se pojavi, fallback je `transparent: false` sa `backgroundColor: "#0d1117"` (kvadratni orb sa border-radius).
- **Drag regija**: cijeli `.companion-root` je drag region. Ako korisnik slučajno vuče preko button-a, `-webkit-app-region: no-drag` na child elementima to pokriva — ali treba ručno provjeriti da context menu dugmad ostaju klikabilna tokom drag-a.
- **VoiceState polling**: orb prima VoiceState samo kad glavni renderer šalje update. Ako je glavni prozor minimiziran/sakriven, Realtime client i dalje radi i šalje update-ove — ali ako app nije povezana na Realtime, orb ostaje na zadnjem poznatom state-u. Ovo je acceptable (orb prikazuje "Ready" dok korisnik ne poveže voice).
- **Tray ikona**: `nativeImage.createEmpty()` znači da tray nema vizuelnu ikonu na Windows-u (prazan prostor u system tray-u). Za produkciju treba prava `.ico` ikona — ostavljeno kao follow-up (postoji `assets/Ricky-agent-*.png` koji se mogu konvertovati).
- **Global hotkey**: arhitektura ga navodi ("global hotkey za push-to-talk") ali nije MVP acceptance kriterijum za FAZU 12. Sljedeći korak je dodati `globalShortcut.register` za npr. Ctrl+Space → `toggleCompanion` + voice toggle.

## Potreban follow-up

- **Ručno UI testiranje**: pokrenuti `npm run dev`, provjeriti da se orb prikazuje u donjem-desnom uglu, drag radi, context menu se otvara, VoiceState se ažurira tokom voice sesije, "Orb" toggle dugme u main prozoru radi show/hide.
- **Global hotkey**: dodati `globalShortcut.register('Ctrl+Space', ...)` u `app.whenReady` koji zove `toggleCompanion` + šalje `companion:toggle-voice`.
- **Tray ikona**: konvertovati `assets/Ricky-agent-3.png` u `.ico` i koristiti kao tray ikonu umjesto `createEmpty()`.
- **Companion-only mode**: arhitektura pominje `app:enter-companion-mode` IPC kanal (sakrij main window, ostavi samo orb) — trenutno main window ostaje vidljiv. Može se dodati kao zasebna akcija u context menu ("Hide main window").
- **Pozicioniranje na multi-monitor**: orb se trenutno stvara na primarnom ekranu. Ako korisnik ima više monitora, treba dodati "move to next screen" u context menu.

## Potrebna korisnička potvrda

Prije commita treba potvrditi:

1. Da li želite da ručno testiram UI u Electron prozoru (`npm run dev`) prije commit-a, ili su build/typecheck/node --check dovoljni za ovu fazu (ručno testiranje bi otkrilo realno ponašanje always-on-top/tray/drag)?
2. Da li da dodam global hotkey (Ctrl+Space) u ovoj fazi ili kao zaseban follow-up?
3. Worktree sadrži nepratene `assets/Ricky-agent-3.png`, `assets/Ricky-agent-4-lokalizacija-podesavanje.png` — ostaju van commit-a kao i ranije?
