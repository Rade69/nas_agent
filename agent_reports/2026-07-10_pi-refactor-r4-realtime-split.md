# R4 — `src/lib/realtime.ts` split (pi refactor izvještaj)

**Datum:** 2026-07-10
**Izvršilac:** pi
**Plan:** `docs/refactor_plan.md` § R4
**Status:** ✅ ZAVRŠEN — čeka Claude pregled

---

## Sažetak

`src/lib/realtime.ts` (535 ln) je splitovan u 4 fajla:
- `realtime.ts` ostaje na istoj putanji — sadrži `RickyRealtimeClient` klasu, `newEntry`, konstante i re-exporte
- `realtimeTypes.ts` — svi tipovi
- `realtimeMouthShape.ts` — pure-function helperi za viseme/mouth-shape matematiku
- `realtimeEventHelpers.ts` — pure-function helperi za event parsing/sanitizaciju

**Metodologija:** "dodaj pa prespoji" (kao R1) — prvo kreirani svi novi moduli, pa `realtime.ts` prepovezan. Tijela metoda klase `RickyRealtimeClient` su **verbatim**, samo su import linije na vrhu fajla promijenjene.

---

## Koraci

### Korak 1–3: Kreirani novi moduli

**1. `src/lib/realtimeTypes.ts` (57 ln)**
Premješteni verbatim + `export` dodat:
- `RickyConnectionState`, `RickyMood`, `MouthShape`, `TranscriptEntry`, `RealtimeCallbacks` (javni API tipovi, već bili export)
- `ServerEvent`, `ResponseOutputItem` (interni tipovi — dodan `export` za cross-file import, ali **nisu** dodani u javni re-export iz `realtime.ts`)
- Importi: `RickyArtifact`, `RickyToolCall`, `RickyToolSpec` iz `"../vite-env"`; `ActivityEvent`, `VoiceState` iz `"./voiceState"`

**2. `src/lib/realtimeMouthShape.ts` (38 ln)**
Premješteni verbatim + `export` dodat svima:
- `silentMouthShape`, `smoothMouthShape`, `getSpeechBands`, `clamp01` (`export`)
- `averageRange`, `lerp` (`export` — radi konzistentnosti/testabilnosti, iako se ne koriste van modula)
- Import: `type { MouthShape }` iz `"./realtimeTypes"`

**3. `src/lib/realtimeEventHelpers.ts` (49 ln)**
Premješteni verbatim + `export` dodat svima:
- `safeParseEvent`, `parseToolArguments`, `sanitizeToolResult`, `collectItemText`, `collectOutputText`
- Importi: `type { ServerEvent, ResponseOutputItem }` iz `"./realtimeTypes"`, `type { RickyToolResult }` iz `"../vite-env"`

`npm run typecheck` — čisto (još nismo dirali `realtime.ts`).

### Korak 4: Prespojen `realtime.ts` (535 → 399 ln)

Izmjene u `realtime.ts`:
- **Importi zamijenjeni:** `RickyArtifact` uklonjen (samo `RickyToolCall`, `RickyToolResult`, `RickyToolSpec`); dodani importi iz `./realtimeMouthShape`, `./realtimeEventHelpers`, `./realtimeTypes`
- **Lokalne definicije tipova obrisane** (RickyConnectionState, RickyMood, MouthShape, TranscriptEntry, RealtimeCallbacks, ServerEvent, ResponseOutputItem)
- **Re-export tipova:** `export type { RickyConnectionState, RickyMood, MouthShape, TranscriptEntry, RealtimeCallbacks } from "./realtimeTypes"`
- **Obrisane funkcije:** `silentMouthShape`, `smoothMouthShape`, `getSpeechBands`, `averageRange`, `lerp`, `clamp01`, `safeParseEvent`, `parseToolArguments`, `sanitizeToolResult`, `collectItemText`, `collectOutputText`
- **Zadržano:** `realtimeUrl`, `MIC_IDLE_TIMEOUT_MS`, `RickyRealtimeClient` klasa (cijelo tijelo, sve metode), `newEntry`, re-exporti iz `voiceState`

### Korak 5: Verifikacija

| Check | Rezultat |
|---|---|
| `npm run typecheck` | ✅ čisto |
| `npm run build` | ✅ čisto (samo pre-postojeći 500kB chunk warning) |
| grep starih lokalnih definicija u `realtime.ts` | ✅ prazno |
| 9 import-mjesta (`from ".../lib/realtime"`) | ✅ sva netaknuta |
| `realtime.ts` linija | 399 (sa 535) |
| `realtimeTypes.ts` | 57 ln |
| `realtimeMouthShape.ts` | 38 ln |
| `realtimeEventHelpers.ts` | 49 ln |

---

## Stabilnost javnog API-ja

Javni API iz `"./lib/realtime"` ostaje identičan:

```
createActivityEvent, newEntry, RickyRealtimeClient,
type ActivityEvent, type MouthShape, type RickyConnectionState,
type RickyMood, type TranscriptEntry, type VoiceState
```

(`RealtimeCallbacks` također ostaje re-exportiran radi API stabilnosti, iako ga nijedan eksterni fajl ne importuje.)

**9 postojećih import-mjesta netaknuto** (grep potvrđen):

| Fajl | Import |
|---|---|
| `src/App.tsx:51` | `} from "./lib/realtime"` |
| `src/components/ActivityTimeline.tsx:2` | `TranscriptEntry` |
| `src/components/BottomVoiceBar.tsx:3` | `RickyConnectionState` |
| `src/components/pixel/IdleScreen.tsx:13` | `ActivityEvent, VoiceState` |
| `src/components/pixel/MiniComputerWindow.tsx:3` | `VoiceState` |
| `src/components/pixel/PixelMockupBoard.tsx:12` | `ActivityEvent, TranscriptEntry, VoiceState` |
| `src/components/pixel/Previews.tsx:9` | `ActivityEvent` |
| `src/components/pixel/TopBar.tsx:7` | `VoiceState` |
| `src/components/RickyFace.tsx:2` | `MouthShape, RickyMood` |
| `src/components/VoiceTopBar.tsx:3` | `RickyConnectionState` |

---

## Potvrda

- ✅ Ponašanje nepromijenjeno — tijela metoda `RickyRealtimeClient` klase **bajt-identična** (samo su import linije na vrhu fajla promijenjene, same metode su verbatim move)
- ✅ `newEntry` ostaje u `realtime.ts` (nije premješten)
- ✅ Svi javni exporti iz `"./lib/realtime"` ostaju identični
- ✅ `typecheck` + `build` čisti
- ✅ Nijedan `className`/tekst/logika nije izmijenjena — ovo je čist TypeScript refactor (move + import/export jedine promjene)

---

## Dira fajlovi

| Fajl | Akcija | Linije |
|---|---|---|
| `src/lib/realtimeTypes.ts` | **kreiran** | 57 |
| `src/lib/realtimeMouthShape.ts` | **kreiran** | 38 |
| `src/lib/realtimeEventHelpers.ts` | **kreiran** | 49 |
| `src/lib/realtime.ts` | **izmijenjen** (samo import/export, tijela metoda netaknuta) | 535 → 399 |

**NE commitovano** — čeka Claude pregled prema protokolu iz `docs/refactor_plan.md`.

---

## Claude pregled checklist (za Claude-a)

- [ ] `npm run typecheck` → čisto
- [ ] `npm run build` → čisto
- [ ] Diff pregled: tijela metoda klase bajt-identična vs `git show HEAD:src/lib/realtime.ts`
- [ ] Spot-check 2-3 premještene funkcije (npr. `sanitizeToolResult`, `getSpeechBands`)
- [ ] `gitnexus detect_changes` — pogođeni samo realtime.ts + 3 nova fajla
- [ ] Runtime smoke **nije potreban** (čist TypeScript refactor sa jakim static safety net-om)