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
        activity: createActivityEvent("error", "Realtime error", event.error?.message, rawType),
      };
    case "input_audio_buffer.speech_started":
      return {
        voiceState: "listening",
        activity: createActivityEvent("voice", "Speech started", undefined, rawType),
      };
    case "input_audio_buffer.speech_stopped":
      return {
        voiceState: "transcribing",
        activity: createActivityEvent("voice", "Speech stopped", undefined, rawType),
      };
    case "conversation.item.input_audio_transcription.completed":
      return {
        voiceState: "thinking",
        activity: createActivityEvent("transcript", "Final transcript", event.transcript, rawType),
      };
    case "response.created":
      return {
        voiceState: "thinking",
        activity: createActivityEvent("status", "Response started", undefined, rawType),
      };
    case "response.audio.delta":
    case "response.output_audio.delta":
      return { voiceState: "speaking" };
    case "response.output_audio.done":
    case "response.audio.done":
      return {
        voiceState: "idle",
        activity: createActivityEvent("voice", "Audio response completed", undefined, rawType),
      };
    case "response.done":
      return {
        voiceState: "idle",
        activity: createActivityEvent("status", "Response completed", undefined, rawType),
      };
    case "response.cancelled":
      return {
        voiceState: "interrupted",
        activity: createActivityEvent("status", "Response interrupted", undefined, rawType),
      };
    default:
      return {};
  }
}