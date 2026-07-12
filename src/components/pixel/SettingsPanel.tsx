/** Settings panel — replaces the "Postavke nisu dostupne" placeholder.
 *  Structured as sections (currently three: "Lično", "Jezik", "Brze
 *  komande") so future preferences can be added as new sections without
 *  restructuring this file.
 *  Context: agent_reports/2026-07-11_settings-panel-foundation.md
 *  Context: agent_reports/2026-07-11_interface-language-stt-hint.md
 *  Context: agent_reports/2026-07-12_language-map-consolidation.md
 *  Context: agent_reports/2026-07-12_custom-quick-commands.md */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { UserSettings } from "../../vite-env";
import i18n from "../../i18n";
// Jedan izvor istine za jezičke mape (agent_reports/2026-07-12_language-map-consolidation.md).
import { SUPPORTED_LANGUAGES } from "../../shared/languages";

type SaveStatus = "loading" | "idle" | "saving" | "saved" | "error";

export function SettingsPanel({
  onQuickCommandsChange,
}: {
  // App.tsx owns the IdleScreen-facing quickCommands state — this applies a
  // save immediately, no app restart, same principle as i18n.changeLanguage()
  // below. Optional since nothing else currently mounts SettingsPanel.
  onQuickCommandsChange?: (commands: string[]) => void;
}) {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [nameStatus, setNameStatus] = useState<SaveStatus>("loading");
  const [languageInput, setLanguageInput] = useState("sr-Latn");
  const [languageStatus, setLanguageStatus] = useState<SaveStatus>("loading");
  const [commandsInput, setCommandsInput] = useState<string[]>([]);
  const [commandsStatus, setCommandsStatus] = useState<SaveStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    window.ricky
      .getSettings()
      .then((result) => {
        if (cancelled) return;
        setSettings(result);
        setNameInput(result.user_name);
        setLanguageInput(result.interface_language ?? "sr-Latn");
        setCommandsInput(result.quick_commands ?? []);
        setNameStatus("idle");
        setLanguageStatus("idle");
        setCommandsStatus("idle");
      })
      .catch(() => {
        if (!cancelled) {
          setNameStatus("error");
          setLanguageStatus("error");
          setCommandsStatus("error");
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

  async function handleSaveCommands() {
    // Empty strings would render as blank buttons in IdleScreen — drop them
    // rather than reject the save, so a stray "+" click followed by Save
    // doesn't need its own error state.
    const cleaned = commandsInput.map((c) => c.trim()).filter((c) => c.length > 0);
    setCommandsStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ quick_commands: cleaned });
      setSettings(updated);
      setCommandsInput(updated.quick_commands ?? []);
      onQuickCommandsChange?.(updated.quick_commands ?? []);
      setCommandsStatus("saved");
      window.setTimeout(() => setCommandsStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setCommandsStatus("error");
    }
  }

  function updateCommandAt(index: number, value: string) {
    setCommandsInput((current) => current.map((c, i) => (i === index ? value : c)));
  }

  function removeCommandAt(index: number) {
    setCommandsInput((current) => current.filter((_, i) => i !== index));
  }

  if (nameStatus === "loading" || languageStatus === "loading" || commandsStatus === "loading") {
    return <p className="drawer-placeholder-text">{t("settings.loading")}</p>;
  }

  const nameDirty = settings !== null && nameInput.trim() !== settings.user_name && nameInput.trim() !== "";
  const languageDirty = settings !== null && languageInput !== (settings.interface_language ?? "sr-Latn");
  const commandsDirty =
    settings !== null &&
    JSON.stringify(commandsInput.map((c) => c.trim()).filter((c) => c.length > 0)) !==
      JSON.stringify(settings.quick_commands ?? []);

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

      <section className="pixel-settings-section">
        <h3>{t("settings.quickCommandsSection")}</h3>
        <span className="pixel-settings-hint">{t("settings.quickCommandsHint")}</span>
        <div className="pixel-quick-commands-editor">
          {commandsInput.map((command, index) => (
            <div className="pixel-quick-command-row" key={index}>
              <input
                type="text"
                value={command}
                onChange={(event) => updateCommandAt(index, event.target.value)}
                placeholder={t("settings.quickCommandPlaceholder")}
              />
              <button
                className="pixel-icon-button"
                onClick={() => removeCommandAt(index)}
                aria-label={t("settings.removeQuickCommand")}
                title={t("settings.removeQuickCommand")}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            className="pixel-secondary"
            onClick={() => setCommandsInput((current) => [...current, ""])}
          >
            + {t("settings.addQuickCommand")}
          </button>
        </div>
        <div className="pixel-settings-actions">
          <button
            className="pixel-primary"
            onClick={() => void handleSaveCommands()}
            disabled={!commandsDirty || commandsStatus === "saving"}
          >
            {commandsStatus === "saving" ? t("settings.saving") : t("settings.save")}
          </button>
          {commandsStatus === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">{t("settings.saved")}</span> : null}
          {commandsStatus === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">{t("settings.error")}</span>
          ) : null}
        </div>
      </section>
    </div>
  );
}
