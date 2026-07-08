import { createActivityEvent, type ActivityEvent, type VoiceState } from "./voiceState";

type RealtimeRouterEvent = {
  type?: string;
  delta?: string;
  transcript?: string;
  error?: { message?: string };
};

export type RoutedRealtimeEvent = {
  voiceState?: VoiceState;
  activity?: ActivityEvent;
};

export function routeRealtimeEvent(event: RealtimeRouterEvent): RoutedRealtimeEvent {
  const rawType = event.type || "unknown";

  switch (rawType) {
    case "error":
      return {
        voiceState: "error",
        activity: createActivityEvent("error", "Realtime greška", event.error?.message, rawType),
      };
    case "input_audio_buffer.speech_started":
      return {
        voiceState: "listening",
        activity: createActivityEvent("voice", "Govor započet", undefined, rawType),
      };
    case "input_audio_buffer.speech_stopped":
      return {
        voiceState: "transcribing",
        activity: createActivityEvent("voice", "Govor završen", undefined, rawType),
      };
    case "conversation.item.input_audio_transcription.completed":
      return {
        voiceState: "thinking",
        activity: createActivityEvent("transcript", "Završen transkript", event.transcript, rawType),
      };
    case "response.created":
      return {
        voiceState: "thinking",
        activity: createActivityEvent("status", "Odgovor započet", undefined, rawType),
      };
    case "response.audio.delta":
    case "response.output_audio.delta":
      return { voiceState: "speaking" };
    case "response.output_audio.done":
    case "response.audio.done":
      return {
        voiceState: "idle",
        activity: createActivityEvent("voice", "Glasovni odgovor završen", undefined, rawType),
      };
    case "response.done":
      return {
        voiceState: "idle",
        activity: createActivityEvent("status", "Odgovor završen", undefined, rawType),
      };
    case "response.cancelled":
      return {
        voiceState: "interrupted",
        activity: createActivityEvent("status", "Odgovor prekinut", undefined, rawType),
      };
    default:
      return {};
  }
}
