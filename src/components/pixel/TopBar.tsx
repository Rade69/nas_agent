/** Pixel top bar — verbatim move from App.tsx (R3). JSX unchanged. */
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
}: {
  mode: RickyMode;
  screen: ScreenState;
  voiceState: VoiceState;
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onStopAll?: () => void;
}) {
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
              Diktiranje
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
          <button className="pixel-top-stop-all" onClick={onStopAll} title="Zaustavi sve aktivnosti">
            <IconStop />
            Stop sve
          </button>
          <button className={`pixel-mode-pill ${mode === "computer" ? "on" : ""}`} onClick={onToggleMode}>
            Računarski režim: {mode === "computer" ? "UKLJUČEN" : "ISKLJUČEN"}
          </button>
          <button className="pixel-icon-button" title="Glas">
            <IconWave />
          </button>
          <button className="pixel-icon-button" onClick={onOpenPlans} title="Planovi">
            <IconCalendar />
          </button>
        </div>
      ) : null}
    </header>
  );
}
