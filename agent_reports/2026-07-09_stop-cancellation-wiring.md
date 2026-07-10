# Agent report — Stop dugme → FAZA 10 cancellation (wiring)

**Datum:** 2026-07-09
**Izvršilac:** Claude Code (security-adjacent — cancellation sloj).
**Tip:** Zatvaranje otvorenog gap-a (ne nova faza). Adresira "Otvoreno" napomenu iz UI Redesign / Confirmation Bridge redova u `docs/MIGRATION_PLAN.md`.

## Scope

Ožičen Stop dugme na backend cancellation sloj. Do sada je `handleStop()` samo
prekidao voice/mik sesiju (`clientRef.disconnect()`), a backend tool u letu je
nastavljao — FAZA 10 `CancellationRegistry` je postojao ali ga UI nikad nije zvao.

Odabran pristup **"cancel-all"** (Stop = "zaustavi sve u letu"): korisnik ne bira
`execution_id`, pa se svi ne-terminalni recordi flaguju odjednom. Time se izbjegava
promjena tool-execute contracta (sinhroni tok znači renderer ionako ne zna
in-flight `execution_id` po pojedinačnom toolu do kraja izvršenja).

## GitNexus impact

Dodate su NOVE funkcije/kanali (nizak rizik — bez izmjene potpisa postojećih):
`CancellationRegistry.request_cancel_all()`, endpoint `POST /tools/executions/cancel-all`,
`cancelAllExecutions` (pythonClient), IPC kanal `tools:cancel-all`. Izmijenjen je samo
`handleStop()` (dodat poziv, potpis nepromijenjen). Nema HIGH/CRITICAL.

## Šta je urađeno (sloj po sloj)

1. **Backend** `app/agent/cancellation.py`: `request_cancel_all()` — flaguje sve
   ne-terminalne recorde, vraća flagovane; terminalne (`completed`/`failed`/…) ostavlja.
2. **Backend** `app/api/tools.py`: `POST /tools/executions/cancel-all` → `{ok, cancelled[], count}`.
   Definisan PRIJE `/tools/executions/{execution_id}/cancel` (različit path shape, nema routing konflikta).
3. **Electron** `services/pythonClient.cjs`: `cancelAllExecutions()` (POST, isti auth obrazac kao ostali pozivi) + export.
4. **Electron** `ipc_handlers/app.cjs`: `handleCancelAllExecutions()` → `cancelAllExecutions()` + export.
5. **Electron** `main.cjs`: import handlera + kanal `"tools:cancel-all"` u `registerIpcHandlers({...})`.
6. **Electron** `preload.cjs`: `window.ricky.cancelAllExecutions()` (isti pattern kao `executeTool`).
7. **Renderer** `src/vite-env.d.ts`: tip za `cancelAllExecutions`.
8. **Renderer** `src/App.tsx` `handleStop()`: uz `disconnect()` sad i
   `void window.ricky.cancelAllExecutions().catch(...)` — best-effort, ne blokira teardown glasa.

## Zašto ovako

- **cancel-all umjesto per-id:** semantički tačno za Stop dugme; izbjegava izmjenu
  tool-execute contracta (client-generisan `execution_id` bi bio veći zahvat — ostavljen
  kao mogući kasniji upgrade za precizan per-tool cancel).
- **Best-effort na UI strani:** teardown glasa (`disconnect`) mora biti trenutan;
  backend cancel je async i ne smije ga blokirati. Ako backend poziv padne, glas je
  već zaustavljen (glavna korist Stop-a).
- **Cancel je "flag", ne "kill":** whether tool stvarno stane zavisi od njegovih
  cancellation checkpoint-a (FAZA 10 handshake), isto kao postojeći per-id cancel.

## Šta nije dirano

- Tool-execute contract (`ToolExecutionRequest`/`Response`) — nepromijenjen.
- Postojeći `POST /tools/executions/{id}/cancel` — netaknut (cancel-all je dodatak).
- Kill-switch (Ctrl+Alt+K) — zaseban, netaknut.
- Nijedan tool handler, permission engine, `currentMode`.

## Verifikacija

- **pytest:** 210 → **214 passed** (+3 unit za `request_cancel_all`: flaguje sve /
  preskače terminalne / prazan registry; +1 endpoint smoke `POST /tools/executions/cancel-all`).
- **node --check:** `main.cjs`, `ipc_handlers/app.cjs`, `services/pythonClient.cjs`, `preload.cjs` — svi parsiraju.
- **npm run typecheck:** čist (novi `window.ricky.cancelAllExecutions` tip prolazi).
- **npm run build:** ✓ (samo pre-postojeći 500kB chunk warning).
- **Runtime smoke:** NIJE urađen (traži pokrenut app + glas). Preporuka: pokrenuti app,
  pokrenuti neku tool akciju pa pritisnuti Stop — potvrditi da backend primi cancel-all
  (nema greške u konzoli, glas prekinut).

## Rizici / ograničenja

- cancel-all je grub (otkazuje SVE u letu) — tačno za Stop, ali ne nudi per-tool izbor.
- Za kratke toolove cancel stigne poslije završetka (bez efekta) — očekivano; korisno
  za dugotrajne (computer-use sekvence).

## Potreban follow-up

- Runtime smoke (korisnik) prije commita.
- Opciono kasnije: client-generisan `execution_id` za precizan per-tool cancel + izlaganje
  FAZA 14 element toolova glasu (zasebna otvorena stavka iz trackera).

## Potrebna korisnička potvrda

- Ručni runtime smoke Stop dugmeta prije commita (UI put bez automatskih testova).

---

## Dopuna (isti dan) — Stop dugme na companion orbu

**Povod:** u Računarskom modu glavni prozor je sklonjen, orb je jedina vidljiva
površina, a orb nije imao vidljivo Stop dugme — samo nevidljivi Ctrl+Alt+K hotkey.
Korisnik ne vidi šta se dešava kad okine hotkey.

**Uočeni dodatni gap:** `runKillSwitch()` (Escape / Ctrl+Alt+K / IPC kill-switch)
je prekidao glas ali **NIJE** zvao cancel-all — isti gap kao stari Stop dugme, samo
na kill-switch putu. Popravljeno usput.

**Izmjene:**
1. `src/components/CompanionOrb.tsx`: vidljivo, uvijek-prisutno **Stop** dugme (crveno,
   `■ Stop`) → `window.ricky.companionStop?.()`.
2. `electron/preload.cjs`: `companionStop: () => ipcRenderer.invoke("companion:stop")`.
3. `electron/main.cjs`: kanal `"companion:stop": triggerKillSwitch` — **reuse** postojeće
   kill-switch orkestracije (forsira display mode + šalje `app:kill-switch` glavnom
   prozoru). Orb Stop = isto što i Ctrl+Alt+K, ali vidljivo. Tvrdi stop (izlazi iz
   Računarskog moda), za razliku od glavnog Stop dugmeta (meki — ostaje u modu).
4. `src/App.tsx` `runKillSwitch()`: dodat `cancelAllExecutions()` — sada SVE kill-switch
   rute (Escape, hotkey, orb) otkazuju i backend toolove, ne samo glas.
5. `src/vite-env.d.ts`: tip `companionStop`. `src/styles/07-companion-orb.css`: stil dugmeta.

**Dizajn:** orb Stop → `companion:stop` (IPC) → `triggerKillSwitch` (main) →
`app:kill-switch` → `runKillSwitch` (glavni prozor: voice teardown + cancel-all).
Jedna implementacija stop-a (`runKillSwitch`), tri ulaza (Escape/hotkey/orb).

**Verifikacija:** node --check (main+preload), typecheck, build — čisto. Bez backend
izmjene (reuse `triggerKillSwitch` + `cancel-all`), pa pytest nepromijenjen (214).

**Runtime smoke (korisnik):** ući u Računarski mod → potvrditi da je Stop vidljiv na
orbu → kliknuti → glas i radnje stanu, izlazak iz Računarskog moda.

---

## Dopuna 2 (isti dan) — raspodjela Stop-a, drag, native meni, mic-toggle fix, ring unifikacija

**Povod:** korisnik je ispravio pogrešnu pretpostavku — postoje DVA različita orba
(veliki `MiniComputerWindow` u računarskom modu vs. mali plutajući `CompanionOrb`),
i tražio je da Stop bude SAMO na malom, uz auto-pojavljivanje u računarskom modu.
Dalje testiranje malog orba otkrilo je tri odvojena, stvarna bug-a.

### Odluka o rasporedu (korisnikov izbor)
- **Veliki orb:** samo "Vrati" — Stop uklonjen.
- **Mali orb (companion):** nosi Stop, **auto-show** kad `set_mode` pređe u
  `computer` (main.cjs, jedinstvena tačka — pokriva i UI i agent-inicirani prelaz),
  **auto-hide** pri povratku u `display`.

### Bug 1 — mali orb se nije mogao pomjerati
Cijeli `.companion-root *` je bio markiran `-webkit-app-region: no-drag`, pa orb
nije imao gdje da se uhvati za drag. Popravljeno: orb (`.companion-orb-button`)
je sad sam drag handle (`-webkit-app-region: drag`), a Stop dugme je eksplicitno
`no-drag` da ostane klikabilno preko draggable roditelja.

### Bug 2 — desni-klik meni se odsijecao
Stari HTML meni (min-width 160px) nije stao u 96px širok orb prozor. Zamijenjen
**native Electron `Menu.popup`** (`showOrbContextMenu` u `companionWindow.cjs`),
koji nije ograničen veličinom prozora. Sadrži iste radnje kao stari meni (Otvori
Ricky / Uključi-isključi glas / Zaključaj poziciju kao checkbox / Zatvori Ricky).
**Nuspojava:** drag-region ne prima lijevi klik, pa su stari lijevi-klik/dupli-klik
gestovi (brzi fokus / otvori glavni) uklonjeni s orba — "otvori glavni prozor" sad
ide isključivo kroz meni ("Otvori Ricky").

### Bug 3 — Stop dugme odsječeno
Companion prozor (96×114, `ORB_SIZE=96`) nije imao mjesta za orb + pill + novo
Stop dugme. Povećan na **144×160** (`ORB_WIN_W`/`ORB_WIN_H` u `companionWindow.cjs`).

### Bug 4 — "Uključi/isključi glas" iz orb menija nikad nije radio
**Pravi uzrok** onoga što je korisnik opisao kao "mikrofon se ne uključi svaki
put": `companion:toggle-voice` IPC kanal je od FAZA 12 slao event glavnom prozoru,
ali `App.tsx` ga NIKAD nije slušao (`onCompanionToggleVoice` je postojao u
`preload.cjs`/`vite-env.d.ts`, ali se nigdje nije pozivao u `src/`) — potvrđeno
grep-om i GitNexus-om (0 poziva u src/). Klik iz orb menija je bio 0%-uspješan,
ne "povremeno". Popravljeno: `useEffect` u `App.tsx` sad subscribe-uje
`onCompanionToggleVoice` i poziva istu `isConnected ? disconnect() : connect()`
logiku kao pravo mikrofon dugme. Realno mrežno kašnjenje (getUserMedia + token +
WebRTC SDP razmjena sa OpenAI-jem) ostaje — to je očekivano, ne bug.

### Vizuelna unifikacija — prstenovi malog orba
Korisnik je primijetio da mali orb izgleda drugačije od velikog (statična slika
vs. animirani triple-ring). Otkriveno: `RickyOrb` komponenta već ima gotovu
`size="floating"` varijantu (84px, hover scale) dizajniranu baš za ovaj slučaj,
ali nikad povezanu s `CompanionOrb.tsx` (koji je koristio statični `orbMini.png`).
Zamijenjeno `<img>` sa `<RickyOrb voiceState={voiceState} size="floating" />` —
mali orb sad ima iste animirane prstenove i reaguje na stvarni voice state (a ne
samo na statičnu sliku). Očišćen mrtav `.companion-orb-img` CSS (2 pravila +
referenca u reduced-motion bloku, redundantna sa `.companion-root *`).

### GitNexus impact
`RickyOrb` — dodat nov pozivalac (`CompanionOrb`), sama komponenta nedirana;
postojeći pozivalac (`IdleScreen`) neizmijenjen. Nizak rizik, aditivna izmjena.

### Fajlovi dirani (dopuna 2)
- `electron/core/companionWindow.cjs` — `showOrbContextMenu`, `setToggleVoiceCallback`,
  prozor 144×160, export izmjene.
- `electron/main.cjs` — `companion:menu` kanal, toggle-voice callback wiring,
  `set_mode` auto-show/hide.
- `electron/preload.cjs` — `companionMenu`.
- `src/App.tsx` — `onCompanionToggleVoice` subscribe, `MiniComputerWindow` bez
  `onStop` prop-a.
- `src/components/CompanionOrb.tsx` — prepisan: `RickyOrb` umjesto `<img>`, ukinut
  HTML meni/lijevi-klik/dupli-klik, drag na orbu, Stop dugme.
- `src/components/pixel/MiniComputerWindow.tsx` — Stop uklonjen (vraćen na
  Vrati-only).
- `src/styles/07-companion-orb.css` — drag CSS, mrtav `.companion-orb-img` uklonjen.
- `src/vite-env.d.ts` — `companionMenu` tip.
- `docs/ORB_PRESENCE_SPEC.md` — novi, matrica načina rada orba (nacrt spec).

### Verifikacija (dopuna 2)
`node --check` (main.cjs, companionWindow.cjs, preload.cjs) čist; `npm run
typecheck` čist; `npm run build` čist. **Korisnik potvrdio runtime smoke: sve
radi kako treba** (drag, native meni bez odsijecanja, Stop vidljiv cijeli,
mic-toggle iz menija radi, prstenovi ujednačeni).

### Potreban follow-up
- `docs/ORB_PRESENCE_SPEC.md` ima 4 otvorene odluke za korisnika (mali orb na
  restore prozora, brzi-diktat hotkey, push-to-talk vs toggle, focus mod okidač)
  — sljedeći koraci van scope-a ove sesije.
- Meni napisan samo na srpskom (Otvori Ricky / Uključi-isključi glas / Zaključaj
  poziciju / Zatvori Ricky) — stari HTML meni je bio na engleskom; svjesna
  odluka za konzistentnost sa ostatkom UI-ja, nije bug.
