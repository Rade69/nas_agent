/** Jedan izvor istine za sve po-jeziku vrijednosti na renderer strani.
 *  Konsoliduje mape koje su ranije bile duplirane na 3 mjesta:
 *  App.tsx (DICTATION_EXIT_PHRASES + DICTATION_TRIGGER_WORDS) i
 *  SettingsPanel.tsx (LANGUAGE_OPTIONS).
 *
 *  Ne dijeli se sa electron/ipc_handlers/realtime.cjs (Electron main, CJS)
 *  — tamo postoji zasebna konsolidovana mapa u istom fajlu, jer bi CJS/ESM
 *  most zahtijevao nov build korak van obima ovog zadatka.
 *  Context: agent_reports/2026-07-12_language-map-consolidation.md
 *
 *  en/de/es/fr dictationTrigger i exitPhrases su best-effort, NOT
 *  native-speaker verified (agent_reports/2026-07-11_dictation-language-cascade.md). */

export type LanguageCode = "sr-Latn" | "en" | "de" | "es" | "fr";

export type SupportedLanguage = {
  code: LanguageCode;
  /** Prikazano u Settings dropdown-u, u izvornom pismu jezika (ne prevoditi
   *  — standardna UI konvencija). */
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