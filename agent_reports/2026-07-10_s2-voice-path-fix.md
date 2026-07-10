# Agent report — S-2 prompt-injection escalation: voice-path fix

**Datum:** 2026-07-10
**Izvršilac:** Claude Code (security-critical, ne pi — dira Electron shared context building).
**Povod:** nalaz tokom provjere FABLE-5 kritike `MULTI_AGENT_SECURITY_ARCHITECTURE_VISUAL.html` mape.

## Scope

S-2 prompt-injection eskalacija (`permission_engine.py` `check_permission`,
`external_content_seen` grana) je bila **ispravno dizajnirana, ožičena i
testirana (8 red-team testova)**, ali **samo za `POST /agent/message`
autonomous runtime put** (`app/agent/runtime.py`). Glasovni Realtime pipeline —
stvarni primarni interakcijski put aplikacije — nikad nije postavljao
`external_content_seen`, pa eskalacija nije mogla trigerovati za glasom
pokrenute tool pozive.

## GitNexus impact

Simboli dirani: `handleToolsExecute` (main.cjs, samo `context` blok proširen),
`RickyRealtimeClient.executeFunctionCalls`/`connect`/`disconnect` (novo polje +
3 mjesta), `toolSpecs` katalog (3 unosa dobila novo polje), `RickyToolSpec`/
`RickyToolCall` tipovi (aditivno proširenje, ne mijenja postojeća polja).
Nema izmjene potpisa postojećih funkcija, nema izmjene Python koda
(`permission_engine.py` već ispravno čita `external_content_seen` — samo
JS strana ga sada stvarno šalje). Nizak-srednji rizik — dodaje novi podatak u
postojeći tok, ne mijenja postojeću logiku grananja.

## Šta je urađeno (dokaz, sloj po sloj)

1. **`electron/core/realtimeToolSpecs.cjs`** — dodano `reads_external_content: true`
   na 3 unosa koja odgovaraju Python `ToolDefinition.reads_external_content=True`
   skupu koji je uopšte dostupan glasom: `web_search`, `screen_snapshot`,
   `ui_inspect`. (Python ima još 2 — `computer_find_elements`,
   `computer_get_element_text` — ali ta dva nisu u ovom katalogu uopšte, dakle
   nisu ni ponuđena modelu glasom; poznat, odvojen gap iz trackera "FAZA 14
   element toolovi nisu glasom pozivljivi", van scope-a ovog fixa.)
2. **`electron/ipc_handlers/realtime.cjs`** — `tools.map()` koji filtrira polja
   prije slanja OpenAI Realtime API-ju sada filtrira i novo `reads_external_content`
   (isti obrazac kao postojeći `risk` filter — sprječava curenje internog
   metadata polja u function-calling šemu koju vidi model).
3. **`electron/main.cjs` `handleToolsExecute`** — `context` blok (koji se šalje
   `POST /tools/execute`) sad prosljeđuje `external_content_seen` iz
   `toolCall.context`, isti obrazac kao postojeći `confirmation_id` prosljeđivanje.
4. **`src/vite-env.d.ts`** — `RickyToolSpec.reads_external_content?: boolean`,
   `RickyToolCall.context?: { confirmation_id?, external_content_seen?, computer_mode? }`
   (formalizuje tip koji je `App.tsx` confirmation-retry put već koristio kroz
   `as`-cast — sad tipski ispravno za oba pozivaoca).
5. **`src/lib/realtime.ts` (`RickyRealtimeClient`)** — novo privatno polje
   `externalContentSeen`, reset u `connect()` i `disconnect()`, postavlja se na
   `true` u `executeFunctionCalls()` nakon uspješnog poziva toola sa
   `reads_external_content=true`, i prosljeđuje se kao `context.external_content_seen`
   u SVAKOM `executeTool()` pozivu (vrijednost PRIJE tog poziva, dakle odražava
   šta se desilo u prethodnim pozivima iste sesije).

## Dizajn odluka — svjesno odstupanje od Python granice (transparentno, ne tiho)

`runtime.py` resetuje `external_content_seen` **po user-poruci** (svaki
`handle_message()` poziv počinje sa `False`, traje kroz do 4 tool-iteracije te
iste poruke, pa se odbacuje). Glasovni Realtime tok nema tako čistu granicu
per-event (jedan `response.done` ne mapira 1:1 na "jedna user poruka" — model
može poslati više rundi za isti logički zahtjev). Odabrao sam **reset po
glasovnoj sesiji** (`connect()`/`disconnect()`), što je **konzervativnije**
(sigurnije, širi prozor eskalacije) od Python varijante, ne manje strogo —
jednom zaprljano, ostaje eskalirano do kraja tog poziva (do 5 min idle timeout
ili Stop). Cijena: nešto više friction-a (svaka acting radnja nakon BILO
kojeg ranijeg web-search/screenshot u istom pozivu traži potvrdu), ali to je
ispravan kompromis za sigurnosni mehanizam — širi lažni-pozitiv prostor je
prihvatljiviji od uskog lažni-negativ prostora.

## Šta NIJE dirano (namjerno)

- `App.tsx` confirmation-bridge retry put (linija ~337) — analizirano i
  potvrđeno da NE treba ovaj flag da bi radio ispravno: retry već šalje pravi
  `confirmation_id` koji zadovoljava `check_permission` nezavisno od
  eskalacije (eskalacija određuje SAMO da li je potvrda potrebna, ne
  validira već-dobijenu potvrdu). Namjerno neizmijenjeno, ne propust.
- `permission_engine.py`, `runtime.py`, `prompt_builder.py` — Python strana je
  već bila ispravna, ovo je isključivo JS-strana rupa u prosljeđivanju.
- `computer_find_elements`/`computer_get_element_text` u `realtimeToolSpecs.cjs`
  — odvojen, već zabilježen gap (FAZA 14 nije glasom pozivljiva), ne dio ovog fixa.

## Verifikacija

- `node --check` na sva tri izmijenjena `.cjs` fajla — čisto.
- `npm run typecheck` — čisto.
- `npm run build` — čisto (samo pre-postojeći 500kB chunk warning).
- `cd python_backend && python -m pytest -q` — 222 passed (nisam dirao Python
  kod; ovo je sanity-check da paralelni pi rad na istoj test suiti nije
  pokvaren mojim JS izmjenama — nepovezano, ali potvrđeno zeleno).

## Rizici/ograničenja

- Nema automatskog testa za sam JS/Electron sloj (main.cjs/realtime.ts nemaju
  test infrastrukturu) — oslanjam se na typecheck + build + ručni runtime smoke.
- Runtime smoke NIJE još urađen (traži: uključi računarski mod, izgovori
  zahtjev za web pretragu, pa odmah traži akcijsku radnju — očekivano: sad
  treba iskočiti potvrda koja ranije nije iskakala).

## Potreban follow-up

- Runtime smoke prije commita (korisnik).
- `docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md` S8 red ažuriran (vidi commit) da
  jasno kaže "oba puta" umjesto da ostavi utisak univerzalnog pokrića.
- Kad FAZA 14 element toolovi postanu glasom pozivljivi, dodati im
  `reads_external_content: true` u `realtimeToolSpecs.cjs` u istom potezu.

## Potrebna korisnička potvrda

Ručni runtime smoke prije commita (glasovni put bez automatskih testova).
