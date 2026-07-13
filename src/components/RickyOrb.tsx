/** Ricky orb overlay with VoiceState-reactive visual states
 *  (idle/listening/thinking/speaking/muted) and Stop button.
 *  Used by both the main window (TopBar) and the companion orb
 *  (CompanionOrb.tsx → ?view=companion BrowserWindow).
 *  Context: agent_reports/2026-07-05_faza12-companion-orb.md */
import type { VoiceState } from "../lib/voiceState";
import rikiAvatar from "../../assets/Riki-avatar.png";

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

export function RickyOrb({
  voiceState,
  size = "large",
  className = "",
}: RickyOrbProps) {
  const orbState = mapVoiceStateToOrbState(voiceState);

  // Keep the raw voiceState class too (e.g. "transcribing", "interrupted")
  // so existing CSS overrides keyed on those still apply, while the
  // ricky-orb--<state> class drives animation/glow over the shared avatar.
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
        src={rikiAvatar}
        alt="Ricky avatar"
        className="ricky-orb-img"
        draggable={false}
      />
    </div>
  );
}
