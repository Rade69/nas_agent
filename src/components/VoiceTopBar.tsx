/** Deprecated voice top bar from the pre-pixel-redesign UI (FAZA 8).
 *  Replaced by the pixel TopBar component. Kept for reference. */
import { Activity, Bot, CircleAlert } from "lucide-react";
import { voiceStateLabel, type VoiceState } from "../lib/voiceState";
import type { RickyConnectionState } from "../lib/realtime";

type VoiceTopBarProps = {
  voiceState: VoiceState;
  connectionState: RickyConnectionState;
  status: string;
  activityCount: number;
};

export function VoiceTopBar({ voiceState, connectionState, status, activityCount }: VoiceTopBarProps) {
  return (
    <header className="voice-top-bar">
      <div className="voice-brand">
        <Bot size={17} />
        <span>Ricky</span>
      </div>
      <div className={`voice-state-pill voice-state-${voiceState}`}>
        <span className="voice-state-dot" />
        <span>{voiceStateLabel(voiceState)}</span>
      </div>
      <div className="voice-top-status">
        {connectionState === "error" ? <CircleAlert size={14} /> : <Activity size={14} />}
        <span>{status}</span>
      </div>
      <div className="voice-top-count">{activityCount}</div>
    </header>
  );
}