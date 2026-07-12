/** Pixel top bar — verbatim move from App.tsx (R3), later localized
 *  (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md). "Ricky" brand
 *  name stays untranslated, same as the doc's own examples. */
import { useTranslation } from "react-i18next";
import IconLogoR from "../../../assets/brending/logo/ricky-logo-r.svg?react";
import IconWave from "../../../assets/brending/icons/voice/icon-audio-wave.svg?react";
import IconStop from "../../../assets/brending/icons/voice/icon-stop.svg?react";
import IconCalendar from "../../../assets/brending/icons/actions/icon-calendar.svg?react";
import { voiceStateLabel } from "../../lib/voiceState";
import type { VoiceState } from "../../lib/realtime";
import type { RickyMode, ScreenState } from "./types";

export function TopBar({
  mode,
  screen,
  voiceState,
  onToggleMode,
  onOpenPlans,
  onStopAll,
  onEnterDictation,
}: {
  mode: RickyMode;
  screen: ScreenState;
  voiceState: VoiceState;
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onStopAll?: () => void;
  onEnterDictation?: () => void;
}) {
  const { t } = useTranslation();
  return (
    <header className="pixel-top-bar">
      <div className="pixel-brand">
        <span className="pixel-brand-orb">
          <IconLogoR className="pixel-brand-logo" />
        </span>
        <strong>Ricky</strong>
        <span className={`pixel-state pixel-state-${voiceState}`}>
          {screen === "dictation" ? (
            <>
              <IconWave className="pixel-state-icon" />
              {t("topBar.dictation")}
            </>
          ) : (
            <>
              <span className="pixel-state-dot" />
              {voiceStateLabel(voiceState)}
            </>
          )}
        </span>
      </div>
      {onStopAll ? (
        <div className="pixel-top-actions">
          <button className="pixel-top-stop-all" onClick={onStopAll} title={t("topBar.stopAllTitle")}>
            <IconStop />
            {t("topBar.stopAll")}
          </button>
          <button className={`pixel-mode-pill ${mode === "computer" ? "on" : ""}`} onClick={onToggleMode}>
            {t("topBar.computerMode")} {mode === "computer" ? t("topBar.on") : t("topBar.off")}
          </button>
          {onEnterDictation && screen !== "dictation" ? (
            <button className="pixel-top-dictation" onClick={onEnterDictation} title={t("topBar.enterDictation")}>
              <IconWave />
              {t("topBar.dictation")}
            </button>
          ) : null}
          <button className="pixel-icon-button" title={t("topBar.voice")}>
            <IconWave />
          </button>
          <button className="pixel-icon-button" onClick={onOpenPlans} title={t("topBar.plans")}>
            <IconCalendar />
          </button>
        </div>
      ) : null}
    </header>
  );
}
