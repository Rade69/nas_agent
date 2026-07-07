# Agent Report — FAZA S-4: Fail-closed defaulti + global kill-switch

**Datum:** 2026-07-07
**Agent:** Claude Code
**Scope:** Sigurnosni backlog, FAZA S-4 iz `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md` (stavke S29, S30, S33).

---

## GitNexus impact
Indeks osvježen prije rada. Blast radius po inspekciji (poznat call graph): `RickyRealtimeClient` koristi samo `App.tsx` preko `clientRef`; preload/main dodaci su aditivni (novi kanal `app:kill-switch`, novi `globalShortcut`); `ConfirmationDialog` izmjena je lokalna. Nema širih zavisnosti.

## Šta je urađeno

### S29 — Fail-closed defaulti
- **Computer Mode OFF na startu:** potvrđeno da `electron/main.cjs` drži `let currentMode = "display"` inicijalizovano na svakom startu procesa, mijenja ga samo `set_mode` tool, i **nema učitavanja sa diska** → već fail-closed. Kill-switch dodatno forsira `currentMode="display"`.
- **Mic idle timeout (`src/lib/realtime.ts`):** novi `MIC_IDLE_TIMEOUT_MS = 5 min`. `bumpIdleTimer()` se resetuje na datachannel open, svaki server event i `sendText`; na isteku poziva `disconnect()` (gasi mic track, zatvara PC/DC) uz status + activity zapis. Timer se čisti u `disconnect()`.

### S33 — Global kill-switch (`electron/main.cjs`, `electron/preload.cjs`, `src/App.tsx`, `src/vite-env.d.ts`)
- `globalShortcut` fallback lanac (korisnikov izbor): **F10 → F11 → Ctrl+Alt+K**. `registerKillSwitch()` binduje prvi koji `register()` prihvati (vraća false ako je zauzet). Unregister u `before-quit`.
- Na okidanje `triggerKillSwitch()`: forsira `currentMode="display"` i šalje `app:kill-switch` glavnom prozoru.
- `preload.cjs`: novi allowlisted listener `onKillSwitch(handler)` na jednom imenovanom kanalu (bez generic passthrough — Gate 0 preload provjera).
- `App.tsx`: `useEffect` pretplata → na kill-switch `clientRef.disconnect()` + `setVoiceState("idle")` + `setMode("display")` + activity zapis. Radi i kad prozor nije fokusiran (globalni hotkey).
- `vite-env.d.ts`: tip `onKillSwitch` dodan u `window.ricky`.

### S30 — Confirm rate-limit (`src/components/ConfirmationDialog.tsx`)
- Novi `armed` state: false kad se dijalog pojavi, true nakon 250ms. Approve dugme `disabled` dok `!armed`. Spriječava automatizovan/slučajan/duplo-klik kroz high-risk potvrdu u trenutku renderovanja.

## Zašto
Fable #14/#8: kill-switch koji uvijek radi (i minimiziran) i fail-closed defaulti su ono što razdvaja upotrebljiv voice agent od demo-a. Mic koji ostane otvoren = stalni privacy rizik; confirm bez rate-limita = ranjiv na automatizovan klik.

## Šta NIJE dirano
- Python backend (nema izmjena).
- Confirmation poslovna logika (samo dodano vrijeme naoružanja dugmeta).
- Postojeći realtime tok osim dodatog idle timera (aditivno).

## Verifikacija
- `npm run typecheck` — čisto.
- `npm run check` (node --check svih electron cjs) — čisto.
- `npm run build` — čisto (samo pre-postojeći chunk-size warning).
- Backend nedirnut; Python testovi nerelevantni za ovu fazu.

## Rizici / ograničenja
- **Nije runtime-testirano** (hotkey + WebRTC traže stvarni Electron prozor). Potreban vizuelni smoke test:
  1. Pokrenuti glasovnu sesiju → pritisnuti hotkey (F10 ili prvi slobodan) → mic se gasi, indikator na "Spreman/idle".
  2. Ostaviti sesiju 5 min neaktivnu → auto-disconnect.
  3. Provjeriti da F10/F11 ne kolidiraju sa nečim bitnim kod korisnika (fallback lanac to ublažava, ali primarni F10 je izbor korisnika).
  4. Confirm dijalog: dugme kratko sivo pa aktivno.
- Kill-switch trenutno ne prekida *već-pokrenutu* backend tool egzekuciju (npr. dugotrajan computer-use tool) — gasi glas/mic i blokira nove akcije (Computer Mode OFF). Prekid in-flight backend akcije preko cancellation registry-ja je moguć follow-up.

## Potreban follow-up
- Vizuelni smoke test gore.
- Sljedeće po planu: **S-5 (supply chain)** — treba `uv`/`pip-tools` za Python hash-pinning; **S-6 (tajne: safeStorage/keyring)**.
- Opciono: povezati kill-switch sa backend cancellation registry-jem da prekine i in-flight tool.

## Potrebna korisnička potvrda
- Commit S-4? (Dira `electron/` + `src/` — Codex je završio svoj krug i stablo je bilo čisto; ovo su moje izmjene na vrhu.)
