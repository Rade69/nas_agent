# Agent report — Dictation Mode: "Doradi" i "..." meni

**Datum:** 2026-07-11
**Scope:** `python_backend/app/schemas/text.py`, `app/api/text.py`, `app/main.py`,
`python_backend/tests/test_text_rewrite.py`, `electron/services/pythonClient.cjs`,
`electron/ipc_handlers/text.cjs` (novo), `electron/main.cjs`, `electron/preload.cjs`,
`src/vite-env.d.ts`, `src/components/pixel/DictationScreen.tsx`,
`src/components/pixel/PixelMockupBoard.tsx`, `src/App.tsx`.

**GitNexus impact:** nema HIGH/CRITICAL upozorenja — novi endpoint/IPC kanal,
prosljeđivanje propova kroz postojeće leaf komponente. Indeks osvježen nakon
prethodnog commita (b918f22), nije ponovo pokretan prije ovog rada jer su
izmjene isključivo aditivne (novi fajlovi + novi propovi, bez izmjene
postojećih signatura osim proširenja).

## Šta je urađeno

1. **Backend** — novi `POST /text/rewrite` endpoint: plain text-in/text-out
   poziv, BEZ agent/tool loopa i BEZ conversation state. Reuse postojećeg
   `OpenAIModelClient.complete()`, nova dedicirana instanca
   `app.state.text_model_client` (namjerno odvojena od `agent_runtime`-a).
2. **Electron** — `pythonClient.rewriteText()`, `ipc_handlers/text.cjs`,
   `text:rewrite` IPC kanal u allowlist-u, `window.ricky.rewriteText` u
   preload-u (isti thin-passthrough obrazac kao `settings.cjs`).
3. **Renderer** — "Doradi" (Formalizuj / Skrati / Provjeri pravopis / Prevedi
   na engleski) sada stvarno poziva backend i zamjenjuje `dictationText`.
   "..." dugme dobilo je isti `.pixel-dropdown` CSS obrazac (čisto
   hover/focus-within, bez novog JS state-a za otvaranje) sa: Kopiraj tekst,
   Obriši sve (uz `window.confirm`), Undo, Preuzmi kao .txt.
4. **Undo** — single-level (`dictationUndoRef`), pokriva i rewrite i "Obriši
   sve" jer su to jedine dvije destruktivne akcije nad cijelim tekstom.

## Zašto ovako

- Istraga (Explore agent) potvrdila da ne postoji gotov sinhroni text-in/
  text-out put van glasovne Realtime WebRTC sesije — `sendText()` u
  `realtime.ts` ide kroz live data channel i po defaultu izaziva audio
  odgovor, a `POST /agent/message` je pun agent loop sa conversation-state i
  tool-calling (pogrešna semantika za "zamijeni cijeli tekst formalnijom
  verzijom"). Zato nov, namjerno tanak endpoint.
- `text_model_client` je zasebna instanca od `agent_runtime`-ovog internog
  model klijenta — nema sprege sa conversation-state/tool-executor, isti
  princip razdvajanja kao `user_settings_service` vs `settings`
  (agent_reports/2026-07-11_settings-panel-foundation.md).
- Model response prazan/None → fallback na originalni tekst (nikad ne briše
  korisnikov dictationText zbog prazanog odgovora modela).

## Šta nije dirano

- `sendText()` / Realtime voice put — nepromijenjen.
- `POST /agent/message` / agent runtime — nepromijenjen, samo referenca u
  odluci zašto NIJE korišten.
- Nema promjene u postojećim IPC kanalima, samo dodat nov (`text:rewrite`).

## Verifikacija

- `cd python_backend && python -m pytest -q` — **233 passed** (226 prije +
  7 novih: 3 pojedinačna + 4 parametrizovana test_all_operations_are_accepted).
- `node --check` na `pythonClient.cjs`, `ipc_handlers/text.cjs`, `main.cjs`,
  `preload.cjs` — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- Runtime NIJE testiran u ovom koraku — potreban korisnički test uživo
  (otvoriti Diktiranje, isprobati sve 4 Doradi akcije, Undo, Kopiraj, Obriši
  sve, Preuzmi kao .txt).

## Rizici / ograničenja

- Svaka "Doradi" akcija je pun HTTP round-trip do OpenAI Chat Completions
  (isti trošak/latencija kao i ostali `gpt-4o-mini` pozivi u ovom projektu) —
  nema streaming-a, korisnik čeka do odgovora (`busy` state to signalizira).
- Undo je samo jedan nivo — druga uzastopna "Doradi" akcija prepisuje undo
  snapshot, ne pravi historiju.
- "Obriši sve" koristi nativni `window.confirm()` (Electron ga podržava),
  ne projektov `ConfirmationDialog` sistem — namjerno, jer je taj sistem
  rezervisan za tool-execution rizik (backend confirmation tabela), ne za
  lokalne UI akcije bez trajnih posljedica van renderer memorije.

## Potreban follow-up

- Korisnički runtime test svih 8 novih akcija.
- `docs/MIGRATION_PLAN.md` tracker nije ažuriran — ovo je popravka
  neispravnog UI-ja unutar već završene Dictation Mode faze, ne nova
  numerisana faza.

## Potrebna korisnička potvrda

Runtime test prije commita.
