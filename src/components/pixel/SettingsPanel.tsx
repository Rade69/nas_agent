/** Settings panel — replaces the "Postavke nisu dostupne" placeholder.
 *  Structured as sections (currently one: "Lično") so future preferences
 *  (e.g. cloud/lokalni STT izbor za diktat, docs/RICKY_GUI_LOCALIZATION_PLAN.md)
 *  can be added as new sections without restructuring this file.
 *  Context: agent_reports/2026-07-11_settings-panel-foundation.md */
import { useEffect, useState } from "react";
import type { UserSettings } from "../../vite-env";

type SaveStatus = "loading" | "idle" | "saving" | "saved" | "error";

export function SettingsPanel() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [status, setStatus] = useState<SaveStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    window.ricky
      .getSettings()
      .then((result) => {
        if (cancelled) return;
        setSettings(result);
        setNameInput(result.user_name);
        setStatus("idle");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSave() {
    const trimmed = nameInput.trim();
    setStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ user_name: trimmed || "Riley" });
      setSettings(updated);
      setNameInput(updated.user_name);
      setStatus("saved");
      window.setTimeout(() => setStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setStatus("error");
    }
  }

  if (status === "loading") {
    return <p className="drawer-placeholder-text">Učitavam postavke...</p>;
  }

  const dirty = settings !== null && nameInput.trim() !== settings.user_name && nameInput.trim() !== "";

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
          <button className="pixel-primary" onClick={() => void handleSave()} disabled={!dirty || status === "saving"}>
            {status === "saving" ? "Čuvam..." : "Sačuvaj"}
          </button>
          {status === "saved" ? <span className="pixel-settings-feedback pixel-settings-feedback-ok">Sačuvano.</span> : null}
          {status === "error" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-error">Greška — pokušaj ponovo.</span>
          ) : null}
        </div>
      </section>
    </div>
  );
}
