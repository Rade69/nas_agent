# Multi-agent security architecture map

**Datum:** 2026-07-10  
**Projekat:** RileyJarvis Windows Hybrid ("Nas-agent")  
**Svrha:** jedan vizuelni dokument koji spaja hijerarhiju fajlova,
sigurnosne mjere i multi-agentski radni tok.

> Izvor istine za faze je `docs/MIGRATION_PLAN.md`. Ovaj dokument je mapa za
> orijentaciju; ne zamjenjuje tracker, `SECURITY_HARDENING_PLAN.md`,
> `SECURITY_MODEL.md` ili `TOOL_CONTRACTS.md`.

---

## 1. Velika slika

```mermaid
flowchart TB
  User["Nikola / korisnik"]

  subgraph Agents["Multi-agent razvojni sloj"]
    Claude["Claude Code<br/>glavni implementacioni agent"]
    Codex["Codex<br/>review, docs, ciljane izmjene"]
    Pi["pi agent<br/>OpenRouter + vise LLM modela"]
  end

  subgraph WorkflowGuard["Radne ograde"]
    AGENTS["AGENTS.md / CLAUDE.md<br/>pravila rada"]
    Tracker["docs/MIGRATION_PLAN.md<br/>tracker kao izvor istine"]
    Reports["agent_reports/<br/>trag svake promjene"]
    GitNexus["GitNexus<br/>impact + detect changes"]
    Git["Git<br/>mali commitovi, status prije rada"]
  end

  subgraph App["RileyJarvis Windows Hybrid"]
    Renderer["src/<br/>React UI + Realtime voice pipeline"]
    Electron["electron/<br/>tanak shell, IPC, prozori, Python process manager"]
    Backend["python_backend/app/<br/>agent runtime, tool registry, security, storage"]
    SQLite["SQLite<br/>tool runs, events, confirmations, plans, artifacts"]
    Legacy["electron/tools_legacy/<br/>legacy PowerShell/media fallback"]
    Assets["assets/<br/>Ricky branding, orb, icons"]
  end

  subgraph External["Vanjski servisi"]
    OpenAI["OpenAI<br/>Realtime + model/image APIs"]
    Exa["Exa / web search"]
    OpenRouter["OpenRouter<br/>pi agent modeli"]
    OS["Windows OS<br/>active window, UI automation"]
  end

  User --> Agents
  Claude --> Git
  Codex --> Git
  Pi --> Git
  Agents --> AGENTS
  Agents --> Tracker
  Agents --> Reports
  Agents --> GitNexus

  Renderer -->|"explicit preload APIs"| Electron
  Electron -->|"localhost + Bearer token"| Backend
  Backend --> SQLite
  Backend -->|"short-lived realtime/session credential"| OpenAI
  Renderer -->|"WebRTC Realtime using ephemeral credential"| OpenAI
  Backend --> Exa
  Backend --> OS
  Electron -. "legacy fallback, gated by feature flag" .-> Legacy
  Legacy -. "temporary, do not expand" .-> OS
  Renderer --> Assets

  Pi --> OpenRouter
```

**Glavno pravilo:** React/Electron je UI shell; Python backend je vlasnik
agent runtime-a, toolova, storage-a, automation-a i AI integracija. Nova
business/agent/storage/AI logika ne ide u `electron/main.cjs`.

---

## 2. Hijerarhija fajlova

```mermaid
flowchart LR
  Root["Nas-agent/"]

  Root --> Src["src/ React renderer"]
  Src --> SrcComponents["components/<br/>ArtifactPanel, RickyOrb, CompanionOrb, pixel UI"]
  Src --> SrcLib["lib/<br/>realtime.ts, voiceState, event routing/helpers"]
  Src --> SrcStyles["styles/<br/>split CSS layers 00-14"]

  Root --> Electron["electron/ Electron shell"]
  Electron --> Main["main.cjs<br/>entry + wiring only"]
  Electron --> Preload["preload.cjs<br/>explicit window.ricky API"]
  Electron --> Core["core/<br/>env, window, IPC, security self-test, secure prefs"]
  Electron --> Services["services/<br/>pythonProcess, pythonClient"]
  Electron --> IpcHandlers["ipc_handlers/<br/>app, realtime, events, plans, confirmations"]
  Electron --> LegacyTools["tools_legacy/<br/>PowerShell + legacy media fallback"]

  Root --> Backend["python_backend/app/ Python backend"]
  Backend --> Api["api/<br/>health, tools, realtime, confirmations, plans, events, agent, security"]
  Backend --> Agent["agent/<br/>runtime, tool_executor, permission_engine, cancellation"]
  Backend --> Tools["tools/<br/>system, memory, web, images, artifacts"]
  Backend --> ServicesPy["services/<br/>confirmation, plan, event, artifact, OpenAI/Exa clients"]
  Backend --> Storage["storage/<br/>db + repositories"]
  Backend --> Schemas["schemas/<br/>tool, confirmation, plan, realtime, agent"]
  Backend --> CorePy["core/<br/>auth, config, logging, path_sandbox, payload_hash, self-test"]
  Backend --> Tests["tests/<br/>pytest coverage for backend/security/tools"]

  Root --> Docs["docs/<br/>migration, security, testing, plans, briefs"]
  Root --> Reports["agent_reports/<br/>agent task reports and audit trail"]
  Root --> Assets["assets/<br/>branding, orb, icons, GUI references"]
  Root --> Scripts["scripts/<br/>smoke-test.cjs"]
  Root --> Config["package.json, vite.config.ts, tsconfig.json,<br/>electron-builder.yml, AGENTS.md, CLAUDE.md"]
```

### Prakticna navigacija

| Dio | Glavni fajlovi/folderi | Uloga |
| --- | --- | --- |
| UI shell | `src/App.tsx`, `src/components/**`, `src/styles/**` | Vizuelni dio, voice UI, artifact panel, confirmations, companion/mini orb. |
| Realtime voice | `src/lib/realtime.ts`, `src/lib/realtimeEventRouter.ts`, `src/lib/voiceState.ts` | WebRTC/OpenAI Realtime pipeline ostaje u rendereru; Python ne preuzima mikrofon/VAD/STT/TTS u MVP-u. |
| Electron shell | `electron/main.cjs`, `electron/core/**`, `electron/ipc_handlers/**` | Prozori, IPC wiring, secure web preferences, Python process manager. |
| Backend client/process | `electron/services/pythonProcess.cjs`, `electron/services/pythonClient.cjs` | Pokretanje backend-a, local token, Bearer auth prema backend-u. |
| Python API | `python_backend/app/api/**` | REST endpointi za health, tools, realtime session, events, confirmations, plans, agent. |
| Agent/tool runtime | `python_backend/app/agent/**` | Tool registry, executor, permission engine, cancellation, model client, runtime. |
| Storage | `python_backend/app/storage/**` | SQLite schema i repository sloj. |
| Security core | `python_backend/app/core/**`, `electron/core/securitySelfTest.cjs`, `electron/core/secureWebPreferences.cjs` | Auth, redaction, path sandbox, security self-test, Electron hardening. |
| Legacy | `electron/tools_legacy/**`, `electron/core/legacyTools.cjs` | Privremeni fallback; ne siriti i ne brisati dok Python zamjena nije testirana. |
| Operativni trag | `agent_reports/**`, `docs/MIGRATION_PLAN.md` | Sta je uradjeno, zasto, testovi, rizici, status faza. |

---

## 3. Runtime tok aplikacije

```mermaid
sequenceDiagram
  autonumber
  participant U as Korisnik
  participant R as React renderer
  participant E as Electron shell
  participant B as Python backend
  participant P as Permission engine
  participant T as Tool executor
  participant DB as SQLite
  participant AI as OpenAI/Exa
  participant OS as Windows OS

  U->>R: Glas, tekst, UI klik
  R->>E: window.ricky.* preload API
  E->>B: Localhost request + Authorization Bearer token
  B->>P: Provjera risk/computer_mode/confirmation_id
  alt treba potvrda
    P-->>B: CONFIRMATION_REQUIRED
    B-->>R: pending confirmation
    U->>R: Approve/Reject u UI
    R->>B: approval preko confirmation endpointa
  end
  B->>T: execute tool
  T->>OS: samo ako policy dozvoljava
  T->>DB: tool_runs/action log/events
  B-->>R: result/artifact/event
  R-->>U: UI update
  R->>AI: WebRTC Realtime samo sa short-lived credentialom
  B->>AI: backend-side OpenAI/Exa/image pozivi kada su potrebni
```

---

## 4. Implementirane sigurnosne mjere

```mermaid
flowchart TB
  subgraph ElectronSec["Electron / renderer zastita"]
    WebPrefs["secureWebPreferences<br/>nodeIntegration=false<br/>contextIsolation=true<br/>sandbox=true<br/>webSecurity=true"]
    IPC["IPC allowlist<br/>bez generic ipcRenderer.invoke"]
    CSP["Production CSP<br/>meta CSP u buildu + self-test gate"]
    Preload["preload.cjs<br/>samo eksplicitni window.ricky API"]
    XSS["Renderer XSS audit<br/>dangerouslySetInnerHTML samo Mermaid strict SVG"]
  end

  subgraph BackendSec["Backend zastita"]
    Localhost["127.0.0.1 lokalni backend"]
    Token["RICKY_LOCAL_TOKEN<br/>Authorization: Bearer token"]
    SelfTest["/security/self-test<br/>Electron + backend gate"]
    Redaction["SecretRedactionFilter<br/>bez API/token logovanja"]
    PathSandbox["path_sandbox primitivi<br/>spremno za file tools"]
  end

  subgraph ToolSec["Tool / agent zastita"]
    Manifest["ToolDefinition manifest<br/>risk, confirmation, computer_mode"]
    Permission["permission_engine.py<br/>risk + confirmation_id + payload_hash + expiry"]
    Cancellation["cancellation.py<br/>execution_id + cancel-all / per-id cancel"]
    ComputerMode["Computer Mode<br/>OFF na startu, high-risk gate"]
    ActiveWindow["Active window validation<br/>blocked apps za computer_* write akcije"]
    PromptInjection["External content escalation<br/>read->act trazi potvrdu"]
  end

  subgraph WorkflowSec["Razvojne ograde"]
    NoShell["Nema model-facing arbitrary shell toola"]
    NoMainLogic["Nema nove business logike u electron/main.cjs"]
    Reports["agent_reports za svaku fazu/zadatak"]
    GitNexus["GitNexus impact prije simbola<br/>detect prije commita"]
    Tracker["MIGRATION_PLAN tracker<br/>jedini status faza"]
    Quality["npm run quality<br/>typecheck, check, build, pytest, smoke"]
  end

  ElectronSec --> BackendSec
  BackendSec --> ToolSec
  ToolSec --> WorkflowSec
```

### Security kontrolna lista

| Kontrola | Gdje je vidljiva | Status u ovom projektu |
| --- | --- | --- |
| Electron hardening | `electron/core/secureWebPreferences.cjs`, `electron/core/window.cjs` | Implementirano za renderer prozore; self-test provjerava produkcijske postavke. |
| IPC allowlist | `electron/core/ipc.cjs`, `electron/ipc_handlers/**`, `electron/preload.cjs` | Eksplicitni kanali i preload API, bez generic IPC prolaza. |
| Backend local auth token | `python_backend/app/core/auth.py`, `electron/services/pythonProcess.cjs`, `electron/services/pythonClient.cjs` | Electron generise per-session token i backend zahtijeva Bearer token u Electron-pokrenutom toku. |
| Realtime key isolation | `python_backend/app/api/realtime.py`, `src/lib/realtime.ts` | Standardni API key ostaje backend-side; renderer dobija kratkozivuci Realtime credential. |
| Tool manifest | `python_backend/app/schemas/tool.py`, `python_backend/app/agent/tool_registry.py` | Toolovi nose risk/confirmation/computer_mode metadata. |
| Permission engine | `python_backend/app/agent/permission_engine.py` | High/critical akcije prolaze kroz risk, computer mode i confirmation provjere. |
| Confirmation binding | `python_backend/app/core/payload_hash.py`, confirmation service/repo | `confirmation_id` je vezan za tool name, payload hash i expiry; ne moze se lako replay/swap. |
| Cancellation | `python_backend/app/agent/cancellation.py`, `POST /tools/executions/cancel-all` | Stop/kill-switch moze traziti backend cancellation, ne samo prekinuti glas. |
| Computer Mode safety | `electron/main.cjs`, `python_backend/app/agent/permission_engine.py`, UI components | Mode je eksplicitan, OFF na startu, high-risk toolovi ga zahtijevaju. |
| Active window / blocked apps | `python_backend/app/agent/permission_engine.py`, `python_backend/app/tools/system/computer.py` | Python computer-use write toolovi imaju blocked-app zastitu. |
| Log redaction | `python_backend/app/core/logging.py` | API kljucevi/tokeni se rediguju u backend logovima. |
| Path sandbox primitive | `python_backend/app/core/path_sandbox.py` | Primitivi postoje; obavezno koristiti kad se dodaju file/path toolovi. |
| CSP | `vite.config.ts`, `electron/core/securitySelfTest.cjs` | Produkcijski build dobija CSP meta; self-test gate provjerava. |
| XSS audit | `agent_reports/2026-07-09_pi-xss-sink-audit.md`, `src/components/ArtifactPanel.tsx` | Jedini HTML sink je Mermaid SVG pod `securityLevel: "strict"`; ostalo React escape. |
| Fail-closed / kill switch | `electron/main.cjs`, `src/App.tsx`, related reports | Global/visible Stop gasi voice/mic, forsira Computer Mode OFF i zove cancel-all. |
| Quality gate | `package.json`, `docs/TESTING.md`, `python_backend/tests/**` | `npm run quality` spaja typecheck, syntax check, build, pytest i smoke. |

---

## 5. Multi-agentski radni tok

```mermaid
sequenceDiagram
  autonumber
  participant N as Nikola
  participant C as Claude Code
  participant X as Codex
  participant P as pi agent / OpenRouter
  participant G as Git working tree
  participant GN as GitNexus
  participant D as docs + agent_reports

  N->>C: Primarni fazni zadaci
  N->>X: Review, dokumentacija, ciljane popravke
  N->>P: Paralelni refactor/audit zadaci

  C->>G: git status + git log prije rada
  X->>G: git status + git log prije rada
  P->>G: git status + git log prije rada

  C->>GN: impact prije izmjene simbola
  X->>GN: impact/detect kad dira simbole ili prije commita
  P->>GN: detect/report po zadatku

  C->>G: mali commit sa reportom
  X->>G: mali commit sa reportom
  P->>G: mali commit/report ili ostavi jasno odvojene fajlove

  C->>D: azurira agent_reports i tracker kad zatvara fazu
  X->>D: ne dira tudje izmjene, reportuje scope
  P->>D: pise pi_* reports za audit/refactor

  N->>G: Pregleda commitove i odlucuje sljedeci korak
```

### Pravila saradnje u istom filesystemu

1. `git status` i `git log` prije rada.
2. Ne stageovati tudje nekomitovane izmjene.
3. Recurring collision fajlove (`python_backend/app/core/config.py`,
   `app/main.py`, `electron/main.cjs`) citati svjeze neposredno prije izmjene.
4. Jedna faza ili jedan mali zadatak = jedan mali skup promjena.
5. `agent_reports/` objasnjava sta je dirano, zasto, kako je provjereno i sta
   nije dirano.
6. `docs/MIGRATION_PLAN.md` tracker se azurira u istom commitu samo kad se
   stvarno zatvara faza/acceptance kriterij.
7. Ako GitNexus kaze HIGH/CRITICAL impact, agent staje i prijavljuje rizik.

---

## 6. Granice odgovornosti

```mermaid
flowchart LR
  UI["React renderer<br/>UI, Realtime WebRTC, visual state"] --> Shell["Electron shell<br/>preload, windows, IPC, backend process"]
  Shell --> Backend["Python backend<br/>tools, agent runtime, storage, security"]
  Backend --> Data["SQLite + action log<br/>plans, confirmations, events, tool_runs"]
  Backend --> Tools["Tool executor<br/>manifest + permission engine"]
  Tools --> OS["Windows automation<br/>only through gated Python tools"]

  Shell -. "temporary fallback only" .-> Legacy["Legacy PowerShell/media tools"]
  Legacy -. "feature-flagged / do not expand" .-> OS

  UI -. "must not own" .-> BackendLogic["agent/storage/AI business logic"]
  Shell -. "must not own" .-> BackendLogic
```

**Najvaznija granica:** model output nikad nije sigurnosna granica. Tool
executor i permission engine su sigurnosna granica.

---

## 7. Kako koristiti ovu mapu

- Kada novi agent ulazi u projekat: prvo procita ovaj dokument, `AGENTS.md`,
  `CLAUDE.md` i `docs/MIGRATION_PLAN.md`.
- Kada se dira UI: gledati `src/**`, ali ne mijesati runtime/tool logiku u UI.
- Kada se dira OS/tool ponasanje: gledati `python_backend/app/agent/**`,
  `python_backend/app/tools/**`, `TOOL_CONTRACTS.md` i security dokumente.
- Kada se dira Electron: provjeriti da promjena ostaje shell/IPC/process-manager
  sloj, bez nove business logike u `electron/main.cjs`.
- Kada se radi commit: pokrenuti relevantne provjere, `gitnexus_detect_changes`
  i napisati `agent_reports/` izvjestaj.

---

## 8. Poznate napomene

- `docs/ARCHITECTURE.md` je referenciran u nekim dokumentima, ali trenutno nije
  prisutan u tree-u. Za status faza koristiti `docs/MIGRATION_PLAN.md`.
- `python_backend/app/core/path_sandbox.py` postoji kao security primitive; ne
  smije ostati "ukras" kada se dodaju toolovi koji primaju putanje.
- Legacy PowerShell/media put je privremen. Ne siriti ga i ne brisati ga dok
  Python zamjena nije testirana.
- `agent_reports/` nije samo arhiva; to je radni trag za vise agenata koji
  dijele isti filesystem.
