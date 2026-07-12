# Brief za pi — retroaktivno dodavanje file header komentara

**Za:** pi · **Od:** Claude
**Povod:** Korisnik je tražio da svaki fajl na vrhu ima kratak komentar/docstring
koji objašnjava šta fajl radi i koji problem rješava — cilj je da se
skeniranjem vrha fajla odluči da li je to pravo mjesto za traženi podatak, bez
čitanja cijelog sadržaja. Pravilo je sad u `CLAUDE.md` ("Rad po fazama"
sekcija, "File header komentar" stavka) i važi ubuduće za nove/značajno
mijenjane fajlove. Ovaj brief je jednokratni retroaktivni prolaz kroz sve
postojeće fajlove koji header još nemaju.

**Čisto aditivan zadatak — dodaješ komentar, ništa drugo ne mijenjaš.** Ne
diraj logiku, importe, formatiranje koda, ne "popravljaj" stvari na koje
naiđeš usput. Ako primijetiš pravi bug ili problem dok čitaš neki fajl da bi
napisao header, NE popravljaj ga — zabilježi ga kao zaseban nalaz u
izvještaju, van scope-a ovog zadatka.

---

## Format po tipu fajla

### Python (`.py`)

Standardni modul docstring, prva stvar u fajlu (ispred `from __future__ import
annotations` ako postoji — docstring uvijek ide prvi, to je Python pravilo, ne
stilski izbor):

```python
"""Kratak opis šta fajl radi i koji problem rješava (1 rečenica).

Opciono: 1-3 dodatne rečenice — kako se uklapa u ostatak sistema, netrivijalan
dizajn izbor, veza sa drugim modulima — SAMO ako to nije očigledno iz naziva
fajla/putanje/prve rečenice. Ne ponavljaj ono što ime fajla već govori.
"""
from __future__ import annotations
```

Referentni primjeri koji već postoje u repo-u (isti nivo detalja, ne duže):
`python_backend/app/agent/model_client.py`, `python_backend/app/core/security_self_test.py`,
`python_backend/app/core/path_sandbox.py`.

**Izuzetak:** `__init__.py` fajlovi koji su prazni (0 linija koda, samo
marker prazne fascikle) se preskaču — nema šta da se opiše. Provjeri prvo da
li je fajl stvarno prazan (`wc -l`) prije nego ga preskočiš; ako ima sadržaj,
tretiraj ga isto kao svaki drugi `.py` fajl.

### TypeScript / TSX (`.ts`, `.tsx`)

`/** ... */` blok, prva stvar u fajlu, ispred svih importa:

```tsx
/** Kratak opis šta fajl radi i koji problem rješava (1 rečenica).
 *  Opciono: dodatne rečenice pod istim uslovom kao gore. */
import { useState } from "react";
```

Referentni primjeri koji već postoje u repo-u: `src/components/pixel/DictationScreen.tsx`,
`src/components/pixel/PixelMockupBoard.tsx`, `src/components/pixel/SettingsPanel.tsx`,
`src/components/pixel/IdleScreen.tsx` — isti nivo detalja i ton.

### Electron (`.cjs`)

`/** ... */` blok (isti oblik kao TS) ili `//` blok od 2-5 linija — koristi
šta god je konzistentnije sa susjednim fajlovima u istom direktorijumu koji
već imaju header (`electron/core/*.cjs`, `electron/ipc_handlers/*.cjs` —
provjeri par postojećih prije nego biraš stil za novi).

---

## Šta je dobar header, šta nije

**Dobro** (specifično, kaže NEŠTO što se ne vidi iz naziva/putanje):
```python
"""Auth dependency enforced on every backend route (app.core.errors.AppError
on failure). Electron always sets RICKY_LOCAL_TOKEN before spawning this
process; the dev-without-Electron path auto-generates its own token instead
of failing open — see app/core/config.py's _resolve_local_token()."""
```

**Loše** (samo parafrazira naziv fajla, nula nove informacije):
```python
"""This is the auth module. It handles authentication."""
```

Ako fajl radi tačno ono što mu ime kaže i nema netrivijalnih veza sa ostatkom
sistema (npr. `app/schemas/text.py` — Pydantic model za text rewrite request),
1 kratka rečenica je dovoljna i tačna — ne izmišljaj dodatni sadržaj da bi
header izgledao "vrijedniji".

---

## Spisak fajlova (91 ukupno, grupisano po oblasti)

### Python backend — `python_backend/app/` (53 fajla, `__init__.py` prazni fajlovi izostavljeni)

```
agent/cancellation.py
agent/conversation_state.py
agent/permission_engine.py
agent/tool_catalog/phase11.py
agent/tool_catalog/phase13.py
agent/tool_catalog/phase14.py
agent/tool_executor.py
agent/tool_registry.py
api/agent.py
api/confirmations.py
api/events.py
api/health.py
api/plans.py
api/realtime.py
api/screenshots.py
api/security.py
api/settings.py
api/text.py
api/tools.py
core/auth.py
core/config.py
core/errors.py
core/logging.py
core/payload_hash.py
main.py
schemas/agent.py
schemas/common.py
schemas/confirmation.py
schemas/plan.py
schemas/realtime.py
schemas/screenshot.py
schemas/settings.py
schemas/text.py
schemas/tool.py
services/action_log.py
services/artifact_service.py
services/confirmation_service.py
services/event_bus.py
services/notes_service.py
services/plan_service.py
services/records_service.py
services/screenshot_service.py
services/settings_service.py
storage/db.py
storage/repositories/agent_repo.py
storage/repositories/artifact_repo.py
storage/repositories/confirmation_repo.py
storage/repositories/event_repo.py
storage/repositories/notes_repo.py
storage/repositories/plan_repo.py
storage/repositories/records_repo.py
storage/repositories/screenshot_repo.py
storage/repositories/settings_repo.py
storage/repositories/tool_run_repo.py
```

(Sve putanje relativne na `python_backend/app/`.)

### Frontend — `src/` (20 fajlova)

```
App.tsx
components/ActivityTimeline.tsx
components/ArtifactPanel.tsx
components/BottomVoiceBar.tsx
components/CompanionOrb.tsx
components/ConfirmationDialog.tsx
components/PlansPanel.tsx
components/RickyFace.tsx
components/RickyOrb.tsx
components/Sidebar.tsx
components/VoiceTopBar.tsx
lib/activityIcons.tsx
lib/cyrillicToLatin.ts
lib/realtime.ts
lib/realtimeEventHelpers.ts
lib/realtimeEventRouter.ts
lib/realtimeMouthShape.ts
lib/realtimeTypes.ts
lib/voiceState.ts
main.tsx
```

(Sve putanje relativne na `src/`.)

### Electron — `electron/` (14 fajlova)

```
core/companionWindow.cjs
core/env.cjs
core/securitySelfTest.cjs
core/window.cjs
main.cjs
services/pythonProcess.cjs
tools_legacy/powershell/computerClick.cjs
tools_legacy/powershell/computerOpenApp.cjs
tools_legacy/powershell/computerPressKey.cjs
tools_legacy/powershell/computerScroll.cjs
tools_legacy/powershell/computerTypeText.cjs
tools_legacy/powershell/runPowerShell.cjs
tools_legacy/powershell/screenSnapshot.cjs
tools_legacy/powershell/uiInspect.cjs
```

(Sve putanje relativne na `electron/`.)

**Napomena o `electron/main.cjs`:** ovo je poznat "collision" fajl (CLAUDE.md
"Multi-agent higijena") koji se često mijenja. Pročitaj ga svježe (`cat`, ne
keširan prikaz) neposredno prije nego dodaš header, i drži izmjenu striktno
na dodavanje 2-5 linija na vrhu — ništa drugo u tom fajlu.

---

## Šta NE dirati

- Bilo koji fajl van gornja tri spiska (uklj. `tests/`, `.d.ts` fajlove,
  `*.json`, `*.md`) — van obima ovog zadatka.
- Prazni `__init__.py` fajlovi (vidi izuzetak gore).
- Logika, importi, formatiranje, postojeći komentari unutar fajla (osim ako
  fajl već ima header koji treba samo premjestiti na pravo mjesto — malo
  vjerovatno u ovoj listi jer je filtrirana da isključi fajlove sa header-om).

## Acceptance criteria

- `npm run typecheck` i `npm run build` — čisto (ove izmjene su komentari,
  ne bi smjele uticati na TS compile, ali provjeri).
- `node --check` na svaki dotaknuti `.cjs` fajl.
- `cd python_backend && python -m pytest -q` — isti broj testova prolazi kao
  prije (251) — komentari ne smiju promijeniti ponašanje.
- Git diff za svaki fajl treba biti ISKLJUČIVO dodavanje komentara na vrhu —
  nula promjena u ostatku fajla. Provjeri sa `git diff --stat` da je svaki
  dotaknuti fajl +N/-0 (osim ako je docstring ubačen ispred postojećeg
  `from __future__ import annotations`, gdje će diff pokazati pomjeranje te
  linije za par redova niže — i dalje bez izmjene sadržaja).
- Agent report: `agent_reports/2026-07-12_file-header-comments.md`,
  standardni CLAUDE.md obrazac. U izvještaju napravi i kratku listu bilo kojih
  fajlova koje si preskočio i zašto (npr. dodatni prazni `__init__.py` koji
  nisam predvidio u spisku iznad).

Kad završiš, javi — Claude verifikuje (git diff pregled, build, GitNexus
impact) prije commita. Obzirom na broj fajlova (91), OK je da uradiš ovo u
više manjih commit-nih grupa (npr. po oblasti: Python / frontend / Electron)
umjesto jednog ogromnog diff-a — ali svejedno mi javi tek kad je SVE gotovo,
ne parcijalno.
