/** VoiceState type definition and ActivityEvent factory.
 *  Defines the canonical voice lifecycle states (idle→listening→thinking→
 *  speaking) and the ActivityEvent shape consumed by ActivityTimeline.
 *  voiceStateLabel() returns a localized label for each state.
 *  Context: agent_reports/2026-07-05_faza8-voice-first-ui-refactor.md */
import i18n from "../i18n";

export type VoiceState =
  | "idle"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "waiting_confirmation"
  | "interrupted"
  | "muted"
  | "error";

export type ActivityEventKind = "voice" | "transcript" | "tool" | "status" | "error";

export type ActivityEvent = {
  id: string;
  kind: ActivityEventKind;
  title: string;
  detail?: string;
  at: string;
  rawType?: string;
};

export function createActivityEvent(
  kind: ActivityEventKind,
  title: string,
  detail?: string,
  rawType?: string,
): ActivityEvent {
  return {
    id: crypto.randomUUID(),
    kind,
    title,
    detail,
    at: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
    rawType,
  };
}

// Localized (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md). This is
// a plain function, not a component, so it can't use the useTranslation()
// hook — calls the i18next instance directly instead (valid react-i18next
// pattern for non-component code). The VoiceState enum itself stays
// language-independent per the doc's own rule (line 315-330).
export function voiceStateLabel(state: VoiceState): string {
  switch (state) {
    case "listening":
      return i18n.t("voice.state.listening");
    case "transcribing":
      return i18n.t("voice.state.transcribing");
    case "thinking":
      return i18n.t("voice.state.thinking");
    case "speaking":
      return i18n.t("voice.state.speaking");
    case "waiting_confirmation":
      return i18n.t("voice.state.waiting_confirmation");
    case "interrupted":
      return i18n.t("voice.state.interrupted");
    case "muted":
      return i18n.t("voice.state.muted");
    case "error":
      return i18n.t("voice.state.error");
    case "idle":
    default:
      return i18n.t("voice.state.idle");
  }
}