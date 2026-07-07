import type { VoiceState } from "../lib/realtime";
import orbListening from "../../assets/brending/orb/ricky-orb-listening.png";
import orbSpeaking from "../../assets/brending/orb/ricky-orb-speaking.png";
import orbThinking from "../../assets/brending/orb/ricky-orb-thinking.png";
import orbWarning from "../../assets/brending/orb/ricky-orb-warning.png";
import orbError from "../../assets/brending/orb/ricky-orb-error.png";
import orbMain from "../../assets/brending/orb/ricky-orb-main.png";

type RickyOrbProps = {
  voiceState: VoiceState;
  size?: "large" | "small";
};

// idle/muted use orbMain (the jagged-aura "hero" asset — see
// assets/GUI-SETS/GUI-SET-1.png) instead of orbIdle, which is a flat,
// simple circle meant for small contexts, not the dominant idle-screen orb.
const ORB_FOR_STATE: Record<string, string> = {
  idle: orbMain,
  listening: orbListening,
  transcribing: orbListening,
  thinking: orbThinking,
  speaking: orbSpeaking,
  waiting_confirmation: orbWarning,
  interrupted: orbWarning,
  muted: orbMain,
  error: orbError,
};

export function RickyOrb({ voiceState, size = "large" }: RickyOrbProps) {
  const orbSrc = ORB_FOR_STATE[voiceState] || orbMain;
  const className = `ricky-orb ${voiceState}${size === "small" ? " ricky-orb-small" : ""}`;

  return (
    <div className={className}>
      <img
        src={orbSrc}
        alt="Ricky orb"
        className="ricky-orb-img"
        draggable={false}
      />
      <div className="ricky-orb-ring" />
    </div>
  );
}