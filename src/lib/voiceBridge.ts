/** RickyVoiceBridge — React-side voice klijent koji vozi Python Realtime voice
 *  (CR-3) preko `window.ricky` / QWebChannel, umjesto browser WebRTC-a.
 *
 *  Ima isti callback interfejs kao RickyRealtimeClient, pa App.tsx ne mora da
 *  zna da je WebRTC zamijenjen Python voice runtime-om. Mikrofon, VAD, STT,
 *  TTS, tool-calling i confirmation žive u Python-u; React samo prikazuje
 *  state/transcript i šalje komande (start/stop/dictation/text).
 *  Context: docs/NAS_AGENT_CANONICAL_REACT_QT_PYTHON_VOICE_MASTER_PLAN.md (CR-3) */

import type { RealtimeCallbacks, RickyConnectionState, RickyMood, MouthShape, TranscriptEntry } from "./realtimeTypes";
import type { VoiceState } from "./voiceState";

function mapStateToMood(state: VoiceState): RickyMood {
  switch (state) {
    case "listening":
      return "listening";
    case "transcribing":
    case "thinking":
      return "thinking";
    case "speaking":
      return "speaking";
    case "waiting_confirmation":
      return "working";
    case "error":
      return "error";
    default:
      return "idle";
  }
}

function mouthFromLevel(level: number): MouthShape {
  const open = Math.max(0, Math.min(1, level));
  return { open, width: 0.5 + 0.3 * open, round: 0.5, teeth: 0 };
}

function entry(role: TranscriptEntry["role"], text: string): TranscriptEntry {
  return {
    id: (crypto as Crypto).randomUUID ? crypto.randomUUID() : String(Date.now()),
    role,
    text,
    at: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
  };
}

export class RickyVoiceBridge {
  private cb: RealtimeCallbacks;
  private unsubs: Array<() => void> = [];
  private connected = false;

  constructor(callbacks: RealtimeCallbacks) {
    this.cb = callbacks;
  }

  async connect(): Promise<void> {
    const r = window.ricky;
    if (!r) {
      this.cb.onConnectionState("error");
      this.cb.onStatus("Native bridge nije dostupan.");
      return;
    }
    void r.debugLog?.("voiceBridge.connect -> startVoice");
    this.cb.onConnectionState("connecting");
    this.cb.onStatus("Povezujem Python voice...");

    this.unsubs.push(
      r.onVoiceStateChanged((s: unknown) => {
        const state = s as VoiceState;
        this.cb.onVoiceState(state);
        this.cb.onMood(mapStateToMood(state));
      }),
      r.onVoiceConnectedChanged((connected: unknown) => {
        this.connected = Boolean(connected);
        this.cb.onConnectionState((this.connected ? "connected" : "idle") as RickyConnectionState);
        if (this.connected) this.cb.onStatus("Ricky je uživo. Govori prirodno.");
      }),
      r.onVoiceUserTranscript((text: unknown) => {
        if (String(text).trim()) this.cb.onTranscript(entry("user", String(text)));
      }),
      r.onVoiceAssistantTranscript((text: unknown) => {
        if (String(text).trim()) this.cb.onTranscript(entry("ricky", String(text)));
      }),
      r.onVoiceInputLevel((level: unknown) => this.cb.onMouthShape(mouthFromLevel(Number(level)))),
      r.onVoiceError((msg: unknown) => {
        this.cb.onConnectionState("error");
        this.cb.onStatus(String(msg));
      }),
      r.onVoiceReconnecting(() => this.cb.onStatus("Ponovo povezujem...")),
    );

    await r.startVoice();
  }

  disconnect(): void {
    void window.ricky?.stopVoice?.();
    for (const unsub of this.unsubs) {
      try {
        unsub();
      } catch {
        /* noop */
      }
    }
    this.unsubs = [];
    this.connected = false;
    this.cb.onConnectionState("idle");
  }

  setDictationMode(_enabled: boolean): void {
    // CR-3 follow-up: Python session command (session.update). No-op za sada.
  }

  sendText(_text: string): void {
    // CR-3 follow-up: Python session inbox command.
  }

  notifyConfirmationResult(_toolName: string, _result: unknown): void {
    // CR-3 follow-up: rezultat UI retryja -> aktivna sesija (Python inbox).
  }
}
