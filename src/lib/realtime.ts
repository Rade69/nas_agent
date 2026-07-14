/** WebRTC Realtime client — manages the OpenAI Realtime voice session
 *  lifecycle (connect, disconnect, sendText, setDictationMode, tool
 *  execution loop). Owns the PeerConnection, DataChannel, microphone
 *  stream, audio output analyser, and mouth-shape animation driver.
 *  Implements dictation-mode toggle and confirmation-bridge auto-retry.
 *  Context: agent_reports/2026-07-10_connect-latency-fix.md
 *  Context: agent_reports/2026-07-06_confirmation-bridge.md */
import type { RickyToolCall, RickyToolResult, RickyToolSpec } from "../vite-env";
import { routeRealtimeEvent } from "./realtimeEventRouter";
import { createActivityEvent } from "./voiceState";
import type { ActivityEvent, VoiceState } from "./voiceState";
import { silentMouthShape, smoothMouthShape, getSpeechBands, clamp01 } from "./realtimeMouthShape";
import { safeParseEvent, parseToolArguments, sanitizeToolResult, collectItemText, collectOutputText } from "./realtimeEventHelpers";
import type { MouthShape, RealtimeCallbacks, ResponseOutputItem, TranscriptEntry } from "./realtimeTypes";

export { createActivityEvent };
export type { ActivityEvent, VoiceState };
export type { RickyConnectionState, RickyMood, MouthShape, TranscriptEntry, RealtimeCallbacks } from "./realtimeTypes";

// ---------- DI seam (R0 — test harness) ----------
// Injected dependencies so tests can swap real browser APIs for fakes.
// Production: omit deps → browser defaults are used (unchanged behavior).
// Context: docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md

export type RealtimeClientDeps = {
  createPeerConnection: () => RTCPeerConnection;
  getUserMedia: (constraints?: MediaStreamConstraints) => Promise<MediaStream>;
  fetch: typeof fetch;
  createAudioElement: () => HTMLAudioElement;
  createAudioContext: () => AudioContext;
  setTimeout: (handler: (...args: unknown[]) => void, timeout?: number) => number;
  clearTimeout: (id: number | undefined) => void;
  requestAnimationFrame: (callback: FrameRequestCallback) => number;
  cancelAnimationFrame: (handle: number) => void;
};

/** Default dependencies that match the live browser environment. */
export const defaultRealtimeDeps: RealtimeClientDeps = {
  createPeerConnection: () => new RTCPeerConnection(),
  getUserMedia: (constraints) => navigator.mediaDevices.getUserMedia(constraints),
  fetch: (...args) => fetch(...args),
  createAudioElement: () => document.createElement("audio"),
  createAudioContext: () => new AudioContext(),
  setTimeout: (handler: (...args: unknown[]) => void, timeout?: number) =>
    setTimeout(handler, timeout as number) as unknown as number,
  clearTimeout: (id: number | undefined) => clearTimeout(id as unknown as number),
  requestAnimationFrame: (callback) => requestAnimationFrame(callback),
  cancelAnimationFrame: (handle) => cancelAnimationFrame(handle),
};
// ---------- end DI seam ----------

const realtimeUrl = "https://api.openai.com/v1/realtime/calls";

// FAZA S-4 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md S29): fail-closed mic idle
// timeout. An open microphone that is forgotten is a standing privacy risk, so
// the Realtime session auto-disconnects after this much inactivity (reset on
// every server event and text send).
const MIC_IDLE_TIMEOUT_MS = 5 * 60 * 1000;
const DEFAULT_CONNECT_TIMEOUT_MS = 30000;

// R2 — controlled reconnect & outbound queue
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_JITTER_MS = 250;
const MAX_OUTBOUND_QUEUE_SIZE = 50;
const MAX_OUTBOUND_QUEUE_AGE_MS = 10000;

export class RickyRealtimeClient {
  private pc: RTCPeerConnection | null = null;
  private dc: RTCDataChannel | null = null;
  private micStream: MediaStream | null = null;
  private deps: RealtimeClientDeps;
  private callbacks: RealtimeCallbacks;
  private currentAssistantText = "";
  private toolSpecs: RickyToolSpec[] = [];
  private toolRunning = false;
  private audioContext: AudioContext | null = null;
  private outputAnalyser: AnalyserNode | null = null;
  private outputMeterFrame = 0;
  private smoothedMouthShape: MouthShape = silentMouthShape();
  private idleTimer: ReturnType<RealtimeClientDeps["setTimeout"]> | null = null;
  // FAZA S-2 voice-path fix (agent_reports/2026-07-10_s2-voice-path-fix.md):
  // tracks whether a reads_external_content tool has succeeded this voice
  // session, so acting-tool calls can be forwarded with external_content_seen
  // for the backend's prompt-injection escalation (permission_engine.py).
  // Scoped per voice session (reset on connect/disconnect), which is MORE
  // conservative than the /agent/message runtime's per-message reset — once
  // tainted, stays escalated for the rest of this voice session.
  private externalContentSeen = false;
  private sttLanguageHint = "sr";

  // R1 — single-flight, timeout, generation guard
  private connectPromise: Promise<void> | null = null;
  private connectionGeneration = 0;
  private connectAbortController: AbortController | null = null;
  private connectTimeoutTimer: ReturnType<RealtimeClientDeps["setTimeout"]> | null = null;
  private connectTimeoutSignal: AbortSignal | null = null;
  private connectTimeoutAbortListener: (() => void) | null = null;

  // R2 — controlled reconnect, outbound queue, manual disconnect guard
  private reconnectAttempts = 0;
  private manualDisconnectRequested = false;
  private reconnectTimer: ReturnType<RealtimeClientDeps["setTimeout"]> | null = null;
  private outboundQueue: Array<{ event: Record<string, unknown>; createdAt: number }> = [];

  constructor(callbacks: RealtimeCallbacks, deps?: Partial<RealtimeClientDeps>) {
    this.callbacks = callbacks;
    this.deps = { ...defaultRealtimeDeps, ...deps };
  }

  // Reset the fail-closed idle timer; called on connect + any voice/text
  // activity. On expiry the mic session is torn down.
  private bumpIdleTimer(): void {
    if (this.idleTimer) this.deps.clearTimeout(this.idleTimer);
    this.idleTimer = this.deps.setTimeout(() => {
      this.callbacks.onStatus("Mikrofon ugašen zbog neaktivnosti.");
      this.callbacks.onActivity(createActivityEvent("status", "Mikrofon ugašen (idle timeout)"));
      this.disconnect();
    }, MIC_IDLE_TIMEOUT_MS);
  }

  // R1 — single-flight connect with timeout, abort, and generation guard.
  // If connect is already in progress, returns the same pending promise.
  // If already connected, does nothing.
  // R2 — resets reconnectAttempts, manualDisconnectRequested, and outboundQueue.
  // Context: docs/VOICE_COMMUNICATION_R1_BRIEF_FOR_PI.md
  // Context: docs/VOICE_COMMUNICATION_R2_BRIEF_FOR_PI.md
  async connect(options: { preserveOutboundQueue?: boolean } = {}): Promise<void> {
    if (this.connectPromise) return this.connectPromise;
    if (this.dc?.readyState === "open") return;

    this.connectAbortController?.abort();
    this.connectAbortController = new AbortController();
    const generation = ++this.connectionGeneration;
    const signal = this.connectAbortController.signal;

    this.externalContentSeen = false;
    this.manualDisconnectRequested = false;
    if (!options.preserveOutboundQueue) {
      this.reconnectAttempts = 0;
      this._cleanupOutboundQueue();
    }

    this.connectPromise = this._connectInternal(generation, signal);
    try {
      await this.connectPromise;
    } finally {
      if (this.connectionGeneration === generation) {
        this.connectPromise = null;
        this.connectAbortController = null;
      }
    }
  }

  private async _connectInternal(generation: number, signal: AbortSignal): Promise<void> {
    this.callbacks.onConnectionState("connecting");
    this.callbacks.onMood("thinking");
    this.callbacks.onVoiceState("thinking");
    this.callbacks.onStatus("Pripremam Realtime sesiju.");
    this.callbacks.onActivity(createActivityEvent("status", "Realtime sesija zatražena"));

    const deadline = this._timeoutPromise(DEFAULT_CONNECT_TIMEOUT_MS, signal, generation);

    try {
      const result = await Promise.race([
        this._doWebrtcConnect(signal, generation),
        deadline,
      ]);

      // Generation guard — stale if disconnect/abort happened during setup
      if (generation !== this.connectionGeneration) return;

      // Success path: DataChannel open will fire after setRemoteDescription.
      // If the promise resolved but we're still connecting (dc not open yet),
      // let the dc "open" handler take over.
      const connected = result as boolean;
      if (connected) {
        this.callbacks.onConnectionState("connected");
        this.callbacks.onMood("idle");
        this.callbacks.onVoiceState("idle");
        this.callbacks.onStatus("Ricky je uživo. Govori prirodno.");
        this.callbacks.onActivity(createActivityEvent("status", "WebRTC povezan"));
        this.bumpIdleTimer();
      }
    } catch (error) {
      if (generation !== this.connectionGeneration) return;
      this.cleanupConnectionResources();
      const message = this._classifyError(error);
      this.callbacks.onConnectionState("error");
      this.callbacks.onMood("error");
      this.callbacks.onVoiceState("error");
      this.callbacks.onStatus(message);
      this.callbacks.onActivity(createActivityEvent("error", "Realtime povezivanje nije uspjelo", message));
    } finally {
      this.clearConnectTimeout();
    }
  }

  // R1 — abort active connect attempt and invalidate generation
  // so stale async continuations cannot emit connected/error.
  // R2 — marks manual disconnect so reconnect is suppressed.
  disconnect(): void {
    this.manualDisconnectRequested = true;
    this._cleanupReconnectState();
    this._cleanupOutboundQueue();
    this.connectAbortController?.abort();
    this.connectionGeneration++;
    this.connectPromise = null;
    this.connectAbortController = null;
    this.cleanupConnectionResources();
    this.callbacks.onConnectionState("idle");
    this.callbacks.onMood("idle");
    this.callbacks.onVoiceState("idle");
    this.callbacks.onMouthShape(silentMouthShape());
  }

  private cleanupConnectionResources(): void {
    if (this.idleTimer) {
      this.deps.clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    this.dc?.close();
    this.pc?.close();
    this.micStream?.getTracks().forEach((track) => track.stop());
    this.stopOutputMeter();
    this.dc = null;
    this.pc = null;
    this.micStream = null;
    this.currentAssistantText = "";
    this.externalContentSeen = false;
    this.callbacks.onMouthShape(silentMouthShape());
  }

  private clearConnectTimeout(): void {
    if (this.connectTimeoutTimer) {
      this.deps.clearTimeout(this.connectTimeoutTimer);
      this.connectTimeoutTimer = null;
    }
    if (this.connectTimeoutSignal && this.connectTimeoutAbortListener) {
      this.connectTimeoutSignal.removeEventListener("abort", this.connectTimeoutAbortListener);
    }
    this.connectTimeoutSignal = null;
    this.connectTimeoutAbortListener = null;
  }

  // ---------- R2 — controlled reconnect ----------

  // Called on transport failure (PC failed/disconnected/closed, DC close/error).
  // Decides whether to reconnect or emit a terminal error.
  private _handleTransportFailure(reason: string): void {
    this.cleanupConnectionResources();

    if (this.manualDisconnectRequested) {
      this.callbacks.onConnectionState("idle");
      this.callbacks.onMood("idle");
      this.callbacks.onVoiceState("idle");
      this.callbacks.onMouthShape(silentMouthShape());
      return;
    }

    if (!this._shouldReconnect(reason)) {
      const msg = this._transportFailureMessage(reason);
      this.callbacks.onConnectionState("error");
      this.callbacks.onMood("error");
      this.callbacks.onVoiceState("error");
      this.callbacks.onStatus(msg);
      this.callbacks.onActivity(createActivityEvent("error", msg));
      this.callbacks.onMouthShape(silentMouthShape());
      this._cleanupOutboundQueue();
      return;
    }

    this._scheduleReconnect(reason);
  }

  // R2 — reconnect policy: only transient transport/network failures get retried.
  // Manual disconnect, quota, billing, auth, microphone, and timeout are permanent.
  private _shouldReconnect(reason: string): boolean {
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return false;
    // Transient transport reasons that can recover
    const transientReasons = ["failed", "disconnected", "dc-close", "dc-error"];
    return transientReasons.includes(reason);
  }

  private _transportFailureMessage(reason: string): string {
    switch (reason) {
      case "failed": return "WebRTC konekcija je pukla";
      case "disconnected": return "WebRTC konekcija je prekinuta";
      case "dc-close": return "Glasovni kanal je neočekivano zatvoren";
      case "dc-error": return "Greška u glasovnom kanalu";
      default: return `Transportna greška: ${reason}`;
    }
  }

  // R2 — schedule reconnect with exponential backoff and jitter.
  // Retries use the existing connect() path (new generation, new token, full setup).
  private _scheduleReconnect(reason: string): void {
    if (this.reconnectTimer || this.connectPromise) return;

    this.reconnectAttempts++;
    const attempt = this.reconnectAttempts;
    const baseDelay = RECONNECT_BASE_DELAY_MS * Math.pow(2, attempt - 1);
    const jitter = Math.floor(Math.random() * RECONNECT_JITTER_MS);
    const delay = baseDelay + jitter;

    const status = `Veza je prekinuta. Pokušavam ponovo ${attempt}/${MAX_RECONNECT_ATTEMPTS}…`;
    this.callbacks.onConnectionState("connecting");
    this.callbacks.onStatus(status);
    this.callbacks.onActivity(createActivityEvent("status", `Reconnect pokušaj ${attempt}/${MAX_RECONNECT_ATTEMPTS}`, reason));

    this.reconnectTimer = this.deps.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.manualDisconnectRequested) return;
      void this._executeReconnect();
    }, delay);
  }

  // R2 — execute a single reconnect attempt through the standard connect() path.
  private async _executeReconnect(): Promise<void> {
    try {
      await this.connect({ preserveOutboundQueue: true });
      if (this.dc?.readyState === "open") {
        this.reconnectAttempts = 0;
        this.callbacks.onStatus("Ponovo povezano.");
        this.callbacks.onActivity(createActivityEvent("status", "Reconnect uspješan"));
        this._flushOutboundQueue();
      } else {
        this._handleReconnectAttemptFailure("dc-error");
      }
    } catch {
      this._handleReconnectAttemptFailure("dc-error");
    }
  }

  private _handleReconnectAttemptFailure(reason: string): void {
    if (this.manualDisconnectRequested) return;
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      const msg = "Reconnect nije uspio. Pokreni glas ponovo.";
      this.callbacks.onConnectionState("error");
      this.callbacks.onMood("error");
      this.callbacks.onVoiceState("error");
      this.callbacks.onStatus(msg);
      this.callbacks.onActivity(createActivityEvent("error", msg, reason));
      this.callbacks.onMouthShape(silentMouthShape());
      this._cleanupOutboundQueue();
      return;
    }
    this._scheduleReconnect(reason);
  }

  // R2 — clean up reconnect timer and reset attempts.
  private _cleanupReconnectState(): void {
    if (this.reconnectTimer) {
      this.deps.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.reconnectAttempts = 0;
  }

  // ---------- R2 — outbound event queue ----------

  // R2 — enqueue an event for later delivery when the DataChannel is not open.
  // Respects max size (drops oldest) and max age (dropped on flush).
  private _enqueueEvent(event: Record<string, unknown>): void {
    const now = Date.now();
    if (this.outboundQueue.length >= MAX_OUTBOUND_QUEUE_SIZE) {
      this.outboundQueue.shift(); // drop oldest
    }
    this.outboundQueue.push({ event, createdAt: now });
  }

  // R2 — flush queued events through the DataChannel.
  // Drops stale events (older than MAX_OUTBOUND_QUEUE_AGE_MS).
  // Only sends if we're on the current generation and DC is open.
  private _flushOutboundQueue(): void {
    if (!this.dc || this.dc.readyState !== "open") return;
    const now = Date.now();
    const stale: typeof this.outboundQueue = [];
    const sendable: typeof this.outboundQueue = [];

    for (const item of this.outboundQueue) {
      if (now - item.createdAt > MAX_OUTBOUND_QUEUE_AGE_MS) {
        stale.push(item);
      } else {
        sendable.push(item);
      }
    }

    for (const item of sendable) {
      this.dc.send(JSON.stringify(item.event));
    }

    this.outboundQueue = [];
  }

  // R2 — clear the outbound queue (called on manual disconnect or permanent error).
  private _cleanupOutboundQueue(): void {
    this.outboundQueue = [];
  }

  // R1 — timeout promise that rejects with Serbian message.
  // Rejects on abort (disconnect during connect) so connect() callers do not
  // wait forever if the underlying browser/Electron operation is not abortable.
  private _timeoutPromise(ms: number, signal: AbortSignal, generation: number): Promise<never> {
    return new Promise<never>((_, reject) => {
      let settled = false;
      const rejectOnce = (error: Error) => {
        if (settled) return;
        settled = true;
        this.clearConnectTimeout();
        reject(error);
      };
      const onAbort = () => {
        rejectOnce(new Error("Povezivanje je prekinuto"));
      };
      this.connectTimeoutSignal = signal;
      this.connectTimeoutAbortListener = onAbort;
      signal.addEventListener("abort", onAbort, { once: true });
      this.connectTimeoutTimer = this.deps.setTimeout(() => {
        if (generation === this.connectionGeneration) {
          rejectOnce(new Error("Realtime povezivanje je isteklo"));
        } else {
          rejectOnce(new Error("Povezivanje je prekinuto"));
        }
      }, ms);
    });
  }

  // R1 — core WebRTC setup extracted from the old connect() body.
  // Returns true when setup completes successfully.
  private async _doWebrtcConnect(signal: AbortSignal, generation: number): Promise<boolean> {
    if (signal.aborted) throw new Error("Povezivanje je prekinuto");

    const pc = this.deps.createPeerConnection();
    this.pc = pc;
    const audio = this.deps.createAudioElement();
    audio.autoplay = true;

    // R1 — transport health: detect PeerConnection failures
    // R2 — route through _handleTransportFailure for controlled reconnect
    pc.onconnectionstatechange = () => {
      if (generation !== this.connectionGeneration) return;
      const state = pc.connectionState;
      if (state === "failed" || state === "disconnected" || state === "closed") {
        this._handleTransportFailure(state);
      }
    };

    pc.ontrack = (event) => {
      audio.srcObject = event.streams[0];
      this.startOutputMeter(event.streams[0]);
    };

    const [toolSpecs, token, micStream] = await Promise.all([
      window.ricky.getToolSpecs(),
      window.ricky.createRealtimeToken(),
      this.deps.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      }),
    ]);
    if (signal.aborted || generation !== this.connectionGeneration) throw new Error("Povezivanje je prekinuto");

    this.toolSpecs = toolSpecs;
    this.sttLanguageHint = token.sttLanguageHint ?? "sr";
    this.micStream = micStream;
    pc.addTrack(this.micStream.getAudioTracks()[0], this.micStream);

    const dc = pc.createDataChannel("oai-events");
    this.dc = dc;

    dc.addEventListener("open", () => {
      if (generation !== this.connectionGeneration) return;
      this.reconnectAttempts = 0;
      this.callbacks.onConnectionState("connected");
      this.callbacks.onMood("idle");
      this.callbacks.onVoiceState("idle");
      this.callbacks.onStatus("Ricky je uživo. Govori prirodno.");
      this.callbacks.onActivity(createActivityEvent("status", "WebRTC povezan"));
      this._flushOutboundQueue();
      this.bumpIdleTimer();
    });

    // R1 — transport health: DataChannel close/error
    // R2 — route through _handleTransportFailure for controlled reconnect
    const onDcClose = () => {
      if (generation !== this.connectionGeneration) return;
      this._handleTransportFailure("dc-close");
    };
    dc.addEventListener("close", onDcClose);
    dc.addEventListener("error", () => {
      if (generation !== this.connectionGeneration) return;
      this._handleTransportFailure("dc-error");
    });

    dc.addEventListener("message", (event) => {
      this.bumpIdleTimer();
      void this.handleServerEvent(event.data, generation);
    });

    if (signal.aborted || generation !== this.connectionGeneration) throw new Error("Povezivanje je prekinuto");

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    if (signal.aborted || generation !== this.connectionGeneration) throw new Error("Povezivanje je prekinuto");

    const sdpResponse = await this.deps.fetch(realtimeUrl, {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${token.value}`,
        "Content-Type": "application/sdp",
      },
      signal,
    });

    if (!sdpResponse.ok) {
      const body = await sdpResponse.text();
      throw new Error(`Realtime WebRTC call failed: ${sdpResponse.status} ${body}`);
    }

    if (signal.aborted || generation !== this.connectionGeneration) throw new Error("Povezivanje je prekinuto");

    await pc.setRemoteDescription({
      type: "answer",
      sdp: await sdpResponse.text(),
    });

    return true;
  }

  // R1 — classify errors into user-friendly Serbian messages.
  // Does NOT log API keys, tokens, SDP blobs, or auth headers.
  private _classifyError(error: unknown): string {
    const raw = error instanceof Error ? error.message : String(error ?? "Nepoznata greška");
    const lower = raw.toLowerCase();

    if (lower.includes("isteklo") || lower.includes("timeout")) {
      return "Realtime povezivanje je isteklo. Provjeri internet konekciju i pokušaj ponovo.";
    }
    if (lower.includes("prekinuto") || lower.includes("abort")) {
      return "Povezivanje je prekinuto.";
    }
    if (
      lower.includes("getaddrinfo failed") ||
      lower.includes("errno 11001") ||
      lower.includes("enotfound") ||
      lower.includes("eai_again") ||
      lower.includes("dns") ||
      lower.includes("fetch failed") ||
      lower.includes("network down")
    ) {
      return "Nema internet konekcije ili DNS ne radi. Provjeri mrežu i pokušaj ponovo.";
    }
    if (lower.includes("insufficient_quota") || lower.includes("quota")) {
      return "OpenAI kvota je potrošena. Provjeri stanje naloga i billing.";
    }
    if (lower.includes("billing") || lower.includes("payment")) {
      return "OpenAI billing problem. Provjeri stanje naloga.";
    }
    if (lower.includes("microphone") || lower.includes("notallowed") || lower.includes("permission denied")) {
      return "Mikrofon nije dostupan. Dozvoli pristup mikrofonu u sistemskim postavkama.";
    }
    if (lower.includes("notfound") || lower.includes("not found")) {
      return "Mikrofon nije pronađen. Poveži mikrofon i pokušaj ponovo.";
    }
    if (lower.includes("permission")) {
      return "Pristup mikrofonu je odbijen. Dozvoli pristup u postavkama.";
    }
    if (lower.includes("unauthorized") || (error instanceof Error && raw.includes("401"))) {
      return "Autentikacija nije uspjela. Provjeri API pristup.";
    }
    // Fallback: sanitize — strip overly long messages that may contain tokens/SDP
    if (raw.length > 200) return `Realtime greška: ${raw.slice(0, 200)}…`;
    return `Realtime greška: ${raw}`;
  }

  sendText(text: string): void {
    if (!this.dc || this.dc.readyState !== "open") {
      this.callbacks.onStatus("Poveži Rickyja prije slanja tekstualne poruke.");
      return;
    }
    this.bumpIdleTimer();
    this.callbacks.onTranscript(newEntry("user", text));
    this.callbacks.onVoiceState("thinking");
    this.callbacks.onActivity(createActivityEvent("transcript", "Tekstualna poruka", text));
    this.sendEvent({
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text }],
      },
    });
    this.sendEvent({ type: "response.create" });
  }

  // Dictation Mode (docs/RICKY_GUI_LOCALIZATION_PLAN.md "Cloud STT" backlog,
  // Phase 1): reuses the already-open Realtime session's built-in speech
  // transcription instead of a separate transcribe-only call or a second mic
  // capture — cheaper and simpler since dictation is only ever entered from an
  // active voice session (App.tsx onQuickCommand). The one piece that needs
  // explicit handling: turn_detection.create_response defaults to true, so
  // without this Ricky would try to speak a reply after every sentence the
  // user dictates. This toggles that off/on via session.update over the
  // existing data channel. `transcription` is re-sent alongside turn_detection
  // (not just once at session-mint time in realtime.cjs) because a session.update
  // that only specifies part of `audio.input` may replace the whole object
  // rather than deep-merge it — omitting transcription here risked silently
  // dropping it the moment dictation mode toggled, killing the exact
  // conversation.item.input_audio_transcription.completed events this whole
  // feature depends on. No-op if not connected (same guard pattern as sendText).
  // Context: agent_reports/2026-07-10_dictation-transcription-enable-fix.md
  setDictationMode(active: boolean): void {
    this.sendEvent({
      type: "session.update",
      session: {
        audio: {
          input: {
            turn_detection: {
              type: "semantic_vad",
              eagerness: "medium",
              create_response: !active,
              interrupt_response: true,
            },
            transcription: {
              model: "whisper-1",
              language: this.sttLanguageHint,
            },
          },
        },
      },
    });
  }

  // R1 — generation guard at the entry of every server event handler.
  // Stale DataChannel events from a previous connection are silently dropped.
  private async handleServerEvent(raw: string, generation: number): Promise<void> {
    if (generation !== this.connectionGeneration) return;

    const event = safeParseEvent(raw);
    if (!event.type) return;

    const routed = routeRealtimeEvent(event);
    if (routed.voiceState) this.callbacks.onVoiceState(routed.voiceState);
    if (routed.activity) this.callbacks.onActivity(routed.activity);

    if (event.type === "error") {
      this.callbacks.onMood("error");
      this.callbacks.onStatus(event.error?.message || "Realtime API returned an error.");
      return;
    }

    if (event.type === "input_audio_buffer.speech_started") {
      this.callbacks.onMood("listening");
      return;
    }

    if (event.type === "input_audio_buffer.speech_stopped") {
      this.callbacks.onMood("thinking");
      return;
    }

    if (event.type === "response.audio.delta" || event.type === "response.output_audio.delta") {
      this.callbacks.onMood("speaking");
      return;
    }

    if (event.type === "response.output_audio.done" || event.type === "response.audio.done") {
      if (!this.toolRunning) this.callbacks.onMood("idle");
      return;
    }

    if (
      event.type === "response.audio_transcript.delta" ||
      event.type === "response.output_audio_transcript.delta" ||
      event.type === "response.output_text.delta"
    ) {
      this.currentAssistantText += event.delta || "";
      return;
    }

    if (event.type === "conversation.item.input_audio_transcription.completed") {
      const transcript = event.transcript || collectItemText(event.item);
      if (transcript) this.callbacks.onTranscript(newEntry("user", transcript));
      return;
    }

    if (event.type === "response.done") {
      const output = event.response?.output || [];
      const spoken = this.currentAssistantText || output.map(collectOutputText).filter(Boolean).join("\n");
      if (spoken) this.callbacks.onTranscript(newEntry("ricky", spoken));
      this.currentAssistantText = "";

      const functionCalls = output.filter((item) => item.type === "function_call" && item.name && item.call_id);
      if (functionCalls.length > 0) {
        await this.executeFunctionCalls(functionCalls, generation);
      } else if (!this.toolRunning) {
        this.callbacks.onMood("idle");
        this.callbacks.onVoiceState("idle");
      }
    }
  }

  private async executeFunctionCalls(items: ResponseOutputItem[], generation: number): Promise<void> {
    if (generation !== this.connectionGeneration) return;

    this.toolRunning = true;
    this.callbacks.onMood("working");
    this.callbacks.onVoiceState("thinking");
    let shouldCreateResponse = false;

    for (const item of items) {
      const callId = item.call_id;
      const name = item.name;
      if (!callId || !name) continue;

      const parsedArgs = parseToolArguments(item.arguments || "{}");
      const knownTool = this.toolSpecs.some((tool) => tool.name === name);
      if (!knownTool) {
        await this.returnToolOutput(callId, {
          ok: false,
          error: `Alat nije dostupan: ${name}`,
        });
        shouldCreateResponse = true;
        continue;
      }

      this.callbacks.onTranscript(newEntry("tool", `Izvršavam ${name}`));
      this.callbacks.onActivity(createActivityEvent("tool", `Izvršavam ${name}`));
      if (name === "image_generate") {
        this.callbacks.onArtifact({
          title: "Generisanje slike",
          kind: "imageLoading",
          content: typeof parsedArgs.prompt === "string" ? parsedArgs.prompt : "Ricky generiše sliku.",
        });
      }
      if (name === "thumbnail_generate" || name === "thumbnail_edit") {
        const loadingResult = await window.ricky.executeTool({
          name: "thumbnail_loading_prepare",
          arguments: {
            ...parsedArgs,
            mode: name === "thumbnail_edit" ? "edit" : "generate",
          },
        } satisfies RickyToolCall);
        if (typeof loadingResult.runId === "string") parsedArgs.runId = loadingResult.runId;
        if (typeof loadingResult.targetId === "string") parsedArgs.targetId = loadingResult.targetId;
        if (loadingResult.artifact) this.callbacks.onArtifact(loadingResult.artifact);
      }
      const result = await window.ricky.executeTool({
        name,
        arguments: parsedArgs,
        // FAZA S-2 voice-path fix (agent_reports/2026-07-10_s2-voice-path-fix.md):
        // forward whether external content was already read this voice session,
        // so the backend can escalate acting tools (previously always omitted —
        // the voice path could never trigger this defense).
        context: { external_content_seen: this.externalContentSeen },
      } satisfies RickyToolCall);
      const executedSpec = this.toolSpecs.find((tool) => tool.name === name);
      if (executedSpec?.reads_external_content && result.ok) {
        this.externalContentSeen = true;
      }
      // FAZA 13/14 confirmation bridge: when the backend blocks a tool call
      // because it needs an approved confirmation, auto-propose one and tell
      // the model to wait instead of retrying blindly.
      // Context: docs/RICKY_CONFIRMATION_BRIDGE_BRIEF.md
      if (result.errorCode === "CONFIRMATION_REQUIRED") {
        const spec = this.toolSpecs.find((t) => t.name === name);
        const risk = (spec?.risk as string) || "high";
        await window.ricky.createConfirmation({
          action_name: name,
          payload: parsedArgs as Record<string, unknown>,
          risk_level: risk as "low" | "medium" | "high" | "critical",
          tool_name: name,
        });
        this.callbacks.onActivity(createActivityEvent("tool", `Čekam potvrdu: ${name}`));
        this.callbacks.onVoiceState("waiting_confirmation");
        await this.returnToolOutput(callId, {
          ok: false,
          waiting_confirmation: true,
          message: "Potrebna je tvoja potvrda prije izvršenja. Potvrdi u dijalogu.",
        } as RickyToolResult);
        // continue, not return: this may not be the last function_call in the
        // batch (e.g. set_mode + computer_type_text in one turn) — returning
        // here would skip every remaining call and never send it a
        // function_call_output, leaving the model waiting on a reply that
        // never comes. shouldCreateResponse=true so the model can actually
        // tell the user it needs approval instead of going silent.
        shouldCreateResponse = true;
        continue;
      }
      if (result.mode === "display" || result.mode === "computer") {
        this.callbacks.onMode(result.mode);
      }
      if (result.artifact) this.callbacks.onArtifact(result.artifact);
      // User-reported gap (2026-07-13): image_generate silently archived the
      // generated image into the app's internal data folder with no way to
      // choose the destination. Fire the native save dialog automatically
      // right when generation finishes — not gated behind a manual button
      // click, since the whole complaint was "he shouldn't decide the
      // location himself". Fire-and-forget: the voice/text turn already
      // completed (result.artifact above already showed the image), so this
      // doesn't block the conversation waiting on the user's dialog choice.
      // If they cancel, the internal copy is untouched — nothing is lost.
      if (name === "image_generate" && result.ok && typeof result.path === "string") {
        // Was silently swallowing errors (.catch(() => {})) — a failure here (e.g.
        // the source path fails saveThumbnailAs's dataDir allowlist check) looked
        // identical to "nothing happened" from the user's side. Log so a repeat
        // failure is diagnosable in devtools instead of invisible.
        void window.ricky
          .saveThumbnailAs({ path: result.path, suggestedName: "ricky-image.png" })
          .catch((error) => console.error("[image_generate] auto save-as dialog failed:", error));
      }
      if (result.thumbnailReady === true) this.callbacks.onThumbnailReady();
      if (result.silent !== true) shouldCreateResponse = true;
      await this.returnToolOutput(callId, result);
    }

    if (shouldCreateResponse) {
      if (generation !== this.connectionGeneration) {
        this.toolRunning = false;
        return;
      }
      this.callbacks.onVoiceState("thinking");
      this.sendEvent({ type: "response.create" });
    } else {
      this.callbacks.onVoiceState("idle");
    }
    this.toolRunning = false;
  }

  private async returnToolOutput(callId: string, result: RickyToolResult): Promise<void> {
    this.sendEvent({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: callId,
        output: JSON.stringify(sanitizeToolResult(result)),
      },
    });
  }

  // R2 — outbound event queue. If DataChannel is not open but the session is
  // alive (connected or connecting, not manually disconnected), queue the event
  // for later delivery. Never queue after manual disconnect or permanent error.
  private sendEvent(event: Record<string, unknown>): void {
    if (this.dc?.readyState === "open") {
      this.dc.send(JSON.stringify(event));
      return;
    }
    // Queue only if session is expected to recover (not manual disconnect)
    if (!this.manualDisconnectRequested && (this.pc || this.dc || this.connectPromise || this.reconnectTimer)) {
      this._enqueueEvent(event);
    }
  }

  private startOutputMeter(stream: MediaStream): void {
    this.stopOutputMeter();

    const audioContext = this.deps.createAudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.72;
    source.connect(analyser);

    this.audioContext = audioContext;
    this.outputAnalyser = analyser;

    const samples = new Uint8Array(analyser.fftSize);
    const frequencies = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(samples);
      analyser.getByteFrequencyData(frequencies);
      let total = 0;
      for (const sample of samples) {
        const centered = (sample - 128) / 128;
        total += centered * centered;
      }
      const rms = Math.sqrt(total / samples.length);
      const energy = clamp01(rms * 10.5);
      const bands = getSpeechBands(frequencies);

      // Simple realtime viseme approximation: low energy rounds the mouth,
      // mid energy opens it, high energy stretches it for consonants/ee sounds.
      const target: MouthShape = {
        open: clamp01(energy * 0.75 + bands.mid * 0.45 - bands.high * 0.16),
        width: clamp01(0.28 + bands.mid * 0.55 + bands.high * 0.74 - bands.low * 0.28),
        round: clamp01(0.08 + bands.low * 0.95 + energy * 0.1 - bands.high * 0.42),
        teeth: clamp01(bands.high * 1.4 + bands.mid * 0.25 - bands.low * 0.35),
      };

      this.smoothedMouthShape = smoothMouthShape(this.smoothedMouthShape, target, 0.36);
      this.callbacks.onMouthShape(this.smoothedMouthShape);
      this.outputMeterFrame = this.deps.requestAnimationFrame(tick);
    };
    tick();
  }

  private stopOutputMeter(): void {
    if (this.outputMeterFrame) {
      this.deps.cancelAnimationFrame(this.outputMeterFrame);
      this.outputMeterFrame = 0;
    }
    void this.audioContext?.close();
    this.audioContext = null;
    this.outputAnalyser = null;
    this.smoothedMouthShape = silentMouthShape();
  }
}

export function newEntry(role: TranscriptEntry["role"], text: string): TranscriptEntry {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    at: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
  };
}
