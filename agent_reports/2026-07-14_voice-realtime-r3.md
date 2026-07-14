# Voice Realtime R3 — Fail-safe tool lifecycle

**Datum:** 2026-07-14
**Agent:** pi + Codex review fix
**Scope:** R3 tool-call lifecycle — timeout, idempotency, active tracking, safe output prema `docs/VOICE_COMMUNICATION_R3_BRIEF_FOR_PI.md`
**Predloženi commit naslov:** `fix(voice): add tool call lifecycle with timeout, idempotency, and safe output (R3)`

## Prethodno stanje

R2 (Codex, 2026-07-14) je već obezbijedio:
- Kontrolisani reconnect/backoff, manual disconnect guard, outbound event queue
- 205 voice testova

Ali `executeFunctionCalls` nije imao zaštitu od:
- Vječno zaglavljenih tool poziva (timeout)
- Duplog izvršavanja istog `call_id` (idempotency)
- Zakašnjelih outputa nakon disconnect-a/nove generacije
- Exception-a koji prekidaju cijeli batch

## GitNexus impact

- `RickyRealtimeClient.executeFunctionCalls`: centralna metoda za tool lifecycle — potpuno prepisana sa R3 zaštitama
- `RickyRealtimeClient.returnToolOutput`: posredno kroz novi `_sendToolOutput` wrapper
- Novi simboli: `_runToolWithTimeout`, `_sendToolOutput`
- Nova polja: `activeToolCalls` (Map), `completedToolCallIds` (Set)
- `detect_changes(scope="all")`: CRITICAL — 6 praćenih fajlova u shared dirty tree-u, 25 promijenjenih simbola, 25 pogođenih procesa. Rizik dolazi iz centralnog `RickyRealtimeClient` realtime puta (`connect`, `disconnect`, `executeFunctionCalls`, `returnToolOutput`) plus nevezane lokalne promjene u `AGENTS.md`/`CLAUDE.md`/drugim fajlovima.
- Ciljani impact nakon Codex review fix-a:
  - `executeFunctionCalls`: LOW / partial (GitNexus ne vraća direktne upstream zavisnosti za novu indeksiranu varijantu simbola)
  - `connect`: CRITICAL — centralni entry point za realtime/reconnect tok; R3 promjena u njemu je namjerno minimalna (`activeToolCalls.clear()` + `completedToolCallIds.clear()`)
  - `disconnect`: LOW / partial; R3 promjena je cleanup mapa/seta
  - `returnToolOutput`: LOW; pogođen preko novog `_sendToolOutput` wrapper-a

## Šta je promijenjeno

### `src/lib/realtime.ts` (202 insertions, 68 deletions)

1. **Nova konstanta** — `DEFAULT_TOOL_TIMEOUT_MS = 30000`

2. **Nova polja**:
   - `activeToolCalls: Map<string, { name, startedAt, generation }>` — prati aktivne tool pozive
   - `completedToolCallIds: Set<string>` — pamti završene call_id za idempotency

3. **`connect()` / `disconnect()`** — čiste `activeToolCalls` i `completedToolCallIds`

4. **`executeFunctionCalls` prepisan** (R3):
   - **Idempotency guard** — prije svakog tool-a provjerava `completedToolCallIds.has(callId)` i `activeToolCalls.has(callId)`. Duplicate dobija kontrolisan `function_call_output` bez ponovnog izvršavanja.
   - **Active tracking** — `activeToolCalls.set(callId, ...)` prije `_runToolWithTimeout`, brisanje u `finally`
   - **Timeout wrapper** — `_runToolWithTimeout` koristi `Promise.race` između `window.ricky.executeTool` i internog timeout promise-a, uz obavezno `clearTimeout` u `finally`
   - **Safe failure** — svaka exception grana (catch) šalje `function_call_output` sa `ok: false`
   - **Stale output guard** — `_sendToolOutput` provjerava `generation === this.connectionGeneration && !this.manualDisconnectRequested` prije slanja
   - **Batch continuation** — `continue` umjesto `return` za pojedinačne failure-e

5. **`_runToolWithTimeout(callId, name, parsedArgs, generation)`** — `Promise.race` wrapper za tool execution sa timeout-om; timeout timer se čisti i kada tool završi uspješno, tako da nema zakašnjelog lažnog `"Alat se nije završio..."` eventa

6. **`_sendToolOutput(callId, result, generation)`** — šalje `returnToolOutput` samo ako je generation još važeća i nije manual disconnect; dodaje `callId` u `completedToolCallIds`

7. **Codex review fix** — `thumbnail_loading_prepare` je prebačen u isti protected lifecycle kao i glavni tool poziv. Ako loading prepare padne ili zaglavi, model ipak dobija kontrolisan failure output umjesto da voice loop ostane bez odgovora.

8. **Codex review fix** — active duplicate `call_id` šalje kontrolisan duplicate/active output, ali ne označava originalni poziv kao completed dok stvarni poziv ne završi; duplicate grane pokreću `response.create` da model može objasniti ishod korisniku.

### `src/lib/__tests__/realtimeClient.test.ts`

- `mockWindowRicky()` proširen sa `executeTool` mock-om
- `callExecuteFn()` helper za poziv privatnog `executeFunctionCalls` sa ispravnim `this` binding-om
- 11 novih R3 testova:
  1. **Active tracking** — tool se registruje kao aktivan prije izvršenja, čisti poslije
  2. **Timeout cleanup** — aktivni poziv se briše nakon što tool resolve-uje, a timeout timer se čisti
  3. **Stvarni timeout output** — zaglavljen tool vraća `TOOL_TIMEOUT`, activity event i briše active state
  4. **Batch continuation** — jedan tool throw ne prekida ostale
  5. **Thumbnail prepare failure** — pad `thumbnail_loading_prepare` vraća safe output
  6. **Duplicate completed call_id** — isti `call_id` ne izvršava tool drugi put i vraća duplicate output
  7. **Active duplicate call_id** — aktivni duplicate ne izvršava tool i ne označava original kao completed
  8. **Duplicate confirmation call_id** — `CONFIRMATION_REQUIRED` duplicate ne kreira drugu confirmation
  9. **Stale output poslije disconnect-a** — zakašnjeli tool output se ne šalje poslije ručnog disconnect-a
  10. **Disconnect clears active** — `disconnect()` briše sve aktivne pozive
  11. **Unknown tool u batch-u** — nepoznati tool ne sprječava izvršenje poznatih

Ukupno: **216 testova** (205 postojećih + 11 novih R3).

### `docs/MIGRATION_PLAN.md`

Ažuriran tracker — dodat R3 status u Backlog/Future Epics red.

## Zašto

- **Timeout**: Ako `window.ricky.executeTool` nikad ne resolve-uje (mrežni problem, backend hang), voice loop ostaje zaglavljen u `thinking/working` stanju. 30s deadline to sprječava.
- **Idempotency**: Ako isti `call_id` stigne dva puta (reconnect, model retry), modifying/destructive tool se ne smije izvršiti dva puta.
- **Safe output**: Svaki tool call mora dobiti kontrolisan `function_call_output` — success, known failure, timeout, duplicate, confirmation required. Model nikad ne smije ostati bez odgovora.
- **Stale output guard**: Ako se sesija promijeni dok tool još radi, zakašnjeli output ne smije otići u pogrešnu sesiju.
- **Batch continuation**: Jedan timeout/failure ne smije spriječiti da ostali toolovi u istom response-u dobiju svoj output.

## Šta nije urađeno (ostaje za R4)

- Detaljniji diagnostics panel
- Provider abstraction za jeftiniji/non-OpenAI voice mode
- Lokalni/jeftini fallback voice stack
- Transport/tool run timeline u UI-u
- Promjene u `electron/main.cjs`

## Verifikacija

```powershell
npm.cmd run test:voice   → 216/216 passed
npm.cmd run typecheck    → clean
npm.cmd run check        → clean
npm.cmd run build        → success (postojeći chunk-size warning, nevezan)
git diff --check         → bez whitespace grešaka
```

## Ručni smoke test checklist

- [ ] Normalan razgovor bez toolova
- [ ] Jedan read-only tool preko glasa
- [ ] Jedan modifying/confirmation tool preko glasa
- [ ] Confirmation required i dalje otvara dijalog
- [ ] Stop tokom aktivnog tool-a ne šalje zakašnjeli output u novu sesiju
- [ ] Reconnect tokom tool-a ne duplira modifying radnju
- [ ] Ako tool padne, agent kaže korisniku smisleno šta se desilo

## Preostali rizik

- Timeout ne prekida stvarni backend posao ako je on već pokrenut i nastavi da radi poslije frontend deadline-a; R3 sprječava hang voice loop-a, ali prava server-side cancelacija ostaje posebna tema za kasnije faze.
- `executeFunctionCalls` je centralna metoda — svaka izmjena ovdje ima širok blast radius
- Testovi sada pokrivaju direktan timeout scenario, safe failure, batch continuation i cleanup, ali ručni smoke test je i dalje potreban sa stvarnim Realtime transportom
