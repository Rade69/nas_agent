# Voice Communication Reliability — R3 brief za Pi agenta

**Datum:** 2026-07-14
**Namjena:** implementacioni brief za Pi agenta
**Status ulaza:** R0, R1 i R2 su završeni i komitovani. Glasovna komunikacija radi; reconnect/backoff radi; network/DNS greške su mapirane u korisničku poruku.

## Kratki cilj

R3 treba da učini **tool-call lifecycle** bezbjednim i predvidljivim tokom voice sesije.

R3 obim:

1. per-tool timeout,
2. tracking aktivnih tool call-ova,
3. idempotency po `call_id`,
4. kontrolisan `function_call_output` za timeout/failure,
5. zaštita od duplog izvršavanja istog tool poziva,
6. testovi za zaglavljene, duplirane i zakašnjele tool pozive,
7. update `docs/MIGRATION_PLAN.md` i novi `agent_reports/YYYY-MM-DD_voice-realtime-r3.md`.

Ovo nije novi provider sistem i nije veliki refaktor tool registry-ja.

## Kako se Pi mora ponašati tokom implementacije

Pi mora raditi usko i konzervativno.

- Ne uvoditi novi LLM/STT/TTS provider.
- Ne mijenjati OpenAI Realtime session payload.
- Ne mijenjati `electron/main.cjs`.
- Ne refaktorisati cijeli tool system.
- Ne mijenjati permission/confirmation engine osim ako test direktno pokaže da R3 promjena lomi postojeći confirmation tok.
- Ne mijenjati backend tool implementacije osim ako je baš potrebno za testabilnost.
- Ne uvoditi opšti shell execution tool.
- Ne duplirati izvršenje modifying/dangerous toolova.
- Ne gutati tool greške tiho — model mora dobiti kontrolisan output.
- Ne commitovati `.env`, logove, lokalne baze, `node_modules`, `dist`, niti `nul`.

Prije izmjena Pi mora uraditi:

```bash
git status --short
git log -5 --oneline
```

Zatim pročitati:

```text
docs/MIGRATION_PLAN.md
docs/VOICE_COMMUNICATION_R1_BRIEF_FOR_PI.md
docs/VOICE_COMMUNICATION_R2_BRIEF_FOR_PI.md
agent_reports/2026-07-14_voice-realtime-r1.md
agent_reports/2026-07-14_voice-realtime-r2.md
```

Ako neki dokument ne postoji u lokalnom tree-u, nastaviti bez panike, ali zapisati u R3 report.

## Trenutno poznato stanje poslije R2

R2 je već riješio:

- kontrolisani reconnect/backoff,
- razlikovanje manualnog Stop/Disconnect od transport prekida,
- outbound event queue,
- reconnect status poruke,
- network/DNS error klasifikaciju,
- 205 voice testova.

R3 ne smije pokvariti ove garancije.

## Primarni fajlovi

Očekivani glavni fajlovi:

- `src/lib/realtime.ts`
- `src/lib/__tests__/realtimeClient.test.ts`
- eventualno mali helper u `src/lib/` ako se pokaže da `realtime.ts` postaje prevelik
- `docs/MIGRATION_PLAN.md`
- `agent_reports/YYYY-MM-DD_voice-realtime-r3.md`

Ne dirati:

- `electron/main.cjs`
- OpenAI session payload u `electron/ipc_handlers/realtime.cjs`
- Python backend tool implementacije, osim ako je testabilnost stvarno blokirana
- permission/confirmation sistem bez direktnog razloga

## Problem koji R3 rješava

Realtime model može poslati `function_call`. Trenutni voice client izvršava toolove i vraća `function_call_output`.

Rizici:

- tool može visiti zauvijek,
- tool može pasti i ostaviti model bez odgovora,
- isti `call_id` može stići ponovo,
- reconnect/queue može dovesti do zakašnjelog output-a,
- modifying tool se može izvršiti dvaput ako nema idempotency guard-a,
- confirmation flow može ostati u čudnom stanju ako timeout nije jasno vraćen modelu.

R3 cilj: model uvijek mora dobiti kontrolisan ishod za svaki tool call — success, confirmation required, known failure, timeout, duplicate ignored — ali bez duplog opasnog izvršavanja.

## R3 funkcionalni zahtjevi

### 1. Active tool call tracking

Dodati interni tracking aktivnih poziva.

Preporučeni oblik:

```ts
type ActiveToolCall = {
  callId: string;
  name: string;
  startedAt: number;
  generation: number;
  status: "running" | "completed" | "timeout" | "failed";
};
```

Može biti:

```ts
private activeToolCalls = new Map<string, ActiveToolCall>();
private completedToolCalls = new Set<string>();
```

ili sličan minimalan oblik.

Pravila:

- prije izvršenja tool-a upisati `call_id` u active map;
- nakon uspjeha/failure/timeout očistiti iz active map;
- completed `call_id` zapamtiti dovoljno dugo da duplicate ne izvrši tool ponovo;
- na manual disconnect očistiti active pozive pažljivo — ne slati zakašnjele outpute u staru sesiju;
- stale generation guard mora i dalje važiti.

Testovi:

- active poziv se doda prije `window.ricky.executeTool`;
- active poziv se ukloni nakon uspjeha;
- active poziv se ukloni nakon failure-a;
- stale generation ne vraća output u novu sesiju.

### 2. Per-tool timeout

Problem:

Ako `window.ricky.executeTool()` nikad ne resolve-uje, voice loop ostaje zaglavljen.

Preporuka:

```text
DEFAULT_TOOL_TIMEOUT_MS = 30000
```

Ako želiš finije:

- read-only/simple toolovi: 20-30s,
- image/thumbnail toolovi: duže, npr. 120s,
- confirmation wait nije isti kao tool timeout.

Za R3 minimalno je prihvatljivo:

- jedna default vrijednost,
- eventualni izuzetak za thumbnail/image ako postojeći testovi pokažu potrebu.

Očekivano ponašanje:

- ako tool timeout-uje, poslati modelu `function_call_output`:

```json
{
  "ok": false,
  "error": "Tool timeout",
  "errorCode": "TOOL_TIMEOUT",
  "message": "Alat se nije završio na vrijeme."
}
```

- status/activity korisniku:

```text
Alat se nije završio na vrijeme: <tool_name>
```

Testovi:

- never-resolving `executeTool` dobija timeout output;
- nakon timeout-a `toolRunning` se vraća u safe stanje;
- model dobija `response.create` ako treba da objasni failure;
- nema vječnog `thinking/working` stanja.

### 3. Idempotency po `call_id`

Problem:

Ako isti `function_call.call_id` dođe dva puta, modifying tool se ne smije izvršiti dva puta.

Pravila:

- ako je `call_id` već active:
  - ne pokretati drugi `executeTool`;
  - vratiti ili ignorisati kontrolisano, zavisno od sigurnijeg toka;
- ako je `call_id` već completed:
  - ne izvršavati tool ponovo;
  - po mogućnosti vratiti cached/safe output ili duplicate message.

Minimalno R3 ponašanje:

```json
{
  "ok": false,
  "duplicate": true,
  "message": "Ovaj tool poziv je već obrađen."
}
```

Za modifying toolove ovo je posebno važno.

Testovi:

- isti `call_id` dva puta ne poziva `window.ricky.executeTool` dva puta;
- duplicate dobija kontrolisan `function_call_output`;
- duplicate ne pokreće confirmation dva puta.

### 4. Safe failure output

Problem:

Ako `executeTool` baci exception, model ne smije ostati bez `function_call_output`.

Očekivano:

- svaka exception grana mora vratiti `function_call_output` sa `ok:false`;
- poruka se sanitizuje;
- ne vraćati stack trace, token, path sa tajnama ili cijeli raw exception ako je predug/osjetljiv.

Primjer:

```json
{
  "ok": false,
  "error": "Tool execution failed",
  "message": "Alat nije uspio: <tool_name>"
}
```

Testovi:

- `executeTool` throw → vraća `function_call_output`;
- UI/activity dobija jasnu grešku;
- `toolRunning` se resetuje;
- `response.create` se šalje ako je DataChannel open ili queue ako nije.

### 5. Confirmation flow ne smije puknuti

Postojeći confirmation bridge radi:

- backend vrati `CONFIRMATION_REQUIRED`,
- client kreira confirmation,
- model dobija output da čeka potvrdu.

R3 ne smije ovo pokvariti.

Posebna pravila:

- `CONFIRMATION_REQUIRED` nije tool failure;
- ne tretirati čekanje potvrde kao timeout tog istog tool poziva nakon što je backend već vratio confirmation required;
- duplicate confirmation za isti `call_id` ne smije kreirati više potvrda;
- retry nakon korisničke potvrde treba ostati postojeći App-level tok, ne širiti R3 bez potrebe.

Testovi:

- `CONFIRMATION_REQUIRED` i dalje kreira jednu confirmation;
- duplicate `call_id` ne kreira drugu confirmation;
- model dobija `waiting_confirmation: true`.

### 6. Generation/stale protection za tool output

R1/R2 već imaju `generation` guard. R3 ga mora proširiti na tool lifecycle.

Pravila:

- ako se sesija promijeni dok tool još radi, zakašnjeli output ne smije otići u novu sesiju;
- ako je korisnik ručno disconnectovao, ne slati tool output;
- ako reconnect promijeni DataChannel, output mora ići samo ako pripada važećoj sesiji ili queue pravilima koja su namjerno dozvoljena.

Minimalno:

- prije `returnToolOutput` provjeriti generation/manual disconnect;
- za stale output upisati activity/status samo ako je korisno, ali ne slati u model pogrešne sesije.

Testovi:

- tool resolve nakon disconnect-a ne šalje output;
- tool resolve nakon nove generacije ne šalje output u novu sesiju;
- active map se očisti.

### 7. Tool timeout ne smije zaustaviti cijeli batch

Ako response ima više function_call itema, jedan timeout/failure ne smije spriječiti da ostali pozivi dobiju output.

Pravila:

- za svaki item vratiti neki output;
- `continue`, ne `return`, osim ako je stvarno fatalno;
- `shouldCreateResponse` treba ostati true ako bilo koji tool treba objašnjenje modela.

Testovi:

- batch sa jednim timeout i jednim success vraća oba outputa;
- batch sa unknown tool i timeout tool ne ostavlja model bez odgovora.

## Acceptance criteria

R3 je završen tek kada važi sve:

- Svaki tool call dobije kontrolisan output: success, known failure, timeout, duplicate, confirmation required.
- Never-resolving tool ne može zaglaviti voice loop.
- `toolRunning` se resetuje nakon success/failure/timeout.
- Duplicate `call_id` ne izvršava modifying tool dva puta.
- Duplicate confirmation se ne kreira dva puta.
- Exception iz `executeTool` ne prekida cijeli batch.
- Stale tool output poslije disconnect/nove generacije ne ide u pogrešnu sesiju.
- Batch tool call-ovi i dalje rade: jedan failure ne prekida ostale outpute.
- `npm.cmd run test:voice` prolazi.
- `npm.cmd run typecheck` prolazi.
- `npm.cmd run build` prolazi ili postojeći Vite warning je dokumentovan.
- `git diff --check` prolazi.
- Ako se dira Electron handler: `node --check electron/ipc_handlers/realtime.cjs`.
- Ako se dira Python backend: `python -m pytest -q python_backend/tests/test_realtime.py`.
- GitNexus `detect_changes(scope="all")` ili `scope="staged"` pokrenut prije commita.
- `docs/MIGRATION_PLAN.md` ažuriran.
- `agent_reports/YYYY-MM-DD_voice-realtime-r3.md` dodat.

## Preporučeni redoslijed rada

### Korak 0 — stanje i impact

Pi prvo:

```bash
git status --short
git log -5 --oneline
```

Zatim GitNexus impact prije izmjene centralnih simbola:

```text
RickyRealtimeClient.executeFunctionCalls
RickyRealtimeClient.returnToolOutput
RickyRealtimeClient.sendEvent
RickyRealtimeClient.disconnect
```

Ako `sendEvent` ili `disconnect` ispadnu HIGH/CRITICAL, nastaviti samo sa minimalnim, testiranim promjenama i zapisati rizik u report.

### Korak 1 — active/completed call tracking

Dodati minimalne mape/setove.

Prvo testovi:

- success čisti active,
- duplicate ne izvršava tool dva puta.

### Korak 2 — timeout wrapper

Dodati helper:

```ts
private runToolWithTimeout(...)
```

ili slično.

Ne koristiti globalne sleep-ove u testovima; koristiti DI `setTimeout` gdje je moguće.

### Korak 3 — exception → safe output

Obmotati `window.ricky.executeTool` u try/catch/timeout.

Svaki failure mora završiti `returnToolOutput`.

### Korak 4 — confirmation regression tests

Dodati testove da `CONFIRMATION_REQUIRED` i dalje radi i da duplicate ne pravi drugu confirmation.

### Korak 5 — stale generation/disconnect tests

Dodati testove za tool resolve nakon disconnect/nove generacije.

### Korak 6 — docs/report

Ažurirati:

- `docs/MIGRATION_PLAN.md`
- `agent_reports/YYYY-MM-DD_voice-realtime-r3.md`

Report mora sadržati:

- šta je promijenjeno,
- šta nije urađeno,
- GitNexus impact sažetak,
- test komande i rezultate,
- ručni smoke test checklist.

## Test komande

Minimalno:

```bash
npm.cmd run test:voice
npm.cmd run typecheck
npm.cmd run build
git diff --check
```

Ako je diran Electron realtime handler:

```bash
node --check electron/ipc_handlers/realtime.cjs
```

Ako je diran Python backend:

```bash
python -m pytest -q python_backend/tests/test_realtime.py
```

Prije commita:

```text
gitnexus_detect_changes(scope="all")
```

## Ručni smoke test nakon R3

Korisnik ili review agent treba provjeriti:

1. Normalan razgovor bez toolova.
2. Jedan read-only tool preko glasa.
3. Jedan modifying/confirmation tool preko glasa.
4. Confirmation required i dalje otvara dijalog.
5. Stop tokom aktivnog tool-a ne šalje zakašnjeli output u novu sesiju.
6. Reconnect tokom tool-a ne duplira modifying radnju.
7. Ako tool padne, agent kaže korisniku smisleno šta se desilo.

## Šta eksplicitno nije R3

Ne raditi:

- lokalni Whisper/Ollama/Piper voice engine,
- provider abstraction,
- automatski fallback na drugi LLM,
- veliki diagnostics panel,
- novi settings ekran,
- veliki UI redesign,
- promjene u `electron/main.cjs`,
- migraciju legacy computer-use toolova,
- generalni backend tool registry rewrite.

Ako Pi vidi da je nešto od ovoga potrebno, neka zapiše kao R4 preporuku, ali ne implementira u R3.

## R4 prijedlog poslije R3

Ako R3 bude stabilan, sljedeći smislen paket je:

- detaljniji diagnostics panel,
- transport/tool run timeline u UI-u,
- provider abstraction za jeftiniji/non-OpenAI voice mode,
- lokalni/jeftini fallback voice stack kao zaseban eksperimentalni dodatak.
