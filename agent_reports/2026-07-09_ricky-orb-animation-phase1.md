# Agent report — Ricky orb animacija (CSS state-driven, Faza 1)

**Datum:** 2026-07-09

## Scope

Implementacija prve verzije Ricky orb animacije po `docs/RICKY_ORB_ANIMATION_PLAN.md`:
CSS-only, state-driven triple-ring sistem bez Lottie/WebGL/canvas-a. Izmijenjena su
samo dva fajla:

- `src/components/RickyOrb.tsx` (rewrite komponente)
- `src/styles.css` (orb CSS blok + keyframes + reduced-motion; companion reduced-motion)

## GitNexus impact

GitNexus MCP alati nisu bili dostupni kao tool-ovi u ovoj sesiji (dostupni su samo
read/bash/edit/write). CLAUDE.md fallback pravilo nalaže ručnu blast-radius analizu,
što je urađeno i prijavljeno korisniku prije izmjena:

- **`RickyOrb`** — 1 pozivaoc: `src/App.tsx:1028` (`<RickyOrb voiceState={voiceState} />`
  u `pixel-hero` idle ekranu). Zadržan `voiceState` prop → **pozivaoc se ne lomi**.
  Rizik: NISKI→SREDNJI.
- CSS override-i u `styles.css` (`.pixel-hero .ricky-orb-ring` l. 3528,
  `.pixel-window-idle .pixel-hero .ricky-orb` l. 4406/5050) — ažurirani na novi
  `--outer` selektor da ostanu važeći.
- `CompanionOrb.tsx` — nije restukturiran (sopstveni mini window + meni); samo mu je
  u CSS-u dodata reduced-motion podrška.

Nakon izmjena pokrenut `npx gitnexus detect-changes --repo nas_agent`:
**Risk level: medium.** Detect-changes prijavljuje i simbole koje ja NISAM dirao
(`createWindow`, `setWindowMode`, `handleToolsExecute` u `electron/*`, `refreshPlans`
u `App.tsx`) — to su prethodne nekomitovane izmjene iz drugih sesija, prisutne u
`git status` prije mog zadatka. Moje izmjene ograničene na `RickyOrb` + `styles.css`
(CSS nije indeksiran kao simbol, ali `RickyOrb` execution flow `PixelMockupBoard →
RickyOrb` je očekivano pogođen). Nema HIGH/CRITICAL upozorenja.

## Šta je urađeno

1. **`src/components/RickyOrb.tsx`** — rewrite:
   - Novi `RickyOrbState` tip: `idle | listening | thinking | speaking | warning | error | muted`.
   - Novi `mapVoiceStateToOrbState(voiceState)` helper — single source of truth za
     mapiranje (plan §12), exportovan za reuse. Mapira 9 VoiceState vrijednosti u 7
     vizuelnih stanja (`transcribing`→`listening`, `interrupted`/`waiting_confirmation`
     →`warning`).
   - Komponenta sada renderuje **3 ringa** (`outer / middle / inner`) + image.
   - Zadržan `voiceState` prop (backward kompatibilno) + dodat `size="floating"` i
     `className` prop.
   - Zadržan PNG-swap po stanju (već radio; plan §2 dozvoljava kao jače vizuelno
     razlikovanje).
   - Zadržan i stari raw `voiceState` class radi postojećih CSS override-a.

2. **`src/styles.css`** — tri izmjene:
   - Glavni `.ricky-orb*` blok zamijenjen triple-ring sistemom sa per-state
     animacijama: idle (breathe + soft float), listening (brži cyan pulse), thinking
     (spori orbit + pulse), speaking (multi-tempo wave + image pulse), warning (miran
     orange, ne preuzima fokus), error (kratki 3× pulse, ne beskonačan), muted
     (grayscale, bez animacija).
   - 10 novih `ricky-*` keyframe-ova; stari `orb-pulse-*` / `orb-shake` keyframes
     uklonjeni (nisu više referencirani).
   - **`prefers-reduced-motion`** media query za `.ricky-orb` (plan §9 — obavezno
     po acceptance criteria) i dodat isti blok za `.companion-*` (mini window).
   - `.pixel-hero .ricky-orb-ring` override ažuriran na `--outer` selektor.

## Zašto je urađeno

`docs/RICKY_ORB_ANIMATION_PLAN.md` traži CSS-only state-driven animaciju kao prvu
verziju (plan §1, §16), bez Lottie/WebGL/canvas-a. Postojeća `RickyOrb` komponenta
imala je samo jedan ring sa minimalnim animacijama. Codexova analiza potvrdila je da
repo već ima `RickyOrb.tsx`, orb assete i `voiceState` kroz `App.tsx`, te da je
osnovna verzija izvodiva u jednoj maloj fazi (2–4h). Ovaj zadatak implementira baš
tu malu fazu, u skladu sa AGENTS.md pravilom "Prefer small PRs".

## Kako je urađeno

- `read` alat za pregled postojećih `RickyOrb.tsx`, `CompanionOrb.tsx`, `voiceState.ts`,
  `App.tsx` call site-a i postojećeg CSS-a.
- `bash` (`grep`) za blast-radius: pronadjen 1 pozivaoc + 3 CSS override lokacije.
- `write` za rewrite `RickyOrb.tsx`; `edit` za tri ciljane izmjene u `styles.css`.
- Verifikacija: `npx tsc --noEmit` (čisto), grep keyframe konzistencije (svih 10
  referenciranih `ricky-*` keyframe-ova definisano), grep zaostalih referenci na stari
  `ricky-orb-ring` selektor (nema).

## Šta nije dirano

- `electron/main.cjs`, `electron/core/window.cjs`, `electron/preload.cjs`,
  `src/App.tsx`, `src/vite-env.d.ts` — ovi fajlovi su bili modified u `git status`
  prije mog zadatka, ali nisam ih ja mijenjao niti komitujem (tuđe nekomitovane
  izmjene iz drugih sesija).
- `CompanionOrb.tsx` logika — nije restukturiran (riziko za companion prozor); samo
  mu je u CSS-u dodata reduced-motion podrška.
- Nije kreiran odvojeni `RickyOrb.css` niti `src/companion/` dir — poštovana postojeća
  repo konvencija (jedan `styles.css`, komponente u `src/components/`).
- Nije dodato Lottie/WebGL/canvas (plan §1 i §14 zabranjuju za prvu verziju).

## Verifikacija

- `npm run typecheck` (`tsc --noEmit`) — čisto, bez greški. ✓
- Svi referencirani keyframe-ovi definisani (10/10). ✓
- Nema zaostalih referenci na stari `ricky-orb-ring` selektor. ✓
- `gitnexus detect-changes --repo nas_agent` — risk level medium, nema HIGH/CRITICAL. ✓
- Ručna vizuelna provjera u Electron GUI-ju nije pokretana iz agent sesije (nije
  pouzdano bez ljudske interakcije) — ostavljeno korisniku.

## Rizici / ograničenja

- **Performanse na Electronu** (Codexova napomena): glow/filter animacije na 3 ringa
  + image mogu opteretiti renderer. Ako padnu, plan §13 nudi fallback: smanjiti
  ringove sa 3 na 2, ugasiti inner ring animation.
- **Asset veličina**: `ricky-orb-main.png` je 1.3 MB (vs `ricky-orb-main.webp` 68 KB).
  Prelazak na `.webp` preporučen u sledećoj fazi.
- **CompanionOrb** i dalje ima sopstveni glow sistem (`companion-glow-pulse`) koji nije
  integrisan sa novim `RickyOrbState` modelom — to je svjesno odloženo radi malog PR-a.
- **Ručno testiranje animacija** nije urađeno — boje/tempo su uzeti direktno iz plana,
  eventualno pixel-fino podešavanje ostaje za sledeću fazu.

## Potreban follow-up

- Faza 2 (polirana verzija): fino podešavanje timinga/boja na stvarnom Electron
  renderu; razmatranje prelaska orb asseta na `.webp`.
- Integrisati `CompanionOrb` sa `mapVoiceStateToOrbState()` ako se želi konzistentan
  state model između main i mini window-a.
- Napredna Siri-like organska animacija (Canvas/Lottie) — tek kad GUI bude stabilan
  (plan §16), van scope-a ove faze.

## Potrebna korisnička potvrda

Ručna provjera da `npm run dev` prikazuje novu triple-ring animaciju i da se
`prefers-reduced-motion` ponaša kad se uključi u OS postavkama — agent nije pokretao
Electron GUI u ovoj sesiji.
