import type { RickyArtifact, RickyToolCall, RickyToolSpec } from "../vite-env";
import type { ActivityEvent, VoiceState } from "./voiceState";

export type RickyConnectionState = "idle" | "connecting" | "connected" | "error";
export type RickyMood = "idle" | "listening" | "thinking" | "speaking" | "working" | "error";

export type MouthShape = {
  open: number;
  width: number;
  round: number;
  teeth: number;
};

export type TranscriptEntry = {
  id: string;
  role: "user" | "ricky" | "system" | "tool";
  text: string;
  at: string;
};

export type RealtimeCallbacks = {
  onConnectionState: (state: RickyConnectionState) => void;
  onMood: (mood: RickyMood) => void;
  onMouthShape: (shape: MouthShape) => void;
  onTranscript: (entry: TranscriptEntry) => void;
  onArtifact: (artifact: RickyArtifact) => void;
  onMode: (mode: "display" | "computer") => void;
  onStatus: (message: string) => void;
  onVoiceState: (state: VoiceState) => void;
  onActivity: (event: ActivityEvent) => void;
  onThumbnailReady: () => void;
};

// Internal-only types for cross-file use (not re-exported from realtime.ts)
export type ServerEvent = {
  type?: string;
  delta?: string;
  transcript?: string;
  response?: {
    output?: ResponseOutputItem[];
  };
  item?: {
    type?: string;
    role?: string;
    content?: Array<{ transcript?: string; text?: string }>;
  };
  error?: {
    message?: string;
  };
};

export type ResponseOutputItem = {
  type?: string;
  name?: string;
  call_id?: string;
  arguments?: string;
  content?: Array<{ transcript?: string; text?: string }>;
};