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
| 10 | Permission/risk/confirmation sloj za lokalne toolove (allowlist aplikacija, risk levels) | ⬜ | Claude Code (sigurnosno kritičan gate) |
| 11 | Tool registry + bezbjedni lokalni toolovi — migracija notes/records/artifacts, screenshot/ui_inspect u Python, event bridge ka artifact panelu | ⬜ | Codex |
| 12 | **Companion orb voice integracija** — zasebni `BrowserWindow`, orb prikazuje `VoiceState`, context menu, drag/position | ⬜ | Codex |
| 13 | Computer-use Python v1 (koordinate) | ⬜ 🔒 BLOCKED dok Security Gate 0 nije zatvoren (vidi sekciju "Security Gates" niže) | Claude Code (1:1 zamjena PowerShell alata iz FAZE 3, treba provjera ponašanja) |
| 14 | Computer-use Python v2 (UI element targeting) | ⬜ 🔒 BLOCKED dok Security Gate 0 nije zatvoren (vidi sekciju "Security Gates" niže) | Claude Code (eksplorativno, UIA nepredvidljiv) |
| 15 | Agent runtime u Pythonu | ⬜ | Claude Code (arhitektonski centralno) |
| 16 | Prebaciti OpenAI/Exa/image pozive u Python | ⬜ | Codex |
| 17 | Deaktivacija legacy PowerShell toolova | ⬜ | Codex |
| 18 | Test suite i quality gate | ⬜ | Codex |
| 19 | Packaging plan | ⬜ | Codex (draft) → Claude Code (verifikacija) |

Faze označene **bold** nazivom su nove/preuzete iz voice-first dokumenata; ostale su iz originalnog hibridnog plana (samo eventualno pomjerene, vidi tabelu mapiranja iznad).

## Backlog / Future Epics

Ideje koje su arhitektonski razrađene, ali **nisu aktivna MVP faza** i nemaju dodijeljen broj faze. Broj se dodjeljuje isključivo ovdje, tek kad korisnik eksplicitno odluči da epic ulazi u aktivan rad — arhitektonski dokumenti ne smiju sami sebi dodjeljivati brojeve faza (vidi napomenu o usklađivanju iznad — ovo pravilo postoji upravo da se izbjegne treći sudar numeracije).

| Epic | Status | Zavisi od | Detalji |
| --- | --- | --- | --- |
| Document / Paperwork Engine | Not active MVP work | FAZA 4-12 (Python skeleton, Realtime session security, Voice-first UI, Activity timeline, Confirmations/Plans, Permission system, Tool registry, Companion orb) | [DOCUMENT_ENGINE_FUTURE_EPIC.md](./DOCUMENT_ENGINE_FUTURE_EPIC.md) |
| GUI Localization (i18n: sr-Latn/en/de/es/fr) | Not active MVP work — implementation approach not yet decided (retrofit onto FAZA 8 components vs. combined with a future UI redesign) | FAZA 8 (Voice-first UI — components already exist with hardcoded strings that Localization PR-1 would touch: `VoiceTopBar.tsx`, `BottomVoiceBar.tsx`, `voiceState.ts`'s `voiceStateLabel()`) | [RICKY_GUI_LOCALIZATION_PLAN.md](./RICKY_GUI_LOCALIZATION_PLAN.md) |

## Security Gates

Izvor: [SECURITY_HARDENING_PLAN.md](./SECURITY_HARDENING_PLAN.md) — autoritativan produkcijski sigurnosni plan. Gates su **cross-cutting kriteriji** koji se ispunjavaju kroz postojeće numerisane faze — ovo nisu nove faze i ne mijenjaju numeraciju iznad. Samo `SECURITY_HARDENING_PLAN.md` opisuje detaljne kontrole; ovdje se samo mapira koja faza nosi koji gate i šta je blokirano dok gate nije zatvoren.

| Gate | Zatvara se kroz | Blokira | Status |
| --- | --- | --- | --- |
| **Security Gate 0** (Electron hardening, IPC allowlist, backend localhost/auth, no arbitrary shell, tool manifest/risk model, active window validation, log redaction, path sandbox, security self-test MVP) | ✅ FAZA 3 (`core/ipc.cjs`), ✅ FAZA 4-5 (backend postoji, Electron ga pokreće — još bez auth tokena), ✅ FAZA 6 (realtime credential handling — standardni API ključ premješten na Python, vidi `agent_reports/2026-07-05_faza6-realtime-session-security.md`), ⬜ FAZA 10 (permission/risk layer), ⬜ FAZA 11 (tool manifest, path sandbox) | **FAZA 13 i FAZA 14 (computer-use v1/v2)** — ne smiju se širiti van lokalnog dev prototipa dok Gate 0 nije zatvoren. Takođe blokira production installer (FAZA 19). | ⬜ Nije zatvoren — 3/5 stavki gotovo (IPC allowlist, backend postoji, realtime API key izolacija); preostaje backend local auth token (dio Security PR-1) i FAZA 10/11 (permission/risk layer, tool manifest, path sandbox). Legacy PowerShell computer-use i dalje radi bez permission sloja direktno iz `electron/main.cjs` — vidi `SECURITY_MODEL.md` "Status implementacije" |
| **Security Gate 1** (document privacy modes, prompt injection boundaries, action receipt privacy status, audit trail, rate limits, dependency scanning, CI security checks) | ✅ FAZA 9 (confirmations/plans storage + approval flow), buduća aktivacija Document Engine epic-a (vidi Backlog iznad), CI podešavanje | Beta/test korisnici | ⬜ Nije zatvoren (confirmations storage postoji, ali permission/risk layer koji automatski *issue*-a confirmations iz tool execution stiže tek u FAZI 10) |
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
