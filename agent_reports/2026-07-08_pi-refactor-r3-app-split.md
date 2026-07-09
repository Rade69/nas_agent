# Agent report — R3: src/App.tsx split (pi izvršilac)

**Datum pisanja:** 2026-07-09
**Ime fajla:** po briefu `docs/refactor_plan.md` sekcija "R3 — src/App.tsx split" (traži `2026-07-08_pi-refactor-r3-app-split.md`).
**Izvršilac:** pi · **Vlasnik plana:** Claude (verifikuje).
**Tip:** Mehanički refactor — JSX nepromijenjen (verbatim premještanje), ponašanje nepromijenjeno.

## Scope

Izdvojeno ~13 prezentacijskih pod-komponenti iz `src/App.tsx` (1115 → 503 ln) u
novi folder `src/components/pixel/`. `App.tsx` zadržava samo `App()`,
`getInitialMode()`, `isMiniWindow()`, `SYSTEM_NOISE_TITLES` + importe.

Ciljna struktura (postignuta, 8 fajlova):
```
src/components/pixel/
  types.ts               # RickyMode, ScreenState, DrawerState
  Previews.tsx           # ConfirmationPreview, ActivityDrawerPreview, PlansDrawerPreview, EmptyPreviewState, planStatusLabel
  DictationScreen.tsx    # DictationScreen
  TopBar.tsx             # TopBar
  Drawer.tsx             # Drawer
  MiniComputerWindow.tsx # MiniComputerWindow
  IdleScreen.tsx         # IdleScreen
  PixelMockupBoard.tsx    # PixelMockupBoard + MockupSection
```

`App.tsx` ostatak: `App()` + `getInitialMode` + `isMiniWindow` + `SYSTEM_NOISE_TITLES`.

## Koraci izvedeni (tačno po briefu R3)

Redoslijed: types prvo (da nema kružnog importa), pa leaf komponente jedna po
jedna, pa PixelMockupBoard zadnja. **`npm run typecheck` poslije SVAKOG koraka.**

### Korak 1 — `types.ts` ✓
Kreiran `pixel/types.ts` sa tri `type` deklaracije (RickyMode/ScreenState/DrawerState)
premještena iz App.tsx. U App.tsx dodat `import type { RickyMode, ScreenState,
DrawerState } from "./components/pixel/types";`. **typecheck čist.**

### Korak 2 — leaf komponente (svaka verbatim + export + importi)

Za svaku: premještena funkcija **verbatim** u novi fajl, na vrh dodati SAMO
importi koje ta komponenta koristi, funkciji dodan `export` (minimalna izmjena
nužna za move — ekvivalentno R1 rename-u), u App.tsx obrisana funkcija + dodat
`import { X } from "./components/pixel/X";`. **typecheck poslije svake.**

| Red | Fajl | Simbol(i) | Orig. linije (u 1115-ln App.tsx) | typecheck |
| --- | --- | --- | --- | --- |
| 2a | `Previews.tsx` | ConfirmationPreview, ActivityDrawerPreview, PlansDrawerPreview, EmptyPreviewState, planStatusLabel | 718–864 (contiguous) | ✓ |
| 2b | `DictationScreen.tsx` | DictationScreen | 882–940 | ✓ |
| 2c | `TopBar.tsx` | TopBar | 724–779 | ✓ |
| 2d | `Drawer.tsx` | Drawer | 827–857 | ✓ |
| 2e | `MiniComputerWindow.tsx` | MiniComputerWindow | 493–524 | ✓ |
| 2f | `IdleScreen.tsx` | IdleScreen | 702–802 | ✓ |

**Bug uhvaćen tokom rada (ispravljen u toku, NE u ponašanju):** kod MiniComputerWindow
prvi `sed` range (501–523) je promašio zadnju `}` (funkcija je 501–524) →
`error TS1005: '}' expected`. Popravljeno dodavanjem `}` (vraćena izgubljena
zagrada). Verbatim provjera potvrđuje funkciju kompletnu.

**Bug uhvaćen i ispravljen (App.tsx):** tokom brisanja Previews bloka, greškom
sam pokrenuo dodatni `sed -i '714,715d'` koji je obrisao `}` koja zatvara
`MockupSection`. Odmah vraćena edit-om sa jedinstvenim kontekstom. typecheck
potvrdio ispravljeno.

### Korak 3 — `PixelMockupBoard.tsx` (zadnja, + MockupSection) ✓
Funkcije PixelMockupBoard (orig 518–690) + MockupSection (orig 692–716)
premještene verbatim u jedan fajl. Importi: Sidebar/ActivityTimeline/PlansPanel
iz `../`, TopBar/IdleScreen/Drawer/DictationScreen/Previews iz `./`, tipovi iz
`./types` + `../../lib/realtime` + `../../vite-env`, `ReactNode` iz react.
**Bug uhvaćen:** zaboravljen `DictationScreen` import (PMB ga koristi u dictation
sekciji) → `TS2552: Cannot find name 'DictationScreen'`. Dodan import. typecheck čist.

### Korak 4 — finalno ✓
`npm run typecheck` — čisto. `npm run build` — `✓ built in 1.20s` (samo
pre-postojeći 500kB chunk warning, nevezan za R3).

### Korak 5 — grep provjera ✓
```
grep -nE "function (PixelMockupBoard|TopBar|IdleScreen|DictationScreen|Drawer|MiniComputerWindow|ConfirmationPreview)" src/App.tsx
→ PRAZNO
```
App.tsx sadrži SAMO: `SYSTEM_NOISE_TITLES`, `getInitialMode`, `isMiniWindow`,
`App` (export default).

## Verifikacija (acceptance criteria iz briefa)

| Kriterij | Očekivano | Dobiveno |
| --- | --- | --- |
| App.tsx sadrži samo App + getInitialMode + isMiniWindow + SYSTEM_NOISE_TITLES | grep prazan | ✓ grep prazan |
| App.tsx veličina | ~600–650 ln | **503 ln** (manje od procjene — App() je manji; cilj ispunjen: sve pod-komponente izdvojene) |
| `pixel/` ima 8 fajlova | 8 | ✓ (types.ts + 7 .tsx) |
| `npm run typecheck` | čisto | ✓ |
| `npm run build` | čisto | ✓ (samo 500kB warning) |
| Nijedan className/tekst/JSX izmijenjen | verbatim move | ✓ (diff dokaz za sve komponente) |

### Verbatim dokaz (byte-identičan JSX)
Za svaku izdvojenu komponentu urađen `diff` originalnih linija (iz snimljenog
`/tmp/r3/App.tsx.orig`, 1115 ln) vs novog fajla (sa skinutim `export ` prefixom
i header importima). Rezultat: **nula razlika u JSX/funkcijskom telu** za sve:

- **Previews.tsx** (5 funkcija, orig 718–864): `PREVIEWS VERBATIM ✓`
- **TopBar.tsx** (orig 866–921): `TOPBAR VERBATIM ✓`
- **DictationScreen.tsx** (orig 1025–1083): `DICTATION VERBATIM ✓`
- **Drawer.tsx** (orig 1085–1115): `DRAWER VERBATIM ✓`
- **MiniComputerWindow.tsx** (orig 493–516): `MINI VERBATIM ✓`
- **IdleScreen.tsx** (orig 923–1023): `IDLESCREEN VERBATIM ✓`
- **PixelMockupBoard.tsx** (orig 518–716, PMB+MockupSection): `PMB+MOCKUP VERBATIM ✓`

Jedina izmjena nad funkcijama: dodan `export` prefix (nužan da App.tsx može
importovati — ekvivalentno R1 rename-u, nije dodirnut JSX/logika/props/className/tekst).

### GitNexus detect_changes (info za Claude)
```
Changes: 3 files, 3 symbols
Affected processes: 0
Risk level: low
Changed symbols: GitNexus → AGENTS.md, ... → docs/DOCUMENT_ENGINE..., GitNexus → CLAUDE.md
```
Napomena: GitNexus nije detektovao App.tsx izmjene jer App.tsx nije bio u index
baseline-a pre-R3 (prethodno nekomitovan); detektovao je samo docs fajlove iz
drugih sesija (nisu moji). **Risk: low, 0 affected processes, nema HIGH/CRITICAL.**

## Fajlovi dirani (tačna lista)

- `src/App.tsx` — modifikovan (1115 → 503 ln): uklonjene pod-komponente,
  dodani `import type {...} from "./components/pixel/types"` + 7 `import { X }`
  linija za pixel komponente.
- `src/components/pixel/types.ts` — novi (6 ln).
- `src/components/pixel/Previews.tsx` — novi (158 ln).
- `src/components/pixel/DictationScreen.tsx` — novi (64 ln).
- `src/components/pixel/TopBar.tsx` — novi (65 ln).
- `src/components/pixel/Drawer.tsx` — novi (36 ln).
- `src/components/pixel/MiniComputerWindow.tsx` — novi (28 ln).
- `src/components/pixel/IdleScreen.tsx` — novi (115 ln).
- `src/components/pixel/PixelMockupBoard.tsx` — novi (214 ln).

**Nije dirano:** `src/styles/*`, postojeće `src/components/*` (Sidebar/RickyOrb/
ActivityTimeline/PlansPanel/ArtifactPanel/ConfirmationDialog — samo importovani,
ne modificirani), `electron/*`, `python_backend/*`, nijedan test.

## Potvrda: JSX nepromijenjen (verbatim move)

- Za svaku od 7 novih .tsx komponenti: `diff` originalnog bloka iz App.tsx vs
  novog fajla (sa skinutim `export`) = **nula razlika** u funkciji.
- Nijedan `className`, tekst, props, markup, atribut nije dirnut.
- Dodatak `export` ispred `function` je jedina izmjena nad simbolima — nužna
  da App.tsx uvozi komponentu (isto kao R1 preimenovanje `_` → javno ime).
- Importi dodani na vrh svakog novog fajla su SAMO oni koje komponenta stvarno
  koristi (ikone, tipovi, sibling komponente) — ekvivalentni importima u App.tsx,
  sa prilagođenim relativnim putanjama (`../../../assets/...` iz pixel/ vs
  `../assets/...` iz src/).

## Found issues (brief sekcija — NE popravljati u ovom koraku)

- App.tsx i dalje sadrži brojne ikon-importe koji su sad **unused** (npr.
  IconWarning, IconSuccess, IconBackend, IconChevronDown, IconChevronRight,
  IconScreenshot, IconOpenApp, IconCalendar, IconMicOff, IconMic, IconSend,
  IconStop, IconWave, IconLogoR, rikiAvatar) — jer su ih koristile samo
  izdvojene komponente. `noUnusedLocals` nije uključen u tsconfig, pa ne prave
  grešku. Ostavljeni su (uklanjanje bi bilo kozmetika izvan scope-a R3 i rizik
  greške ako neki ipak koristi App(); brief pravilo "Ne diraj App() logiku").
  **Otvoreno pitanje za Claude:** očistiti unused importe u zasebnom mini-PR-u?
- App.tsx (503 ln) je ispod briefove procjene ~600–650 ln — razlog: App()
  funkcija je manja nego procijenjeno; sve pod-komponente su izdvojene što je
  cilj R3.

## Commit

**Nije komitovan** — čeka Claude pregled (brief pravilo 5).

## Potrebna korisnička potvrda (Claude R3 protokol)

1. `npm run typecheck` + `npm run build` sam → čisto (ja potvrdio: oba čista).
2. **Diff pregled:** za 2–3 izdvojene komponente uporediti JSX sa originalom
   (snimljen u `/tmp/r3/App.tsx.orig`) — ja sam uradio verbatim diff za sve 7,
   nula razlika u JSX. Claude može nezavisno potvrditi poredbom sa `git show`
   (App.tsx pre-R3 nije komitovan, pa je `/tmp/r3/App.tsx.orig` referenca —
   ili Claude može tražiti od korisnika pre-R3 stanje).
3. `gitnexus detect_changes` — low risk, 0 affected processes (vidi gore).
4. Preporučiti korisniku **vizuelni smoke** (pokrenuti app, provjeriti da
   idle/dictation/drawers/mini-window/mockup-board izgledaju identično) jer UI
   nema automatske testove — jedino stvarno osiguranje vizuelne identičnosti je
   verbatim premještanje + build prolazi.

Otvorena pitanja za Claude:
- Da li očistiti unused icon-importe iz App.tsx (zasebni mini-PR)?
- Da li je 503 ln (ispod procjene 600–650) prihvatljivo, ili se očekivalo da
  App() bude veći (možda je neka komponenta propuštena?) — grep potvrđuje da
  su SVE navedene pod-komponente izdvojene i samo App/getInitialMode/
  isMiniWindow/SYSTEM_NOISE_TITLES ostaju.
