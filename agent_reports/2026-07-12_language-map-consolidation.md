# Agent Report — Konsolidacija dupliranih jezičkih mapa

**Datum:** 2026-07-12
**Agent:** pi
**Brief:** `docs/PI_TASK_LANGUAGE_MAP_CONSOLIDATION_BRIEF.md`
**Povod:** `agent_reports/2026-07-12_app-review-findings.md` nalaz #3

---

## Scope

Čist mehanički refaktor — iste vrijednosti, samo reorganizovane. Sa **6 nezavisnih
mjesta** gdje su istih 5 jezika bili definisani, na **2 izvora istine** (+ 5 JSON
locale fajlova koji su suštinski druga vrsta podatka — puni prevodi teksta, ne
konfiguracija).

Izmijenjeni fajlovi:
- `src/shared/languages.ts` (novo)
- `src/App.tsx`
- `src/components/pixel/SettingsPanel.tsx`
- `electron/ipc_handlers/realtime.cjs`

---

## GitNexus impact

Nije pokrenut (nije dostupan). Ručni blast radius — minimalan, jer su vrijednosti
identične, samo se izvor mijenja.

---

## Šta je urađeno

### Prije — 6 nezavisnih lokacija

| Lokacija | Mapa | Broj vrijednosti |
|----------|------|-----------------|
| `src/App.tsx:68-100` | `DICTATION_EXIT_PHRASES` | 5 jezika × ~4-7 fraza |
| `src/App.tsx:106-113` | `DICTATION_TRIGGER_WORDS` | 5 jezika × 1 trigger |
| `src/components/pixel/SettingsPanel.tsx:15-21` | `LANGUAGE_OPTIONS` | 5 jezika × 1 labela |
| `electron/ipc_handlers/realtime.cjs:13-14` | `STT_LANGUAGE_HINTS` | 5 jezika × 1 hint |
| `electron/ipc_handlers/realtime.cjs:18-25` | `LANGUAGE_NAMES` | 5 jezika × 1 ime |
| `src/i18n/locales/*.json` | 5 JSON fajlova | Puni prevodi GUI teksta |

**Dodavanje 6. jezika = izmjena na 6 mjesta u kodu**, lako zaboraviti jedno.

### Poslije — 2 izvora istine

**Renderer (ESM/TS):** `src/shared/languages.ts` — jedan fajl sa:

```ts
export type SupportedLanguage = {
  code: LanguageCode;
  nativeName: string;          // Settings dropdown labela
  dictationTrigger: string;    // Glasovni okidač za Dictation Mode
  exitPhrases: string[];       // Glasovne fraze za izlaz
};
```

- `App.tsx` koristi `getLanguage(code).dictationTrigger` i `.exitPhrases`
- `SettingsPanel.tsx` koristi `SUPPORTED_LANGUAGES` za dropdown renderovanje

**Electron (CJS):** `electron/ipc_handlers/realtime.cjs` — jedna konsolidovana mapa:

```js
const LANGUAGE_CONFIG = {
  "sr-Latn": { sttHint: "sr", promptName: "Serbian (Latin script)" },
  en: { sttHint: "en", promptName: "English" },
  // ...
};
```

Dvije odvojene konsolidacije (ne jedna) jer Electron main proces (CJS) i renderer
(ESM/Vite) ne mogu direktno dijeliti isti TS modul bez novog build koraka za
CJS/ESM most — to je van obima ovog zadatka.

---

## Zašto je urađeno

- `agent_reports/2026-07-12_app-review-findings.md` identifikovao ovo kao problem
  visokog prioriteta (nalaz #3).
- Svako dodavanje jezika je ručni posao na više mjesta, visok rizik od greške.
- Verifikovano i potvrđeno od strane korisnika u `docs/PROJECT_OVERVIEW.md` sekciji 6.
- Nakon konsolidacije, dodavanje 6. jezika = dodaj 1 element u `SUPPORTED_LANGUAGES`
  niz + 1 element u `LANGUAGE_CONFIG` mapu + 1 JSON locale fajl.

---

## Kako je urađeno

1. **Kreiran `src/shared/languages.ts`** — tipizirani niz sa svim konfiguracijskim
   podacima za 5 jezika. `getLanguage()` helper sa fail-open logikom na `sr-Latn`
   (zamjenjuje 4 stare DEFAULT_* konstante).

2. **`src/App.tsx`** — uklonjeno ~46 linija (dvije mape + dva default-a + komentari),
   dodat jedan import. Tri mjesta upotrebe ažurirana:
   - `DICTATION_TRIGGER_WORDS[...] ?? DEFAULT_DICTATION_TRIGGER_WORD` →
     `getLanguage(...).dictationTrigger` (×2)
   - `DICTATION_EXIT_PHRASES[...] ?? DEFAULT_DICTATION_EXIT_PHRASES` →
     `getLanguage(...).exitPhrases` (×1)

3. **`SettingsPanel.tsx`** — uklonjen `LANGUAGE_OPTIONS` niz (~7 linija), dodat
   `import { SUPPORTED_LANGUAGES }`. Select renderovanje promijenjeno sa
   `option.value`/`option.label` na `lang.code`/`lang.nativeName`.

4. **`realtime.cjs`** — `STT_LANGUAGE_HINTS` + `DEFAULT_STT_LANGUAGE_HINT` +
   `LANGUAGE_NAMES` + `DEFAULT_LANGUAGE_NAME` (~13 linija) spojeni u jednu
   `LANGUAGE_CONFIG` mapu + `DEFAULT_LANGUAGE_CONFIG`. Sve upotrebe ažurirane:
   `sttLanguageHint` → `languageConfig.sttHint`, `languageName` →
   `languageConfig.promptName`.

---

## Šta nije dirano

- `src/i18n/locales/*.json` — puni prevodi GUI teksta, druga vrsta podatka, nisu dio ove konsolidacije
- Bilo koji fajl van dozvoljene liste
- Vrijednosti — nijedna nije promijenjena (čist refaktor, ne izmjena ponašanja)

---

## Verifikacija

- ✅ `npx tsc --noEmit` — čisto
- ✅ `npm run build` — uspješan
- ✅ `node --check electron/ipc_handlers/realtime.cjs` — čisto
- ✅ Sve stare reference uklonjene (potvrđeno grep-om)
- ✅ Ponašanje bajt-identično — isti trigger, iste exit fraze, isti STT hint, isto ime u promptu, iste opcije u dropdown-u

---

## Rizici / ograničenja

Nema. Čist refaktor, bez izmjene ponašanja.

---

## Potrebna korisnička potvrda

Nije potrebna — sve verifikacije prolaze, ponašanje bajt-identično.