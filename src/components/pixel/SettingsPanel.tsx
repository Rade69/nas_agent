/** Settings panel — replaces the "Postavke nisu dostupne" placeholder.
 *  Structured as sections (currently two: "Lično" and "Jezik") so future
 *  preferences can be added as new sections without restructuring this file.
 *  Context: agent_reports/2026-07-11_settings-panel-foundation.md
 *  Context: agent_reports/2026-07-11_interface-language-stt-hint.md */
import { useEffect, useState } from "react";
import type { UserSettings } from "../../vite-env";

type SaveStatus = "loading" | "idle" | "saving" | "saved" | "error";

// STT jezički hint mapiranje — istovjetno electron/ipc_handlers/realtime.cjs.
// Sr-Latn ostaje "sr" (NE "bs"), zadržava postojeće ponašanje.
const LANGUAGE_OPTIONS: { value: string; label: string }[] = [
  { value: "sr-Latn", label: "Srpski (latinica)" },
  { value: "en", label: "English" },
  { value: "de", label: "Deutsch" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
];

export function SettingsPanel() {
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
      setLanguageStatus("saved");
      window.setTimeout(() => setLanguageStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setLanguageStatus("error");
    }
  }

  if (nameStatus === "loading" || languageStatus === "loading") {
    return <p className="drawer-placeholder-text">Učitavam postavke...</p>;
  }

  const nameDirty = settings !== null && nameInput.trim() !== settings.user_name && nameInput.trim() !== "";
  const languageDirty = settings !== null && languageInput !== (settings.interface_language ?? "sr-Latn");

  return (
    <div className="pixel-settings-panel">
      <section className="pixel-settings-section">
        <h3>Lično</h3>
        <label className="pixel-settings-field">
          <span>Tvoje ime</span>
          <input
            type="text"
            value={nameInput}
            onChange={(event) => setNameInput(event.target.value)}
            placeholder="Riley"
          />
          <span className="pixel-settings-hint">Riki će te ovako oslovljavati u razgovoru.</span>
        </label>
        <div className="pixel-settings-actions">
          <button className="pixel-primary" onClick={() => void handleSaveName()} disabled={!nameDirty || nameStatus === "saving"}>
            {nameStatus === "saving" ? "Čuvam..." : "Sačuvaj"}
          </button>
          {nameStatus === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">Sačuvano.</span> : null}
          {nameStatus === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">Greška — pokušaj ponovo.</span>
          ) : null}
        </div>
      </section>

      <section className="pixel-settings-section">
        <h3>Jezik</h3>
        <label className="pixel-settings-field">
          <span>Jezik diktiranja</span>
          <select
            value={languageInput}
            onChange={(event) => setLanguageInput(event.target.value)}
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <span className="pixel-settings-hint">
            Jezik za prepoznavanje govora u Diktatu. Promjena se primjenjuje pri sljedećem povezivanju glasa.
          </span>
        </label>
        <div className="pixel-settings-actions">
          <button className="pixel-primary" onClick={() => void handleSaveLanguage()} disabled={!languageDirty || languageStatus === "saving"}>
            {languageStatus === "saving" ? "Čuvam..." : "Sačuvaj"}
          </button>
          {languageStatus === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">Sačuvano.</span> : null}
          {languageStatus === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">Greška — pokušaj ponovo.</span>
          ) : null}
        </div>
      </section>
    </div>
  );
}
