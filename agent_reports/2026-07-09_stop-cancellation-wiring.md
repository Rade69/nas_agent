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
