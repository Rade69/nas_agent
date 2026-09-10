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
import type { UserSettings, BrowserBridgeStatus, PairingSession } from "../../vite-env";
import i18n from "../../i18n";
import { SUPPORTED_LANGUAGES } from "../../shared/languages";

type SaveStatus = "loading" | "idle" | "saving" | "saved" | "error";

// OpenAI Realtime voice model — in-app selector. Interni API ID → labela.
const REALTIME_MODELS = [
  { value: "gpt-realtime-2.1", label: "GPT Realtime 2.1" },
  { value: "gpt-realtime-2.1-mini", label: "GPT Realtime 2.1 Mini" },
];

export function SettingsPanel({
  onQuickCommandsChange,
  onAgentNameChange,
}: {
  // App.tsx owns the IdleScreen-facing quickCommands state — this applies a
  // save immediately, no app restart, same principle as i18n.changeLanguage()
  // below. Optional since nothing else currently mounts SettingsPanel.
  onQuickCommandsChange?: (commands: string[]) => void;
  onAgentNameChange?: (name: string) => void;
}) {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [nameStatus, setNameStatus] = useState<SaveStatus>("loading");
  const [agentNameInput, setAgentNameInput] = useState("");
  const [agentNameStatus, setAgentNameStatus] = useState<SaveStatus>("loading");
  const [languageInput, setLanguageInput] = useState("sr-Latn");
  const [languageStatus, setLanguageStatus] = useState<SaveStatus>("loading");
  const [commandsInput, setCommandsInput] = useState<string[]>([]);
  const [commandsStatus, setCommandsStatus] = useState<SaveStatus>("loading");
  const [realtimeModelInput, setRealtimeModelInput] = useState("gpt-realtime-2.1");
  const [realtimeModelStatus, setRealtimeModelStatus] = useState<SaveStatus>("loading");
  // C0: Browser Bridge
  const [bridgeStatus, setBridgeStatus] = useState<BrowserBridgeStatus | null>(null);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [pairingId, setPairingId] = useState<string | null>(null);
  const [pairingExpiry, setPairingExpiry] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    window.ricky
      .getSettings()
      .then((result) => {
        if (cancelled) return;
        setSettings(result);
        setNameInput(result.user_name);
        setAgentNameInput(result.agent_name ?? "Ricky");
        setLanguageInput(result.interface_language ?? "sr-Latn");
        setCommandsInput(result.quick_commands ?? []);
        setRealtimeModelInput(result.realtime_model ?? "gpt-realtime-2.1");
        setNameStatus("idle");
        setAgentNameStatus("idle");
        setLanguageStatus("idle");
        setCommandsStatus("idle");
        setRealtimeModelStatus("idle");
      })
      .catch(() => {
        if (!cancelled) {
          setNameStatus("error");
          setAgentNameStatus("error");
          setLanguageStatus("error");
          setCommandsStatus("error");
          setRealtimeModelStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // C0: Browser Bridge — poll status every 5 seconds
  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      window.ricky.getBrowserBridgeStatus().then((status) => {
        if (!cancelled) setBridgeStatus(status);
      }).catch(() => {});
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // C0: Pairing code countdown
  useEffect(() => {
    if (pairingExpiry <= 0) return;
    const interval = setInterval(() => {
      setPairingExpiry((prev) => {
        if (prev <= 1) {
          setPairingCode(null);
          setPairingId(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [pairingExpiry]);

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

  async function handleSaveAgentName() {
    const trimmed = agentNameInput.trim();
    setAgentNameStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ agent_name: trimmed || "Ricky" });
      setSettings(updated);
      setAgentNameInput(updated.agent_name ?? "Ricky");
      onAgentNameChange?.(updated.agent_name ?? "Ricky");
      setAgentNameStatus("saved");
      window.setTimeout(() => setAgentNameStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setAgentNameStatus("error");
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

  async function handleSaveRealtimeModel() {
    setRealtimeModelStatus("saving");
    try {
      const updated = await window.ricky.updateSettings({ realtime_model: realtimeModelInput });
      setSettings(updated);
      setRealtimeModelInput(updated.realtime_model ?? "gpt-realtime-2.1");
      setRealtimeModelStatus("saved");
      window.setTimeout(() => setRealtimeModelStatus((current) => (current === "saved" ? "idle" : current)), 2000);
    } catch {
      setRealtimeModelStatus("error");
    }
  }

  if (
    nameStatus === "loading" ||
    agentNameStatus === "loading" ||
    languageStatus === "loading" ||
    commandsStatus === "loading" ||
    realtimeModelStatus === "loading"
  ) {
    return <p className="drawer-placeholder-text">{t("settings.loading")}</p>;
  }

  const nameDirty = settings !== null && nameInput.trim() !== settings.user_name && nameInput.trim() !== "";
  const agentNameDirty =
    settings !== null && agentNameInput.trim() !== (settings.agent_name ?? "Ricky") && agentNameInput.trim() !== "";
  const languageDirty = settings !== null && languageInput !== (settings.interface_language ?? "sr-Latn");
  const commandsDirty =
    settings !== null &&
    JSON.stringify(commandsInput.map((c) => c.trim()).filter((c) => c.length > 0)) !==
      JSON.stringify(settings.quick_commands ?? []);
  const realtimeModelDirty =
    settings !== null && realtimeModelInput !== (settings.realtime_model ?? "gpt-realtime-2.1");

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
          <span className="pixel-settings-hint">{t("settings.nameHint", { agentName: agentNameInput.trim() || "Ricky" })}</span>
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
        <label className="pixel-settings-field">
          <span>{t("settings.agentName")}</span>
          <input
            type="text"
            value={agentNameInput}
            onChange={(event) => setAgentNameInput(event.target.value)}
            placeholder="Ricky"
          />
          <span className="pixel-settings-hint">{t("settings.agentNameHint")}</span>
        </label>
        <div className="pixel-settings-actions">
          <button
            className="pixel-primary"
            onClick={() => void handleSaveAgentName()}
            disabled={!agentNameDirty || agentNameStatus === "saving"}
          >
            {agentNameStatus === "saving" ? t("settings.saving") : t("settings.save")}
          </button>
          {agentNameStatus === "saved" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-ok">{t("settings.saved")}</span>
          ) : null}
          {agentNameStatus === "error" ? (
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
        <h3>Glas</h3>
        <label className="pixel-settings-field">
          <span>AI voice model</span>
          <select
            value={realtimeModelInput}
            onChange={(event) => setRealtimeModelInput(event.target.value)}
          >
            {REALTIME_MODELS.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
          <span className="pixel-settings-hint">
            Primjenjuje se pri sljedećoj glasovnoj sesiji.
          </span>
        </label>
        <div className="pixel-settings-actions">
          <button
            className="pixel-primary"
            onClick={() => void handleSaveRealtimeModel()}
            disabled={!realtimeModelDirty || realtimeModelStatus === "saving"}
          >
            {realtimeModelStatus === "saving" ? t("settings.saving") : t("settings.save")}
          </button>
          {realtimeModelStatus === "saved" ? (
            <span className="pixel-settings-feedback pixel-settings-feedback-ok">{t("settings.saved")}</span>
          ) : null}
          {realtimeModelStatus === "error" ? (
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

      {/* C0: Browser Bridge */}
      <section className="pixel-settings-section">
        <h3>Browseri i kartice</h3>
        <p className="pixel-settings-hint">
          Poveži Ricky sa Brave/Chrome/Edge browserom da bi mogao da vidi, broji, otvara i zatvara kartice.
        </p>

        {/* Status */}
        <div style={{
          padding: "10px 12px",
          borderRadius: 6,
          marginBottom: 14,
          fontSize: "0.85rem",
          background: bridgeStatus?.connected ? "#1b4332" : "#3e1a1a",
          border: bridgeStatus?.connected ? "1px solid #2d6a4f" : "1px solid #6b2c2c",
        }}>
          {bridgeStatus?.connected ? (
            <>
              ✅ <strong>Povezano</strong> — {bridgeStatus.browser_kind} / {bridgeStatus.profile_label || "Default"}
              {bridgeStatus.extension_version && <span style={{opacity:0.6, marginLeft:8}}>v{bridgeStatus.extension_version}</span>}
            </>
          ) : (
            <>⚠ <strong>Nije povezano</strong> — instaliraj Ricky Browser Bridge ekstenziju</>
          )}
        </div>

        {/* Pairing flow */}
        {!bridgeStatus?.connected && (
          <>
            <label className="pixel-settings-field">
              <span>Browser</span>
              <select
                id="bridge-browser-select"
                defaultValue="brave"
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #444",
                  borderRadius: 6,
                  background: "#16213e",
                  color: "#e0e0e0",
                  fontSize: "0.9rem",
                }}
              >
                <option value="brave">Brave</option>
                <option value="chrome">Chrome</option>
                <option value="edge">Edge</option>
              </select>
            </label>

            {!pairingCode ? (
              <button
                className="pixel-primary"
                onClick={async () => {
                  const select = document.getElementById("bridge-browser-select") as HTMLSelectElement;
                  const browserKind = select?.value || "brave";
                  try {
                    const session: PairingSession = await window.ricky.startBrowserPairing(browserKind);
                    setPairingCode(session.human_code);
                    setPairingId(session.pairing_id);
                    setPairingExpiry(session.expires_in_seconds);
                  } catch (e: any) {
                    alert("Greška: " + (e?.message || "Nije uspjelo pokretanje pairinga."));
                  }
                }}
              >
                🔑 Poveži
              </button>
            ) : (
              <div style={{
                background: "#0d1b2a",
                borderRadius: 8,
                padding: "14px 16px",
                marginBottom: 12,
                textAlign: "center",
              }}>
                <p style={{margin: "0 0 8px 0", fontSize:"0.82rem", color:"#aaa"}}>
                  Otvori ekstenziju (klikni na ikonicu u browser toolbaru → Options) i unesi ovaj kod:
                </p>
                <div style={{
                  fontFamily: "'Courier New', monospace",
                  fontSize: "1.8rem",
                  fontWeight: "bold",
                  letterSpacing: 5,
                  color: "#4CAF50",
                  padding: "8px 0",
                }}>
                  {pairingCode}
                </div>
                <p style={{margin: "4px 0 0 0", fontSize:"0.75rem", color:"#888"}}>
                  Kod ističe za {pairingExpiry}s
                </p>
                <button
                  className="pixel-secondary"
                  style={{marginTop: 8}}
                  onClick={() => {
                    navigator.clipboard.writeText(pairingCode);
                  }}
                >
                  📋 Kopiraj kod
                </button>
                <button
                  className="pixel-secondary"
                  style={{marginTop: 8, marginLeft: 8}}
                  onClick={() => {
                    setPairingCode(null);
                    setPairingId(null);
                    setPairingExpiry(0);
                    if (pairingId) window.ricky.cancelBrowserPairing(pairingId).catch(() => {});
                  }}
                >
                  ✕ Otkaži
                </button>
              </div>
            )}

            <div style={{
              fontSize: "0.78rem",
              color: "#777",
              lineHeight: 1.5,
            }}>
              <strong>Kako instalirati ekstenziju (development):</strong>
              <ol style={{paddingLeft: 16, margin: "4px 0"}}>
                <li>Otvori <code>brave://extensions</code> (ili chrome://extensions / edge://extensions)</li>
                <li>Uključi <strong>Developer mode</strong></li>
                <li>Klikni <strong>Load unpacked</strong></li>
                <li>Izaberi folder <code>browser_extension/</code> iz ovog projekta</li>
                <li>Klikni na ikonicu ekstenzije → <strong>Options</strong></li>
                <li>Unesi pairing kod koji se prikaže ovdje nakon klika na Poveži</li>
              </ol>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
