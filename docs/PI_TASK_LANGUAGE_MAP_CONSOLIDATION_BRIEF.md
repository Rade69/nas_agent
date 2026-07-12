# Brief za pi — konsolidacija dupliranih jezičkih mapa

**Za:** pi · **Od:** Claude
**Povod:** `agent_reports/2026-07-12_app-review-findings.md` nalaz #3 (verifikovan i
potvrđen u `docs/PROJECT_OVERVIEW.md` sekciji 6 — "Duplirane jezičke mape").
Dodavanje 6. jezika trenutno zahtijeva izmjenu na 6 mjesta u kodu. Ovaj zadatak
to svodi na 2 mjesta (+ 5 JSON locale fajlova, koji ostaju odvojeni jer su
suštinski druga vrsta podatka — puni prevodi teksta, ne mala per-jezik
konfiguracija).

**Čisto mehanički refaktor — iste vrijednosti, samo reorganizovane.** Nijedna
vrijednost se ne mijenja, ne "popravlja", ne prevodi ponovo. Ako primijetiš
grešku u postojećim vrijednostima dok radiš ovo, NE ispravljaj je usput —
zabilježi u izvještaju kao zaseban nalaz.

---

## Arhitektonska odluka (već donesena, samo izvrši)

Electron main proces je CommonJS/Node (`electron/ipc_handlers/*.cjs`), renderer
je ESM/TS kroz Vite (`src/`). Ne postoji jednostavan način da isti TS modul
uvezu oba runtime-a bez novog build koraka — to je van obima ovog zadatka.
Zato **dvije odvojene konsolidacije**, ne jedna:

1. **Renderer strana** — novi `src/shared/languages.ts`, jedan izvor istine
   za sve TS/React potrošače.
2. **Electron strana** — dvije postojeće mape u `realtime.cjs` spojene u
   jednu, unutar istog fajla (bez cross-runtime dijeljenja).

---

## Korak 1 — `src/shared/languages.ts` (novo)

```ts
export type LanguageCode = "sr-Latn" | "en" | "de" | "es" | "fr";

export type SupportedLanguage = {
  code: LanguageCode;
  /** Prikazano u Settings dropdown-u, u izvornom pismu jezika (ne prevoditi
   *  — standardna UI konvencija, isto obrazloženje kao postojeći komentar u
   *  SettingsPanel.tsx). */
  nativeName: string;
  /** Supstring glasovni okidač za ulazak u Dictation Mode. */
  dictationTrigger: string;
  /** Glasovne fraze za izlazak iz Dictation Mode-a. */
  exitPhrases: string[];
};

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  {
    code: "sr-Latn",
    nativeName: "Srpski (latinica)",
    dictationTrigger: "dikt",
    exitPhrases: [
      "vrati se u normalan",
      "vrati u normalan",
      "izađi iz diktat",
      "izadji iz diktat",
      "prekini diktat",
      "završi diktiranje",
      "zavrsi diktiranje",
    ],
  },
  {
    code: "en",
    nativeName: "English",
    dictationTrigger: "dictat",
    exitPhrases: ["go back to normal", "exit dictation", "stop dictating", "end dictation"],
  },
  {
    code: "de",
    nativeName: "Deutsch",
    dictationTrigger: "diktier",
    exitPhrases: ["zurück zum normalen modus", "diktat beenden", "diktat verlassen"],
  },
  {
    code: "es",
    nativeName: "Español",
    dictationTrigger: "dict",
    exitPhrases: ["volver al modo normal", "salir del dictado", "terminar el dictado"],
  },
  {
    code: "fr",
    nativeName: "Français",
    dictationTrigger: "dict",
    exitPhrases: ["retour au mode normal", "quitter la dictée", "arrêter la dictée"],
  },
];

export const DEFAULT_LANGUAGE_CODE: LanguageCode = "sr-Latn";

/** Vraća SupportedLanguage za dati kod, fail-open na sr-Latn ako kod nije
 *  prepoznat (isti fail-open princip kao postojeći DEFAULT_* fallback-ovi
 *  koje ovo zamjenjuje). */
export function getLanguage(code: string | undefined | null): SupportedLanguage {
  return SUPPORTED_LANGUAGES.find((lang) => lang.code === code) ?? SUPPORTED_LANGUAGES[0];
}
```

Vrijednosti su prekopirane 1:1 iz `src/App.tsx` (linije 68-113, trenutni
`DICTATION_EXIT_PHRASES`/`DICTATION_TRIGGER_WORDS`) i `src/components/pixel/SettingsPanel.tsx`
(linije 15-21, `LANGUAGE_OPTIONS`). Zadrži postojeći komentar o best-effort
en/de/es/fr prevodima (nisu native-speaker potvrđeni) kao komentar na vrhu
`SUPPORTED_LANGUAGES` niza.

## Korak 2 — `src/App.tsx`

Ukloni `DICTATION_EXIT_PHRASES`, `DEFAULT_DICTATION_EXIT_PHRASES`,
`DICTATION_TRIGGER_WORDS`, `DEFAULT_DICTATION_TRIGGER_WORD` (linije 60-113).
Dodaj `import { getLanguage } from "./shared/languages";`.

Zamijeni na sva 3 mjesta gdje se koriste:
- Linija ~316 i ~682: `DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD`
  → `getLanguage(interfaceLanguageRef.current).dictationTrigger`
- Linija ~328: `DICTATION_EXIT_PHRASES[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_EXIT_PHRASES`
  → `getLanguage(interfaceLanguageRef.current).exitPhrases`

(Tačne linije provjeri svježim `cat` prije izmjene — `App.tsx` se često mijenja.)

## Korak 3 — `src/components/pixel/SettingsPanel.tsx`

Ukloni `LANGUAGE_OPTIONS` (linije 13-21). Dodaj
`import { SUPPORTED_LANGUAGES } from "../../shared/languages";`.

U JSX-u gdje se renderuje `<select>` (trenutno `LANGUAGE_OPTIONS.map((option) => (<option key={option.value} value={option.value}>{option.label}</option>))`),
zamijeni sa `SUPPORTED_LANGUAGES.map((lang) => (<option key={lang.code} value={lang.code}>{lang.nativeName}</option>))`.

Svuda gdje se koristi `"sr-Latn"` kao hardkodiran default (npr.
`useState("sr-Latn")`, `?? "sr-Latn"`) možeš opciono zamijeniti sa
`DEFAULT_LANGUAGE_CODE` iz istog modula — nije obavezno, tvoja procjena
čitljivosti, ali ne mijenjaj ponašanje.

## Korak 4 — `electron/ipc_handlers/realtime.cjs`

Spoji `STT_LANGUAGE_HINTS` + `DEFAULT_STT_LANGUAGE_HINT` + `LANGUAGE_NAMES` +
`DEFAULT_LANGUAGE_NAME` (linije 10-25) u jednu mapu:

```js
// Jedan izvor istine za sve po-jeziku vrijednosti na Electron strani. Ne
// dijeli se sa src/shared/languages.ts (renderer, ESM/Vite) jer bi to
// zahtijevalo nov build korak za CJS/ESM most — van obima ovog zadatka.
// Context: docs/PI_TASK_LANGUAGE_MAP_CONSOLIDATION_BRIEF.md
const LANGUAGE_CONFIG = {
  "sr-Latn": { sttHint: "sr", promptName: "Serbian (Latin script)" },
  en: { sttHint: "en", promptName: "English" },
  de: { sttHint: "de", promptName: "German" },
  es: { sttHint: "es", promptName: "Spanish" },
  fr: { sttHint: "fr", promptName: "French" },
};
const DEFAULT_LANGUAGE_CONFIG = LANGUAGE_CONFIG["sr-Latn"];
```

Zamijeni upotrebu (oko linije 78-79):
```js
sttLanguageHint = STT_LANGUAGE_HINTS[settings.interface_language] ?? DEFAULT_STT_LANGUAGE_HINT;
languageName = LANGUAGE_NAMES[settings.interface_language] ?? DEFAULT_LANGUAGE_NAME;
```
sa:
```js
const languageConfig = LANGUAGE_CONFIG[settings.interface_language] ?? DEFAULT_LANGUAGE_CONFIG;
sttLanguageHint = languageConfig.sttHint;
languageName = languageConfig.promptName;
```

Provjeri i inicijalne deklaracije (`let sttLanguageHint = DEFAULT_STT_LANGUAGE_HINT;`,
`let languageName = DEFAULT_LANGUAGE_NAME;`) — ažuriraj da koriste
`DEFAULT_LANGUAGE_CONFIG.sttHint`/`DEFAULT_LANGUAGE_CONFIG.promptName`.

## Šta NE dirati

- `src/i18n/locales/*.json` — puni prevodi GUI teksta, drugačija vrsta
  podatka, nisu dio ove konsolidacije.
- `docs/RICKY_GUI_LOCALIZATION_PLAN.md`, `docs/LOCALIZATION_AND_STT_ENGINE_PLAN.md` —
  samo referenca, ne mijenjati.
- Bilo koji fajl van: `src/shared/languages.ts` (novo), `src/App.tsx`,
  `src/components/pixel/SettingsPanel.tsx`, `electron/ipc_handlers/realtime.cjs`.

## Acceptance criteria

- `npm run typecheck` i `npm run build` — čisto.
- `node --check electron/ipc_handlers/realtime.cjs` — čisto.
- Ponašanje bajt-identično za sve postojeće jezike — isti trigger, iste exit
  fraze, isti STT hint, isto ime u promptu, iste opcije u dropdown-u. Ovo je
  reorganizacija, ne izmjena ponašanja.
- Agent report: `agent_reports/2026-07-12_language-map-consolidation.md`,
  standardni CLAUDE.md obrazac.

Kad završiš, javi — Claude verifikuje (build, GitNexus impact) prije commita.
