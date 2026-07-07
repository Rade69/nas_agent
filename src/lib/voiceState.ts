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
      return "Slušam";
    case "transcribing":
      return "Obrađujem";
    case "thinking":
      return "Razmišljam";
    case "speaking":
      return "Govorim";
    case "waiting_confirmation":
      return "Čekam potvrdu";
    case "interrupted":
      return "Prekinuto";
    case "muted":
      return "Utišano";
    case "error":
      return "Greška";
    case "idle":
    default:
      return "Spreman";
  }
}