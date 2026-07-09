# Refactor plan — agent-friendly struktura (prema docs/AGENT_FRIENDLY_CODE.md)

**Datum:** 2026-07-08
**Vlasnik plana:** Claude (planira + verifikuje). **Izvršilac:** pi (mehanički rad pod Claude kontrolom).
**Protokol:** docs/AGENT_FRIENDLY_CODE.md §8. Ponašanje se NE mijenja; testovi zeleni poslije svakog koraka; jedan modul = jedan "dio" = jedan Claude pregled.

---

## Inventar (fajlovi > 500 linija logike)

| Fajl | Linije | Status | Redoslijed |
|---|---|---|---|
| `electron/main.cjs` | 1922 | 🔒 Codex nekomitovan | R2 (poslije Codexa) |
| `src/App.tsx` | 1115 | 🔒 Codex nekomitovan/aktivan | R3 (poslije Codexa) |
| `python_backend/app/agent/tool_registry.py` | 637→78 | ✅ **R1 ZAVRŠEN** (Claude verifikovao) | ✔ |
| `src/lib/realtime.ts` | 534 | 🟡 tik preko | R4 (opciono) |

CSS je već cijepan (`src/styles/00–14`) — model se poštuje. Ne dirati.

## Pravila koja pi MORA poštovati (sve faze)
1. **Ponašanje nepromijenjeno.** Kod se PREMJEŠTA verbatim. Ne mijenjati imena alata, sheme, risk nivoe, flagove, logiku. Refaktor ≠ popravka.
2. **Ne dirati tuđe fajlove.** Samo fajlove navedene u tekućem R-koraku. NIKAD `electron/*`, `src/*` (Codex) u R1.
3. **Testovi zeleni poslije svakog koraka.** `cd python_backend && python -m pytest -q` mora ostati **199 passed**. Ako padne — STANI i prijavi, NE "popravljaj" mijenjanjem ponašanja.
4. **Bez mrtvog koda / shim-ova na kraju.** Privremeni re-export shim se briše prije kraja koraka.
5. **Ne commitovati dok Claude ne pregleda** (osim na zasebnoj grani — vidi dolje). Kad završiš R-korak, javi; Claude verifikuje pa daje zeleno za sljedeći.
6. Nađeni bugovi usput → NE popravljati; upisati u sekciju "Found issues" ovog fajla.

---

## R1 — `tool_registry.py` split (IZVODI pi, SADA)

### Cilj (tačna završna struktura)
```
python_backend/app/agent/tool_registry.py      # ostaje: ToolHandler, RegisteredTool, ToolRegistry, echo_tool, create_default_registry (~90 ln)
python_backend/app/agent/tool_catalog/
  __init__.py                                   # javni API (re-export 3 register fn)
  phase11.py                                    # register_phase11_tools(registry, services)
  phase13.py                                    # register_phase13_tools(registry)
  phase14.py                                    # register_phase14_tools(registry)
```

### Zašto ovako
`tool_registry.py` sad drži i mehanizam (ToolRegistry klasa), i katalog definicija (3 velike `_register_phaseN` funkcije). Katalog je zaseban od mehanizma. Poslije: `tool_registry.py` = registar + orkestracija; `tool_catalog/` = definicije po fazama. Vanjski uvoz `from app.agent.tool_registry import create_default_registry` (koristi ga `app/main.py`) **ostaje nepromijenjen**.

### Koraci (tačno ovim redom, pytest poslije svakog)
1. Kreiraj folder `python_backend/app/agent/tool_catalog/` sa praznim `__init__.py`.
2. **`phase11.py`:** premjesti CIJELU funkciju `_register_phase11_tools` iz `tool_registry.py` **verbatim**, samo je preimenuj u `register_phase11_tools` (ukloni vodeći `_`). Njeni `from app.tools...import make_handlers` importi su UNUTAR funkcije — ostaju tu. Na vrh fajla dodaj: `from __future__ import annotations`, `from typing import Any`, `from app.schemas.tool import ToolDefinition`, i 1–3 linije docstring ("FAZA 11 tool catalog: memory/artifact/system/web/image tool definitions and registration."). Pokreni `pytest -q` (još se poziva iz tool_registry — vidi korak 5; do tada pytest može ostati zelen jer stari kod još stoji — NE brisati stari dok korak 5 ne prespoji).
   > Napomena: da testovi ostanu zeleni tokom migracije, radi ovako: PRVO dodaj nove module (koraci 1–4), PA u koraku 5 prespoji `tool_registry.py` na njih i obriši stare funkcije. Tako nema međustanja gdje je funkcija nestala a još se zove.
3. **`phase13.py`:** isto za `_register_phase13_tools` → `register_phase13_tools`. Dodaj na vrh: `from __future__ import annotations`, `from typing import Any`, `from app.schemas.tool import ToolDefinition`, `from app.agent.permission_engine import DEFAULT_BLOCKED_APPS`, docstring ("FAZA 13 tool catalog: coordinate-based computer-use tools.").
4. **`phase14.py`:** isto za `_register_phase14_tools` → `register_phase14_tools`. Vrh: `from __future__ import annotations`, `from typing import Any`, `from app.schemas.tool import ToolDefinition`, `from app.agent.permission_engine import DEFAULT_BLOCKED_APPS`, docstring ("FAZA 14 tool catalog: UIA element-targeting tools.").
5. **`__init__.py`:**
   ```python
   """Public API for the tool catalog — per-phase tool definitions/registration."""
   from .phase11 import register_phase11_tools
   from .phase13 import register_phase13_tools
   from .phase14 import register_phase14_tools

   __all__ = ["register_phase11_tools", "register_phase13_tools", "register_phase14_tools"]
   ```
6. **`tool_registry.py` prespoji:** obriši tri `_register_phaseN_tools` funkcije; dodaj na vrh `from app.agent.tool_catalog import register_phase11_tools, register_phase13_tools, register_phase14_tools`; u `create_default_registry` zamijeni pozive `_register_phase11_tools(...)` → `register_phase11_tools(...)` (i 13/14). Zadrži `ToolHandler`, `RegisteredTool`, `ToolRegistry`, `echo_tool`, `create_default_registry` netaknute.
7. `grep -rn "_register_phase" python_backend/` — mora biti PRAZNO (nijedan poziv na stara privatna imena).
8. `cd python_backend && python -m pytest -q` → **199 passed**.

### Acceptance (pi provjeri prije nego javi)
- `tool_registry.py` < 120 linija.
- `tool_catalog/` ima `__init__.py` + `phase11/13/14.py`, svaki sa jednom `register_phaseNN_tools`.
- `grep "_register_phase"` prazan.
- `pytest -q` = **199 passed** (identično baseline-u).
- Nijedna tool definicija (name/schema/risk/flags) nije mijenjana — dokaz je da testovi prolaze bez izmjene.

### Izvještaj pi (kad završi)
`agent_reports/2026-07-08_pi-refactor-r1-tool-registry.md` sa: koraci, `pytest` izlaz (199), potvrda "ponašanje nepromijenjeno", i lista tačnih fajlova diranih.

---

## R3 — `src/App.tsx` split (IZVODI pi, poslije R1)

### Kontekst i mreža
`App.tsx` je 1115 linija: stateful container `App()` (~437 ln) + ~13 prezentacijskih pod-komponenti/helpera nagurano u isti fajl (Codex pixel rebuild). **Safety net: `tsc` (typecheck) + `vite build`.** NEMA unit testova (UI), pa se oslanjamo na (a) `tsc` hvata svaku mehaničku grešku (fali import, tip ne štima) i (b) **verbatim premještanje JSX-a** — komponenta se PREMJEŠTA, JSX se NE mijenja. Claude radi diff pregled da potvrdi čist move.

### Cilj (tačna završna struktura)
```text
src/components/pixel/
  types.ts               # RickyMode, ScreenState, DrawerState (premješteni iz App.tsx)
  PixelMockupBoard.tsx   # PixelMockupBoard + MockupSection
  MiniComputerWindow.tsx # MiniComputerWindow
  TopBar.tsx             # TopBar
  IdleScreen.tsx         # IdleScreen
  DictationScreen.tsx    # DictationScreen
  Drawer.tsx             # Drawer
  Previews.tsx           # ConfirmationPreview + ActivityDrawerPreview + PlansDrawerPreview + EmptyPreviewState + planStatusLabel
```
`App.tsx` ZADRŽAVA: `App()`, `getInitialMode()`, `isMiniWindow()`, `SYSTEM_NOISE_TITLES`, i importuje pixel komponente iz `./components/pixel/...`.

### Zašto `types.ts` prvo
`RickyMode`/`ScreenState`/`DrawerState` koriste I `App.tsx` I izdvojene komponente (props). Ako ostanu u `App.tsx` a komponente ih importuju → kružni import (`App → komponenta → App`). Zato idu u `pixel/types.ts` koji oba importuju — nema ciklusa. (`App.tsx` importuje komponente; komponente importuju SAMO tipove iz `types.ts`, nikad iz `App.tsx`.)

### Koraci (tsc + build poslije SVAKOG, ne na kraju)
1. Kreiraj `src/components/pixel/`. **`types.ts`:** premjesti tri `type` deklaracije (RickyMode/ScreenState/DrawerState) iz `App.tsx`; u `App.tsx` dodaj `import type { RickyMode, ScreenState, DrawerState } from "./components/pixel/types";`. `npm run typecheck`.
2. Izdvoji **leaf** komponente jednu po jednu (ovim redom): `Previews.tsx` (5 simbola: ConfirmationPreview, ActivityDrawerPreview, PlansDrawerPreview, EmptyPreviewState, planStatusLabel) → `DictationScreen.tsx` → `TopBar.tsx` → `Drawer.tsx` → `MiniComputerWindow.tsx` → `IdleScreen.tsx`. Za svaku: premjesti funkciju **verbatim** u novi fajl; dodaj na vrh SAMO importe koje ta komponenta koristi (ikone iz `../../assets/...`, komponente iz `../` npr. `RickyOrb`/`Sidebar`/`ActivityTimeline`/`PlansPanel`, `categoryForActivity`/`voiceStateLabel`/`createActivityEvent` iz `../../lib/...`, tipove iz `./types`, tipove `ActivityEvent`/`Plan`/`VoiceState` iz odgovarajućih modula kao u App.tsx); u `App.tsx` dodaj `import { X } from "./components/pixel/X";`. **`npm run typecheck` poslije svake** — ako javi fali-import, dodaj ga (tsc te tačno vodi).
3. Zadnja: `PixelMockupBoard.tsx` (+ `MockupSection`) — importuje svu djecu iz sibling fajlova (`./TopBar`, `./IdleScreen`, `./DictationScreen`, `./Drawer`, `./Previews`, `./MiniComputerWindow`) + `Sidebar`/`ActivityTimeline`/`PlansPanel` iz `../`. `npm run typecheck`.
4. Finalno: `npm run typecheck` **i** `npm run build` — oba moraju proći čisto (osim pre-postojećeg 500kB chunk warninga).
5. `grep -n "function PixelMockupBoard\|function TopBar\|function IdleScreen\|function DictationScreen\|function Drawer\|function MiniComputerWindow\|function ConfirmationPreview" src/App.tsx` → **prazno** (sve izdvojeno; ostaje samo `function App`, `getInitialMode`, `isMiniWindow`).

### Pravila specifična za R3
- **JSX se NE mijenja ni znak.** Premještaš funkciju, ne prepravljaš markup, className, tekst, props. Refaktor ≠ redizajn.
- Ne diraj `App()` logiku (state, useEffect, handlere) — samo zamijeni inline definicije komponenti importima.
- Ne diraj `src/styles/*`, `src/components/*` postojeće (Sidebar/RickyOrb/itd.), `electron/*`, Python. Samo `App.tsx` + novi `pixel/` fajlovi.
- Ako `tsc` javi grešku koju ne možeš riješiti čistim dodavanjem importa (npr. traži logičku izmjenu) → STANI i prijavi. Ne "popravljaj" mijenjanjem koda.

### Acceptance (pi provjeri prije nego javi)
- `App.tsx` sadrži SAMO `App` + `getInitialMode` + `isMiniWindow` + `SYSTEM_NOISE_TITLES` (grep iz koraka 5 prazan); ~600–650 linija.
- `src/components/pixel/` ima 8 fajlova iz cilja.
- `npm run typecheck` čist, `npm run build` čist.
- Nijedan `className`/tekst/JSX nije izmijenjen (dokaz: diff su čisti move-ovi).

### Izvještaj pi
`agent_reports/2026-07-08_pi-refactor-r3-app-split.md`: koraci, koja komponenta u koji fajl, `typecheck`+`build` izlaz, potvrda "JSX nepromijenjen (verbatim move)", tačna lista diranih fajlova. NE commitovati — čeka Claude pregled.

### Claude R3 pregled (dopuna opšteg protokola)
- `npm run typecheck` + `npm run build` sam → čisto.
- **Diff pregled:** za 2–3 izdvojene komponente uporediti JSX sa `git show HEAD:src/App.tsx` — mora biti byte-identičan markup (samo lokacija se promijenila).
- `gitnexus detect_changes` — pogođeni samo App/pixel simboli.
- Preporučiti korisniku **vizuelni smoke** (pokrenuti app, provjeriti da idle/dictation/drawers/mini-window izgledaju isto) jer UI nema automatske testove.

---

## Protokol Claude pregleda (poslije svakog R-koraka)
1. Pročitam diff + nove fajlove.
2. Pokrenem `pytest -q` sam → mora 199.
3. Spot-check: par tool definicija (npr. `computer_type_text` schema/risk) byte-identično prije/poslije.
4. `gitnexus detect_changes` — potvrda da su pogođeni samo očekivani simboli (premještanje, ne izmjena logike).
5. Ako čisto → zeleno za sljedeći R-korak + ažuriram status ovdje. Ako ne → pošaljem pi precizne korekcije.

## Sekvenca poslije R1
- **R2 `main.cjs`** — tek kad Codex commituje. NEMA unit testova → Claude prvo piše karakterizacione/smoke provjere ILI radi sam. NE delegirati slijepo na pi.
- **R3 `App.tsx`** — kad Codex završi avatar kozmetiku i commituje. Izdvojiti pixel pod-komponente (PixelMockupBoard, TopBar, IdleScreen, DictationScreen, *Preview, Drawer) u zasebne fajlove.
- **R4 `realtime.ts`** — opciono, nisko.

## Found issues (popuniti usput, popravljati ODVOJENO)
- (prazno)
