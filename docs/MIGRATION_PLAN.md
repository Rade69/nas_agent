# Migration plan — RileyJarvis Windows Hybrid

Ovo je fazni plan migracije iz [ARCHITECTURE.md](./ARCHITECTURE.md). Pun originalni dokument sa svim detaljima (koracima, primjerima koda, acceptance kriterijumima za svaku fazu) je u [RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md](./RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md) — ovaj fajl je kratki pregled/tracker faza i pravila rada.

## Status faza

| Faza | Naziv | Status |
| --- | --- | --- |
| 0 | Baseline i zaštita trenutnog stanja | ✅ urađeno (git init, tag `windows-port-baseline`, branch `hybrid-python-backend`) |
| 1 | Dokumentacija arhitekture | ✅ urađeno (ovaj `docs/` set) |
| 2 | Ažurirati AGENTS.md i CLAUDE.md | ✅ urađeno (uključuje agent_reports proceduru i konvenciju `Context:` komentara) |
| 3 | Razbiti `electron/main.cjs` bez promjene ponašanja | 🟡 djelimično (env/window/PowerShell alati izvučeni; `core/ipc.cjs` odgođen — vidi `agent_reports/2026-07-05_split-main-cjs-faza3.md`) |
| 4 | Python backend skeleton (FastAPI, `/health`, `/tools`, `/tools/execute`) | ⬜ |
| 5 | Electron pokreće Python backend | ⬜ |
| 6 | Tool bridge Electron -> Python | ⬜ |
| 7 | SQLite storage i action log | ⬜ |
| 8 | Migracija memorije: notes/records/artifacts | ⬜ |
| 9 | Event bridge i artifact panel | ⬜ |
| 10 | Screenshot i active window u Pythonu | ⬜ |
| 11 | Permission system | ⬜ |
| 12 | Computer-use Python v1 (koordinate) | ⬜ |
| 13 | Computer-use Python v2 (UI element targeting) | ⬜ |
| 14 | Agent runtime u Pythonu | ⬜ |
| 15 | Prebaciti OpenAI/Exa/image pozive u Python | ⬜ |
| 16 | Deaktivacija legacy PowerShell toolova | ⬜ |
| 17 | Test suite i quality gate | ⬜ |
| 18 | Packaging plan | ⬜ |

## Redoslijed PR-ova

```text
PR 01 - Baseline and docs
PR 02 - Project agent rules update
PR 03 - Split electron/main.cjs into modules
PR 04 - Add Python backend skeleton
PR 05 - Electron starts Python backend
PR 06 - Tool bridge Electron -> Python
PR 07 - SQLite storage and action log
PR 08 - Migrate notes/records/artifacts
PR 09 - Event bridge and artifact panel integration
PR 10 - Python screenshot and UI inspect
PR 11 - Permission/risk/confirmation system
PR 12 - Python computer-use v1
PR 13 - Python computer-use v2 element targeting
PR 14 - Python agent runtime
PR 15 - Move OpenAI/Exa/image integrations to Python
PR 16 - Disable legacy PowerShell tools by default
PR 17 - Test suite and quality gate
PR 18 - Packaging
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

## Master prompt (za novi agent session)

```text
You are working on RileyJarvis Windows Hybrid.

Goal:
Migrate the current Windows-adapted Electron RileyJarvis prototype to a modular
hybrid architecture where React/Electron remains the UI shell and Python becomes
the backend brain for tools, storage, Windows automation, artifacts and agent runtime.

Hard architecture rules:
- React renderer is UI.
- Electron main process is only app shell, IPC bridge and Python process manager.
- Python backend owns agent runtime, tools, storage, automation and AI integrations.
- Do not add new business logic to electron/main.cjs.
- Do not remove legacy PowerShell tools until Python replacements are implemented and tested.
- No arbitrary shell execution tool exposed to the model.
- All tool calls must go through a tool registry and permission/risk layer.
- All tool calls must be logged.

Current task:
Implement only PHASE <NUMBER>: <PHASE NAME> from docs/RILEYJARVIS_WINDOWS_HYBRID_IMPLEMENTATION_PLAN.md.
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
```

## Definicija uspjeha

```text
- Electron/React UI radi kao prije.
- Electron automatski startuje Python backend.
- Python backend ima /health, /tools, /tools/execute.
- Toolovi su registrovani u Python registry-ju.
- Tool calls prolaze kroz permission/risk layer.
- Tool calls se loguju u SQLite.
- Artifacts dolaze iz Python backend-a i prikazuju se u React panelu.
- Screenshot/ui_inspect rade iz Python-a.
- Osnovni computer-use radi kroz Python na Notepad smoke testu.
- Legacy PowerShell tools su disabled by default.
- Agent runtime je u Python-u.
- App se može buildati bez rušenja.
```
