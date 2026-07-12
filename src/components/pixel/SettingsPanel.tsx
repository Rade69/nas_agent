/** Settings panel — replaces the "Postavke nisu dostupne" placeholder.
 *  Structured as sections (currently two: "Lično" and "Jezik") so future
 *  preferences can be added as new sections without restructuring this file.
 *  Context: agent_reports/2026-07-11_settings-panel-foundation.md
 *  Context: agent_reports/2026-07-11_interface-language-stt-hint.md
 *  Context: agent_reports/2026-07-12_language-map-consolidation.md */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { UserSettings } from "../../vite-env";
import i18n from "../../i18n";
// Jedan izvor istine za jezičke mape (agent_reports/2026-07-12_language-map-consolidation.md).
import { SUPPORTED_LANGUAGES } from "../../shared/languages";

type SaveStatus = "loading" | "idle" | "saving" | "saved" | "error";

export function SettingsPanel() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [nameStatus, setNameStatus] = useState<SaveStatus>("loading");
  const [languageInput, setLanguageInput] = useState("sr-Latn");
  const [languageStatus, setLanguageStatus] = useState<SaveStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    window.ricky
      .getSettings()
      .then((result) => {
        if (cancelled) return;
        setSettings(result);
        setNameInput(result.user_name);
        setLanguageInput(result.interface_language ?? "sr-Latn");
        setNameStatus("idle");
        setLanguageStatus("idle");
      })
      .catch(() => {
        if (!cancelled) {
          setNameStatus("error");
          setLanguageStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSaveName() {
    const trimmed = nameInput.trim();
    setNameStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ user_name: trimmed || "Riley" });
      setSettings(updated);
      setNameInput(updated.user_name);
      setNameStatus("saved");
      window.setTimeout(() => setNameStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setNameStatus("error");
    }
  }

  async function handleSaveLanguage() {
    setLanguageStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ interface_language: languageInput });
      setSettings(updated);
      setLanguageInput(updated.interface_language ?? "sr-Latn");
      // Applies immediately, no app restart — docs/RICKY_GUI_LOCALIZATION_PLAN.md
      // prefers live language switching over a "restart to apply" message.
      void i18n.changeLanguage(updated.interface_language ?? "sr-Latn");
      setLanguageStatus("saved");
      window.setTimeout(() => setLanguageStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setLanguageStatus("error");
    }
  }

  if (nameStatus === "loading" || languageStatus === "loading") {
    return <p className="drawer-placeholder-text">{t("settings.loading")}</p>;
  }

  const nameDirty = settings !== null && nameInput.trim() !== settings.user_name && nameInput.trim() !== "";
  const languageDirty = settings !== null && languageInput !== (settings.interface_language ?? "sr-Latn");

  return (
    <div className="pixel-settings-panel">
      <section className="pixel-settings-section">
        <h3>{t("settings.personalSection")}</h3>
        <label className="pixel-settings-field">
          <span>{t("settings.yourName")}</span>
          <input
            type="text"
            value={nameInput}
            onChange={(event) => setNameInput(event.target.value)}
            placeholder="Riley"
          />
          <span className="pixel-settings-hint">{t("settings.nameHint")}</span>
        </label>
        <div className="pixel-settings-actions">
          <button className="pixel-primary" onClick={() => void handleSaveName()} disabled={!nameDirty || nameStatus === "saving"}>
            {nameStatus === "saving" ? t("settings.saving") : t("settings.save")}
          </button>
          {nameStatus === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">{t("settings.saved")}</span> : null}
          {nameStatus === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">{t("settings.error")}</span>
          ) : null}
        </div>
      </section>

      <section className="pixel-settings-section">
        <h3>{t("settings.languageSection")}</h3>
        <label className="pixel-settings-field">
          <span>{t("settings.dictationLanguage")}</span>
          <select
            value={languageInput}
            onChange={(event) => setLanguageInput(event.target.value)}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.nativeName}
              </option>
            ))}
          </select>
          <span className="pixel-settings-hint">{t("settings.dictationLanguageHint")}</span>
        </label>
        <div className="pixel-settings-actions">
          <button className="pixel-primary" onClick={() => void handleSaveLanguage()} disabled={!languageDirty || languageStatus === "saving"}>
            {languageStatus === "saving" ? t("settings.saving") : t("settings.save")}
          </button>
          {languageStatus === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">{t("settings.saved")}</span> : null}
          {languageStatus === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">{t("settings.error")}</span>
          ) : null}
        </div>
      </section>
    </div>
  );
}
