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

export function voiceStateLabel(state: VoiceState): string {
  switch (state) {
    case "listening":
      return "Listening";
    case "transcribing":
      return "Transcribing";
    case "thinking":
      return "Thinking";
    case "speaking":
      return "Speaking";
    case "waiting_confirmation":
      return "Waiting confirmation";
    case "interrupted":
      return "Interrupted";
    case "muted":
      return "Muted";
    case "error":
      return "Error";
    case "idle":
    default:
      return "Ready";
  }
}