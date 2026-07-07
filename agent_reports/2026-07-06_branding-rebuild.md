# Korak 3 — GUI rebuild sa pravim brending asetima

## Datum

2026-07-06

## Izvor

`docs/PI_BRANDING_REBUILD_BRIEF.md` (Korak 3 u `PI_NEXT_STEPS.md`)

## Scope

Zamjena CSS-generisanih/prostih UI elemenata stvarnim brending asetima iz `assets/brending/`:
- PNG orb slike za svako VoiceState (umjesto CSS kruga sa slovom "R")
- SVG ikone iz `assets/brending/icons/` (umjesto lucide-react biblioteke)
- Logo SVG u top baru i sidebar-u
- Companion orb minijatura (ricky-orb-mini.png)
- Sakriven debug artifact panel po default-u
- Filtrirana "Zadnja aktivnost" (bez sirovih backend/system logova)

## Pripremni koraci

1. **Premješteni aseti**: `assets/brending/ricky_brending_assets/{logo,orb,icons}` → `assets/brending/{logo,orb,icons}`
2. **vite-plugin-svgr** instaliran (`npm i -D vite-plugin-svgr`) — omogućava `?react` import SVG-ova kao React komponente sa `currentColor` CSS kontrolom
3. **`vite.config.ts`** ažuriran: dodat `svgr()` plugin
4. **`src/vite-env.d.ts`**: dodat `/// <reference types="vite-plugin-svgr/client" />` za TypeScript podršku

## Izmijenjeni fajlovi

### Komponente

| Fajl | Promjena |
|---|---|
| `src/components/RickyOrb.tsx` | Zamijenjen CSS "R" krug sa PNG orb slikama: `orbIdle/orbListening/orbSpeaking/orbThinking/orbWarning/orbError/orbMain`; VoiceState → slika mapiranje; zadržan glow ring CSS za animacije |
| `src/components/Sidebar.tsx` | lucide-react ikone zamijenjene SVG importima iz `assets/brending/icons/navigation/icon-*.svg?react`; dodat logo SVG u brand header |
| `src/components/ConfirmationDialog.tsx` | lucide-react shield/check/x zamijenjeni sa `icon-warning/icon-confirm/icon-cancel.svg?react`; labeli prevedeni na sr-Latn |
| `src/components/CompanionOrb.tsx` | `CompanionFace` komponenta (CSS oči/usta) potpuno uklonjena; zamijenjena sa `<img src={orbMini} />` — `ricky-orb-mini.png`; sva IPC logika (voice state, menu, click handleri) očuvana |
| `src/App.tsx` | lucide-react Mic/MicOff/Square/X/Expand zamijenjeni SVG importima (`icon-microphone/icon-microphone-muted/icon-stop/icon-close/icon-realtime.svg?react`); `artifactVisible` default promijenjen na `false`; filtrirana "Zadnja aktivnost" (isključeni "Backend ready"/"Renderer ready" logovi); dodat logo SVG u top bar |

### Stilovi

| Fajl | Promjena |
|---|---|
| `src/styles.css` | `.ricky-orb` sekcija prepravljena za image-based orb (`.ricky-orb-img`, uklonjen `.ricky-orb-inner`/`.ricky-orb-r`); dodate `.top-bar-logo`, `.top-bar-brand`, `.top-bar-btn-icon`, `.idle-cta-icon`, `.sidebar-logo-icon`, `.sidebar-item-icon`, `.confirmation-icon-svg`, `.companion-orb-img` |

### Konfiguracija

| Fajl | Promjena |
|---|---|
| `vite.config.ts` | Dodat `svgr()` plugin |
| `src/vite-env.d.ts` | Dodat `vite-plugin-svgr/client` reference |

## Šta NIJE dirano

- **Confirmation Bridge logika** (`App.tsx` `handleApproveConfirmation` auto-retry, `realtime.ts` auto-propose) — netaknuta, ručno provjereno
- **Python backend** — nijedan fajl
- **`electron/main.cjs`** — netaknut
- **`electron-builder.yml`** — netaknut (Vite već bundluje PNG/SVG u `dist/assets/`, `electron-builder` ih pokupi kroz `dist/**/*`)

## Nove dev zavisnosti

- `vite-plugin-svgr` — SVG kao React komponente

## Verifikacija

```text
typecheck: prošao
build: prošao (8 PNG orb fajlova + SVG ikone bundlovani u dist/assets/)
pytest: 180 passed (bez regresije)
node --check: svi Electron moduli clean
smoke: prošao
```

## Acceptance criteria

- ✅ Veliki brendirani orb (PNG slike iz `assets/brending/orb/`) u centru idle ekrana
- ✅ Nema debug/artifact panela u glavnom layout-u (`artifactVisible` default=false)
- ✅ "Zadnja aktivnost" prikazuje smislene korisničke akcije, ne sirove backend/system logove
- ✅ Mikrofon CTA dugme postoji i klikljivo je (SVG ikona iz `icons/voice/icon-microphone.svg`)
- ✅ Sve ikonice iz `assets/brending/icons/`, nijedan emoji, nijedan lucide-react (osim `MonitorCog` za Computer Mode)
- ✅ Confirmation Bridge logika netaknuta i dalje radi
- ✅ Companion orb koristi `ricky-orb-mini.png` (bonus)