# Migration plan — RileyJarvis Windows Hybrid

Ovo je fazni plan migracije. Izvori:

- [ARCHITECTURE.md](./ARCHITECTURE.md) — osnovna podjela slojeva (Electron shell / Python backend / SQLite).
- [RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md](./RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md) — originalni generički hibridni plan (FAZA 0-18), detaljni koraci/acceptance kriterijumi za infrastrukturne faze.
- [ARCHITECTURE_VOICE_FIRST_REVISED.md](./ARCHITECTURE_VOICE_FIRST_REVISED.md) — voice-first arhitektonska odluka (Python NE preuzima audio pipeline; `src/lib/realtime.ts` ostaje primarni voice engine).
- [RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md](./RICKY_UI_REDESIGN_AGENT_PROMPT_V3_REALTIME_COMPANION.md) — UI redesign prompt (voice-first shell, Companion Mode) usklađen sa istom odlukom.

Ovaj fajl (`MIGRATION_PLAN.md`) je **jedini izvor istine za brojeve i redoslijed faza**. Gdje se broj faze ovdje razlikuje od broja u nekom od izvornih dokumenata iznad, važi ovaj fajl.

## Napomena o usklađivanju (2026-07-05)

Voice-first dokumenti su prvobitno predlagali sopstvenu numeraciju (VF-1...VF-6), a revidirana verzija je tražila da se to spoji u ovaj tracker — ali je pritom predložila iste brojeve faza (5-10) sa drugačijim sadržajem od originalnog hibridnog plana. Odluka: voice-first rad ima prioritet (to je sad osnovni proizvod, ne dodatak), pa je ubačen odmah nakon osnovne Python/Electron infrastrukture (FAZA 4-5), a generičke infrastrukturne faze koje se preklapaju (storage, event bridge, permission system, tool bridge) su spojene u odgovarajuće voice-first faze umjesto da ostanu duplirane. Ništa iz originalnog plana nije odbačeno — samo presloženo. Mapiranje starih → novih brojeva:

| Stari broj (original plan) | Novi broj (ovaj tracker) | Napomena |
| --- | --- | --- |
| 0-4 | 0-4 | nepromijenjeno |
| 5 (Electron starta Python) | 5 | nepromijenjeno |
| 6 (Tool bridge) | dio FAZE 11 | spojeno sa memory/artifact/screenshot alatima |
| 7 (SQLite storage) | 7 | zadržano, sadržaj proširen MVP voice-first tabelama |
| 8 (Migracija memorije) | dio FAZE 11 | spojeno |
| 9 (Event bridge/artifact panel) | dio FAZE 11 | spojeno |
| 10 (Screenshot/ui_inspect u Pythonu) | dio FAZE 11 | spojeno |
| 11 (Permission system) | 10 | pomjereno ranije, prije bilo kog tool executiona |
| 12 (Computer-use v1) | 13 | pomjereno |
| 13 (Computer-use v2) | 14 | pomjereno |
| 14 (Agent runtime) | 15 | pomjereno |
| 15 (OpenAI/Exa/image) | 16 | pomjereno |
| 16 (Disable legacy PowerShell) | 17 | pomjereno |
| 17 (Test suite) | 18 | pomjereno |
| 18 (Packaging) | 19 | pomjereno |
| — (novo) | 6, 8, 9, 12 | Realtime session security, Voice-first UI, Confirmations/Plans, Companion orb — iz voice-first dokumenata |

## Status faza

Kolona **Agent** je preporuka podjele rada (vidi `agent_reports/2026-07-05_codex-claude-split.md` za obrazloženje): Codex dobija mehaničke, izolovane, već precizno specificirane faze; Claude Code zadržava ono što dira već-radeću funkcionalnost, sigurnosno-kritične slojeve i arhitektonski centralne dijelove. Nije fiksno pravilo — samo polazna preporuka po fazi.

| Faza | Naziv | Status | Agent |
| --- | --- | --- | --- |
| 0 | Baseline i zaštita trenutnog stanja | ✅ urađeno (git init, tag `windows-port-baseline`, branch `hybrid-python-backend`) | Claude Code |
| 1 | Dokumentacija arhitekture | ✅ urađeno (ovaj `docs/` set) | Claude Code |
| 2 | Ažurirati AGENTS.md i CLAUDE.md | ✅ urađeno (uključuje agent_reports proceduru i konvenciju `Context:` komentara) | Claude Code |
| 3 | Razbiti `electron/main.cjs` bez promjene ponašanja | ✅ urađeno (env/window/PowerShell alati izvučeni + `core/ipc.cjs` IPC wiring sloj dodat; handler tijela/business logika i dalje u `main.cjs` namjerno — vidi `agent_reports/2026-07-05_split-main-cjs-faza3.md` i `agent_reports/2026-07-05_ipc-split-completion.md`) | Claude Code |
| 4 | Python backend skeleton (FastAPI, `/health`, `/tools`, `/tools/execute`) | ✅ urađeno (dummy `echo` tool, tool registry/executor, testovi 4 passed; vidi `agent_reports/2026-07-05_faza4-python-backend-skeleton.md`) | Codex |
| 5 | Electron pokreće Python backend | ✅ urađeno (dev auto-start, `/health` wait, log forwarding, stop on quit; vidi `agent_reports/2026-07-05_faza5-electron-starts-python-backend.md`) | Codex |
| 6 | **Realtime session security** — Python endpoint minta ephemeral OpenAI Realtime credential (premješta postojeću logiku iz `realtime:create-token` u `main.cjs`); standardni API ključ ostaje samo na backend strani | ✅ urađeno (`POST /realtime/session` u Python backend-u, `handleRealtimeCreateToken` u `main.cjs` sad zove Python umjesto direktno OpenAI; vidi `agent_reports/2026-07-05_faza6-realtime-session-security.md`) | Claude Code (dira live voice-auth tok koji već radi) |
| 7 | SQLite storage i action log (MVP tabele: `settings`, `realtime_sessions`, `voice_turns`, `transcripts`, `activity_events`, `confirmations`, `plans`, `plan_steps`, `tool_runs`, `artifacts`) | ✅ urađeno (SQLite init + `tool_runs` action log za success/failure; vidi `agent_reports/2026-07-05_faza7-sqlite-storage-action-log.md`) | Codex |
| 8 | **Voice-first UI refactor** oko postojećeg `src/lib/realtime.ts` — TopBar/BottomVoiceBar, `VoiceState`, Realtime Event Router, Activity/transcript prikaz | ✅ urađeno (VoiceState model, event router, TopBar/BottomVoiceBar, local Activity timeline; vidi `agent_reports/2026-07-05_faza8-voice-first-ui-refactor.md`) | Codex |
| 9 | **Confirmations + Plans/Proposals** — Approval dialog, `confirmation_id`, plan storage u SQLite (bez Notepad/auto-export) | ✅ urađeno (backend REST `/confirmations*`, `/plans*`, ConfirmationService/PlanService, repo-i; Electron IPC `confirmations:*`, `plans:*`; React `ConfirmationDialog` + `PlansPanel`; 8 novih testova; vidi `agent_reports/2026-07-05_faza9-confirmations-plans.md`) | Codex |
| 10 | Permission/risk/confirmation sloj za lokalne toolove (allowlist aplikacija, risk levels) **+ execution_id/cancellation_token state mašina** (SECURITY_HARDENING_PLAN.md sekcija 25) | ✅ urađeno (`app/agent/permission_engine.py` — risk/computer_mode/confirmation_id provjere, `confirmation_id` sad vezan za tool_name+payload_hash+expires_at; `app/agent/cancellation.py` — in-memory execution_id state mašina; `ToolExecutor` prepravljen da koristi oboje; `POST /tools/executions/{id}/cancel`; 20 novih testova; active window/path/network provjere OSTAJU van obima — FAZA 11/13/14; vidi `agent_reports/2026-07-05_faza10-permission-cancellation-engine.md`) | Claude Code (sigurnosno kritičan gate) |
| 11 | Tool registry + bezbjedni lokalni toolovi — migracija notes/records/artifacts, screenshot/ui_inspect u Python, event bridge ka artifact panelu | ✅ urađeno (Python tool handlers: notes/records/artifacts/screenshot/ui_inspect; `/events` polling event bridge; Electron delegacija sa legacy fallback; 13 novih testova; vidi `agent_reports/2026-07-05_faza11-tool-registry-local-tools.md`) | Codex |
| 12 | **Companion orb voice integracija** — zasebni `BrowserWindow`, orb prikazuje `VoiceState`, context menu, drag/position | ✅ urađeno (`electron/core/companionWindow.cjs` zasebni transparentan always-on-top prozor; `src/components/CompanionOrb.tsx` renderer entry preko `?view=companion`; VoiceState IPC forward `companion:voice-state-update`; context menu (Open/Toggle voice/Lock/Quit); tray; drag/position lock; toggle dugme u glavnom prozoru; vidi `agent_reports/2026-07-05_faza12-companion-orb.md`) | Codex |
| 13 | Computer-use Python v1 (koordinate) | ⬜ Odblokirano (Security Gate 0 zatvoren za MVP scope — vidi sekciju "Security Gates" niže). **Prvi korak ove faze mora biti active window enforcement u `permission_engine.py`** (`requires_active_window_match`/`allowed_apps`/`blocked_apps` polja već postoje u `ToolDefinition`, provjera namjerno odložena dovde da ne bude netestirana bez pravog toola) | Claude Code (1:1 zamjena PowerShell alata iz FAZE 3, treba provjera ponašanja) |
| 14 | Computer-use Python v2 (UI element targeting) | ⬜ Odblokirano (Security Gate 0 zatvoren za MVP scope — vidi sekciju "Security Gates" niže) | Claude Code (eksplorativno, UIA nepredvidljiv) |
| 15 | Agent runtime u Pythonu | ✅ urađeno (`LocalDesktopAssistant` u `app/agent/runtime.py` — jedan agent, bez multi-agent orkestracije; `conversation_state.py`/`agent_repo.py` čuvaju `agent_conversations`/`agent_messages` u SQLite; `model_client.py` OpenAI chat-completions wrapper sa `ModelClient` Protocol-om radi mockable testova; `prompt_builder.py` pretvara `ToolDefinition` listu u OpenAI function-calling schema; svaki tool-call koji model zatraži ide kroz ISTI `ToolExecutor` koji koristi i `POST /tools/execute` (isti FAZA 10 permission/cancellation sloj — agent runtime nema paralelni put mimo njega); `POST /agent/message` + `GET /agent/conversations/{id}`; 6 novih testova uklj. eksplicitnu provjeru da `records_delete` (critical) i `screen_snapshot` (computer_mode) ostaju blokirani kad ih zatraži model bez odobrenja; vidi `agent_reports/2026-07-06_faza15-agent-runtime.md`) | Claude Code (arhitektonski centralno) |
| 16 | Prebaciti OpenAI/Exa/image pozive u Python | ✅ urađeno (`python_backend/app/services/exa_client.py`, `openai_image_client.py`; `app/tools/web/search.py` (`web_search`), `app/tools/images/generate.py` (`image_generate`); Exa/OpenAI ključevi sad na Python backend strani (Security Gate 0 pattern); Electron delegacija u `PHASE11_DELEGATED_TOOLS`; 7 novih testova; vidi `agent_reports/2026-07-05_faza16-openai-exa-image-python.md`) | Codex |
| 17 | Deaktivacija legacy PowerShell toolova | ✅ urađeno (`electron/core/legacyTools.cjs` feature flag modul; `RICKY_USE_LEGACY_POWERSHELL_TOOLS` env var (default=1 dok FAZA 13/14 ne dodaju Python computer_* toolove); `handleToolsExecute` wrapp-uje computer_*/screen_snapshot/ui_inspect legacy handler-e iza flag-a + blokira PHASE11 fallback kad je legacy off; `docs/LEGACY_TOOLS.md` dokumentacija; vidi `agent_reports/2026-07-06_faza17-disable-legacy-powershell.md`) | Codex |
| 18 | Test suite i quality gate | ✅ urađeno (`npm run quality` pipeline: typecheck → check → build → pytest → smoke; `scripts/smoke-test.cjs` Electron end-to-end; `docs/TESTING.md` dokumentacija + CI prijedlog; 13 novih edge-case testova (schemas + events); ukupno 91 test; vidi `agent_reports/2026-07-06_faza18-test-suite-quality-gate.md`) | Codex |
| 19 | Packaging plan | ⬜ U TOKU (draft scope) — originalni spec (`RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md` FAZA 18) eksplicitno kaže "ne počinji packaging dok legacy PowerShell toolovi nisu disabled by default"; taj uslov **nije ispunjen** (FAZA 13/14 nisu urađene, `RICKY_USE_LEGACY_POWERSHELL_TOOLS` default i dalje 1). Odluka (2026-07-06): draft/prep dio (PyInstaller sidecar build, electron-builder `extraFiles`/`asarUnpack` konfiguracija, `pythonProcess.cjs` packaged-mode grananje koje danas potpuno isključuje auto-start backend-a) može početi odmah jer je nezavisan i stvaran posao; **finalni packaged build/ship čeka FAZA 13/14 + legacy default flip na 0**. | Codex/pi (draft) → Claude Code (verifikacija) |

Faze označene **bold** nazivom su nove/preuzete iz voice-first dokumenata; ostale su iz originalnog hibridnog plana (samo eventualno pomjerene, vidi tabelu mapiranja iznad).

## Backlog / Future Epics

Ideje koje su arhitektonski razrađene, ali **nisu aktivna MVP faza** i nemaju dodijeljen broj faze. Broj se dodjeljuje isključivo ovdje, tek kad korisnik eksplicitno odluči da epic ulazi u aktivan rad — arhitektonski dokumenti ne smiju sami sebi dodjeljivati brojeve faza (vidi napomenu o usklađivanju iznad — ovo pravilo postoji upravo da se izbjegne treći sudar numeracije).

| Epic | Status | Zavisi od | Detalji |
| --- | --- | --- | --- |
| Document / Paperwork Engine | Not active MVP work | FAZA 4-12 (Python skeleton, Realtime session security, Voice-first UI, Activity timeline, Confirmations/Plans, Permission system, Tool registry, Companion orb) | [DOCUMENT_ENGINE_FUTURE_EPIC.md](./DOCUMENT_ENGINE_FUTURE_EPIC.md) |
| GUI Localization (i18n: sr-Latn/en/de/es/fr) | ⚠️ **Not active MVP work — ne zaboraviti dodijeliti kad UI rad na Companion orb-u (FAZA 12) ili redizajnu počne**, implementation approach not yet decided (retrofit onto FAZA 8 components vs. combined with a future UI redesign) | FAZA 8 (Voice-first UI — components already exist with hardcoded strings that Localization PR-1 would touch: `VoiceTopBar.tsx`, `BottomVoiceBar.tsx`, `voiceState.ts`'s `voiceStateLabel()`) | [RICKY_GUI_LOCALIZATION_PLAN.md](./RICKY_GUI_LOCALIZATION_PLAN.md) |
| UI Redesign (voice-first shell v2 — TopBar/LeftVoicePanel/WorkspacePanel sa persistentnim Output/Activity/Plans/Memory/Screens tabovima, umjesto trenutnog Activity overlay-a; + Voice Input UX dodatak: Ephemeral Command/Dictation/Confirmation Review modovi, click-to-talk umjesto hold-to-talk, No-Notepad pravilo; + finalni vizuelni dizajn — dark/premium Ricky orb, Idle/Dictation/Confirmation ekrani po odobrenom mockup-u) | Not active MVP work — **redizajn postojećeg, ne novi rad** (FAZA 8/9 shell i confirmations/plans već rade); uključuje voice visual hierarchy, cancellation-aware Stop UI (već pokriveno backend-om iz FAZE 10) i Computer Mode safety UI | FAZA 8 (postojeći voice-first shell koji se redizajnira), FAZA 9 (postojeći confirmations/plans koji se redizajnira), FAZA 10 (permission/cancellation engine — UI treba odraziti stvarne tool_state vrijednosti), FAZA 12 (Companion orb — "Redesign step 4" u dokumentu ispod) | [RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md](./RICKY_UI_REDESIGN_AGENT_PROMPT_V4_AFTER_REVIEW.md) (arhitektura/ponašanje) + [RICKY_FINAL_UI_IMPLEMENTATION_PROMPT.md](./RICKY_FINAL_UI_IMPLEMENTATION_PROMPT.md) (finalni vizuelni izgled, dopunjen Stop/cancellation kontrolom i cross-referencama ka postojećim komponentama) |

## Security Gates

Izvor: [SECURITY_HARDENING_PLAN.md](./SECURITY_HARDENING_PLAN.md) — autoritativan produkcijski sigurnosni plan. Gates su **cross-cutting kriteriji** koji se ispunjavaju kroz postojeće numerisane faze — ovo nisu nove faze i ne mijenjaju numeraciju iznad. Samo `SECURITY_HARDENING_PLAN.md` opisuje detaljne kontrole; ovdje se samo mapira koja faza nosi koji gate i šta je blokirano dok gate nije zatvoren.

| Gate | Zatvara se kroz | Blokira | Status |
| --- | --- | --- | --- |
| **Security Gate 0** (Electron hardening, IPC allowlist, backend localhost/auth, no arbitrary shell, tool manifest/risk model, active window validation, **execution_id/cancellation_token state mašina**, log redaction, path sandbox, security self-test MVP) | ✅ FAZA 3 (`core/ipc.cjs`), ✅ FAZA 4-5 (backend postoji, Electron ga pokreće), ✅ FAZA 6 (realtime credential handling — standardni API ključ premješten na Python), ✅ FAZA 10 (permission engine + cancellation state mašina — `app/agent/permission_engine.py`, `app/agent/cancellation.py`), ✅ FAZA 11 djelimično (tool manifest primijenjen na 13 stvarno migriranih toolova — notes/records/artifacts/screenshot/ui_inspect, sada prolaze kroz FAZA 10 permission engine; `ui_inspect` čita active window ali **ne postoji enforcement** allowed_apps/blocked_apps provjere u `permission_engine.py` — ovo ostaje namjerno za FAZU 13), ✅ **backend local auth token** (Security PR-1 — `app/core/auth.py`, `RICKY_LOCAL_TOKEN` generisan po Electron sesiji u `pythonProcess.cjs`, provjeren na svakom requestu; vidi `agent_reports/2026-07-05_backend-local-auth-token.md`), ✅ **log redaction + path sandbox + security self-test MVP** (Gate 0 gap-closing rad — `app/core/logging.py` `SecretRedactionFilter`, `app/core/path_sandbox.py` primitivi, `app/core/security_self_test.py` + `GET /security/self-test`, `electron/core/secureWebPreferences.cjs` jedinstven izvor za `sandbox`/`webSecurity`/`allowRunningInsecureContent` — sad eksplicitno postavljeni, ne oslonjeni na Electron default, `electron/core/securitySelfTest.cjs` kombinuje Electron+backend provjere i fail-closed blokira produkcijski build; 24 nova testa + prošireni smoke test (7 koraka); vidi `agent_reports/2026-07-06_gate0-selftest-pathsandbox.md`) | ~~**FAZA 13 i FAZA 14 (computer-use v1/v2)**~~ Gate 0 zatvoren za sve stavke osim active window enforcement, koja se sad radi kao prvi korak same FAZE 13 (ne kao poseban predkorak — ista logika kao FAZA 10 → FAZA 11). FAZA 13/14 mogu krenuti. | ✅ **Zatvoren za MVP scope** — preostaje samo active window enforcement, namjerno odloženo do prvog stvarnog `computer_*` Python toola (FAZA 13) jer bi provjera bez toola koji je koristi bila neiskorišten kod bez pravog testa. Legacy PowerShell computer-use (`computer_*` alati) i dalje radi bez permission sloja **i bez auth tokena** direktno iz `electron/main.cjs` dok FAZA 13/14 ne dodaju Python zamjenu — vidi `SECURITY_MODEL.md` "Status implementacije" |
| **Security Gate 1** (document privacy modes, prompt injection boundaries, action receipt privacy status, audit trail, rate limits, dependency scanning, CI security checks) | ✅ FAZA 9 (confirmations/plans storage + approval flow), ✅ FAZA 10 (permission engine sad automatski zahtijeva/validira confirmation_id za tools sa `requires_confirmation`/`risk=critical`), buduća aktivacija Document Engine epic-a (vidi Backlog iznad), CI podešavanje | Beta/test korisnici | ⬜ Nije zatvoren (confirmation issuing + validation sad postoji za Python-registrovane toolove; document privacy modes, prompt injection boundaries, CI security checks i dalje nedostaju) |
| **Security Gate 2** (code signing, signed updates, encrypted secrets/local storage, self-test hard fail, no devtools/debug u produkciji, pentest checklist, incident/recovery plan) | FAZA 19 (packaging) | Production release | ⬜ Nije zatvoren |

**Preduslov za Security PR-1** (Electron security config check, preload API inventory, generic IPC zabrana, backend localhost/auth design, self-test skeleton — vidi `SECURITY_HARDENING_PLAN.md` sekcija 23): ✅ FAZA 3 je sad kompletna — `core/ipc.cjs` postoji kao eksplicitan IPC wiring/allowlist sloj (vidi `agent_reports/2026-07-05_ipc-split-completion.md`). `preload.cjs` je pri provjeri već bio usklađen sa allowlist principom (samo 4 imenovane funkcije, bez generic `ipcRenderer.invoke` prolaza). Ostatak Security PR-1 (backend localhost/auth design, self-test skeleton) i dalje čeka FAZA 4-5.

## Redoslijed PR-ova

```text
PR 01 - Baseline and docs
PR 02 - Project agent rules update
PR 03 - Split electron/main.cjs into modules
PR 04 - Add Python backend skeleton
PR 05 - Electron starts Python backend
PR 06 - Realtime session security (Python mints ephemeral credential)
PR 07 - SQLite storage and action log (voice-first MVP schema)
PR 08 - Voice-first UI refactor (TopBar/BottomVoiceBar/VoiceState/Event Router)
PR 09 - Confirmations + Plans/Proposals UI and storage
PR 10 - Permission/risk/confirmation system for local tools
PR 11 - Tool registry + safe local tools (memory/artifacts/screenshot/ui_inspect)
PR 12 - Companion orb voice integration
PR 13 - Python computer-use v1
PR 14 - Python computer-use v2 element targeting
PR 15 - Python agent runtime
PR 16 - Move OpenAI/Exa/image integrations to Python
PR 17 - Disable legacy PowerShell tools by default
PR 18 - Test suite and quality gate
PR 19 - Packaging
```

## Pravila rada (važe za svaku fazu)

1. Ne raditi veliki refaktor u jednom koraku — jedna faza = jedan mali skup promjena.
2. Prije izmjene postojeće funkcije/klase/metode, prvo pročitati njen kontekst i call sites.
3. Ako je GitNexus dostupan za ovaj repo, prije izmjene simbola pokrenuti impact analysis; ako HIGH/CRITICAL rizik — stati i prijaviti korisniku. Ako GitNexus nije podešen, uraditi ručnu analizu blast radius-a.
4. Ne raditi find-and-replace rename simbola ako postoji GitNexus rename alat.
5. Ne brisati postojeće PowerShell toolove dok Python zamjena nije testirana.
6. Ne uvoditi shell execution tool koji model može pozvati slobodno.
7. Ne stavljati API ključeve, `.env.local`, logove sa tajnama ili `node_modules` u git.
8. Prije commita pokrenuti relevantne testove/build i prijaviti izmijenjene fajlove, promjene ponašanja i rizike.
9. **Ne zamjenjivati `src/lib/realtime.ts` (WebRTC/OpenAI Realtime) custom Python audio pipeline-om.** Python ne preuzima mikrofon/VAD/STT/TTS u MVP-u — vidi `ARCHITECTURE_VOICE_FIRST_REVISED.md`.
10. Event nazivi: dvotačka za Electron IPC kanale (`voice:start`), tačka za interne app/backend evente (`voice.state_changed`), sirovi OpenAI nazivi nepromijenjeni do event-router sloja.

## Master prompt (za novi agent session)

```text
You are working on RileyJarvis Windows Hybrid — a voice-first desktop companion.

Goal:
Migrate the current Windows-adapted Electron RileyJarvis prototype to a modular
hybrid architecture where React/Electron remains the UI shell and Python becomes
the backend brain for session security, storage, confirmations/plans, tools,
Windows automation and agent runtime. Voice is the primary interaction mode.

Hard architecture rules:
- React renderer is UI. src/lib/realtime.ts (WebRTC/OpenAI Realtime) is the
  primary voice/audio pipeline and must not be replaced by a Python audio engine.
- Electron main process is only app shell, IPC bridge and Python process manager.
- Python backend owns session security, storage, confirmations/plans, tools,
  automation, and non-realtime AI integrations (web search, image generation) —
  but NOT microphone/VAD/STT/TTS in the MVP.
- Do not add new business logic to electron/main.cjs.
- Do not remove legacy PowerShell tools until Python replacements are implemented and tested.
- No arbitrary shell execution tool exposed to the model.
- All tool calls must go through a tool registry and permission/risk layer.
- All tool calls must be logged.

Current task:
Implement only PHASE <NUMBER>: <PHASE NAME> from docs/MIGRATION_PLAN.md.
Do not implement later phases.
```

## Najveće greške koje treba izbjeći

```text
- Full rewrite u Python odmah.
- Brisanje Electron UI-ja.
- Guranje nove logike nazad u electron/main.cjs.
- Preuranjen packaging.
- Korištenje koordinatnog klika kao primarnog rješenja dugoročno.
- Izlaganje shell command tool-a modelu.
- Miješanje storage logike između JSON, Electron i Python bez plana.
- Pravljenje multi-agent sistema prije stabilnog tool registry-ja.
- Uvođenje novih dependencies bez objašnjenja.
- Nevođenje action log-a.
- Zamjena src/lib/realtime.ts custom Python audio pipeline-om.
- Planovi kao gomila .txt/.md fajlova umjesto SQLite zapisa.
```

## Definicija uspjeha

```text
- Electron/React UI radi kao prije, sada voice-first (glas primaran, tekst fallback).
- src/lib/realtime.ts i dalje jedini audio pipeline (WebRTC <-> OpenAI Realtime).
- Electron automatski startuje Python backend.
- Python backend ima /health, /tools, /tools/execute i realtime session endpoint.
- Toolovi su registrovani u Python registry-ju.
- Tool calls prolaze kroz permission/risk layer.
- Tool calls, voice turns i activity se loguju u SQLite.
- Confirmations i Plans su UI/DB zapisi, ne fajlovi.
- Artifacts dolaze iz Python backend-a i prikazuju se u React panelu.
- Screenshot/ui_inspect rade iz Python-a.
- Companion orb prikazuje VoiceState i radi kao voice entry point.
- Osnovni computer-use radi kroz Python na Notepad smoke testu.
- Legacy PowerShell tools su disabled by default.
- Agent runtime je u Python-u.
- App se može buildati bez rušenja.
```
