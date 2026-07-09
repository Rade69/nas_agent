import type { VoiceState } from "../lib/voiceState";
import orbListening from "../../assets/brending/orb/ricky-orb-listening.png";
import orbSpeaking from "../../assets/brending/orb/ricky-orb-speaking.png";
import orbThinking from "../../assets/brending/orb/ricky-orb-thinking.png";
import orbWarning from "../../assets/brending/orb/ricky-orb-warning.png";
import orbError from "../../assets/brending/orb/ricky-orb-error.png";
import orbMain from "../../assets/brending/orb/ricky-orb-main.png";

/**
 * Visual orb state — coarser than VoiceState, drives CSS animation class.
 * See docs/RICKY_ORB_ANIMATION_PLAN.md section 3 for the mapping rationale.
 */
export type RickyOrbState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "warning"
  | "error"
  | "muted";

type RickyOrbProps = {
  /** App-level voice state; mapped to a visual orb state internally. */
  voiceState: VoiceState;
  size?: "large" | "small" | "floating";
  className?: string;
};

/**
 * Map the app VoiceState to a visual RickyOrbState. The orb must NOT decide
 * its own state — this is the single source of truth for the mapping, per
 * RICKY_ORB_ANIMATION_PLAN.md section 12.
 */
export function mapVoiceStateToOrbState(voiceState: VoiceState): RickyOrbState {
  switch (voiceState) {
    case "listening":
    case "transcribing":
      return "listening";

    case "thinking":
      return "thinking";

    case "speaking":
      return "speaking";

    case "waiting_confirmation":
    case "interrupted":
      return "warning";

    case "error":
      return "error";

    case "muted":
      return "muted";

    case "idle":
    default:
      return "idle";
  }
}

// idle/muted use orbMain (the jagged-aura "hero" asset — see
// assets/GUI-SETS/GUI-SET-1.png) instead of orbIdle, which is a flat,
// simple circle meant for small contexts, not the dominant idle-screen orb.
const ORB_IMAGE_FOR_STATE: Record<RickyOrbState, string> = {
  idle: orbMain,
  listening: orbListening,
  thinking: orbThinking,
  speaking: orbSpeaking,
  warning: orbWarning,
  error: orbError,
  muted: orbMain,
};

export function RickyOrb({
  voiceState,
  size = "large",
  className = "",
}: RickyOrbProps) {
  const orbState = mapVoiceStateToOrbState(voiceState);
  const orbSrc = ORB_IMAGE_FOR_STATE[orbState];

  // Keep the raw voiceState class too (e.g. "transcribing", "interrupted")
  // so existing CSS overrides keyed on those still apply, while the
  // ricky-orb--<state> class drives the new ring animation system.
  const classes = [
    "ricky-orb",
    voiceState,
    `ricky-orb--${orbState}`,
    size === "small" ? "ricky-orb-small" : "",
    size === "floating" ? "ricky-orb-floating" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <div className="ricky-orb__ring ricky-orb__ring--outer" />
      <div className="ricky-orb__ring ricky-orb__ring--middle" />
      <div className="ricky-orb__ring ricky-orb__ring--inner" />

      <img
        src={orbSrc}
        alt="Ricky orb"
        className="ricky-orb-img"
        draggable={false}
      />
    </div>
  );
}
