/** i18next bootstrap (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md).
 *  Language codes match interface_language values from Settings exactly
 *  (sr-Latn/en/de/es/fr) — no separate mapping table needed here, unlike
 *  the STT hint (electron/ipc_handlers/realtime.cjs) which needs OpenAI-
 *  specific codes.
 *
 *  de/es/fr translations are best-effort, NOT native-speaker verified —
 *  same disclaimer as the dictation trigger/exit phrases
 *  (agent_reports/2026-07-11_dictation-language-cascade.md). sr-Latn and en
 *  are direct translations of the actual current UI strings.
 *
 *  Only three components are wired to this so far (Sidebar, TopBar,
 *  voiceStateLabel) — proving the postavka -> i18n -> rendered text chain
 *  works end to end. The rest of the GUI stays hardcoded Serbian, deferred
 *  to a later round (docs/RICKY_GUI_LOCALIZATION_PLAN.md PR-2/PR-3).
 *  Context: agent_reports/2026-07-11_i18n-foundation.md */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import deLocale from "./locales/de.json";
import enLocale from "./locales/en.json";
import esLocale from "./locales/es.json";
import frLocale from "./locales/fr.json";
import srLatnLocale from "./locales/sr-Latn.json";

void i18n.use(initReactI18next).init({
  resources: {
    "sr-Latn": { translation: srLatnLocale },
    en: { translation: enLocale },
    de: { translation: deLocale },
    es: { translation: esLocale },
    fr: { translation: frLocale },
  },
  lng: "sr-Latn",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
