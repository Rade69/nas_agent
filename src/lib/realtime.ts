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

const realtimeUrl = "https://api.openai.com/v1/realtime/calls";

// FAZA S-4 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md S29): fail-closed mic idle
// timeout. An open microphone that is forgotten is a standing privacy risk, so
// the Realtime session auto-disconnects after this much inactivity (reset on
// every server event and text send).
const MIC_IDLE_TIMEOUT_MS = 5 * 60 * 1000;

export class RickyRealtimeClient {
  private pc: RTCPeerConnection | null = null;
  private dc: RTCDataChannel | null = null;
  private micStream: MediaStream | null = null;
  private callbacks: RealtimeCallbacks;
  private currentAssistantText = "";
  private toolSpecs: RickyToolSpec[] = [];
  private toolRunning = false;
  private audioContext: AudioContext | null = null;
  private outputAnalyser: AnalyserNode | null = null;
  private outputMeterFrame = 0;
  private smoothedMouthShape: MouthShape = silentMouthShape();
  private idleTimer: ReturnType<typeof setTimeout> | null = null;
  // FAZA S-2 voice-path fix (agent_reports/2026-07-10_s2-voice-path-fix.md):
  // tracks whether a reads_external_content tool has succeeded this voice
  // session, so acting-tool calls can be forwarded with external_content_seen
  // for the backend's prompt-injection escalation (permission_engine.py).
  // Scoped per voice session (reset on connect/disconnect), which is MORE
  // conservative than the /agent/message runtime's per-message reset — once
  // tainted, stays escalated for the rest of this voice session.
  private externalContentSeen = false;

  constructor(callbacks: RealtimeCallbacks) {
    this.callbacks = callbacks;
  }

  // Reset the fail-closed idle timer; called on connect + any voice/text
  // activity. On expiry the mic session is torn down.
  private bumpIdleTimer(): void {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => {
      this.callbacks.onStatus("Mikrofon ugašen zbog neaktivnosti.");
      this.callbacks.onActivity(createActivityEvent("status", "Mikrofon ugašen (idle timeout)"));
      this.disconnect();
    }, MIC_IDLE_TIMEOUT_MS);
  }

  async connect(): Promise<void> {
    if (this.pc) return;
    this.externalContentSeen = false;
    this.callbacks.onConnectionState("connecting");
    this.callbacks.onMood("thinking");
    this.callbacks.onVoiceState("thinking");
    this.callbacks.onStatus("Pripremam Realtime sesiju.");
    this.callbacks.onActivity(createActivityEvent("status", "Realtime sesija zatražena"));

    try {
      const pc = new RTCPeerConnection();
      const audio = document.createElement("audio");
      audio.autoplay = true;

      pc.ontrack = (event) => {
        audio.srcObject = event.streams[0];
        this.startOutputMeter(event.streams[0]);
      };

      // These three were previously awaited one after another even though none
      // depends on another's result — createRealtimeToken() alone is a network
      // round trip (Electron -> Python backend -> OpenAI), so serializing it
      // behind getToolSpecs() and in front of getUserMedia() added avoidable
      // latency to every connect(). Running them concurrently cuts the wait to
      // roughly the slowest one instead of the sum of all three.
      // Context: agent_reports/2026-07-10_connect-latency-fix.md
      const [toolSpecs, token, micStream] = await Promise.all([
        window.ricky.getToolSpecs(),
        window.ricky.createRealtimeToken(),
        navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        }),
      ]);
      this.toolSpecs = toolSpecs;
      this.micStream = micStream;
      pc.addTrack(this.micStream.getAudioTracks()[0], this.micStream);

      const dc = pc.createDataChannel("oai-events");
      dc.addEventListener("open", () => {
        this.callbacks.onConnectionState("connected");
        this.callbacks.onMood("idle");
        this.callbacks.onVoiceState("idle");
        this.callbacks.onStatus("Ricky je uživo. Govori prirodno.");
        this.callbacks.onActivity(createActivityEvent("status", "WebRTC povezan"));
        this.bumpIdleTimer();
      });
      dc.addEventListener("message", (event) => {
        this.bumpIdleTimer();
        void this.handleServerEvent(event.data);
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const sdpResponse = await fetch(realtimeUrl, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${token.value}`,
          "Content-Type": "application/sdp",
        },
      });

      if (!sdpResponse.ok) {
        throw new Error(`Realtime WebRTC call failed: ${sdpResponse.status} ${await sdpResponse.text()}`);
      }

      await pc.setRemoteDescription({
        type: "answer",
        sdp: await sdpResponse.text(),
      });

      this.pc = pc;
      this.dc = dc;
    } catch (error) {
      this.callbacks.onConnectionState("error");
      this.callbacks.onMood("error");
      this.callbacks.onVoiceState("error");
      this.callbacks.onStatus(error instanceof Error ? error.message : String(error));
      this.disconnect();
    }
  }

  disconnect(): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
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
    this.callbacks.onConnectionState("idle");
    this.callbacks.onMood("idle");
    this.callbacks.onVoiceState("idle");
    this.callbacks.onMouthShape(silentMouthShape());
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

  private async handleServerEvent(raw: string): Promise<void> {
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
        await this.executeFunctionCalls(functionCalls);
      } else if (!this.toolRunning) {
        this.callbacks.onMood("idle");
        this.callbacks.onVoiceState("idle");
      }
    }
  }

  private async executeFunctionCalls(items: ResponseOutputItem[]): Promise<void> {
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
      if (result.thumbnailReady === true) this.callbacks.onThumbnailReady();
      if (result.silent !== true) shouldCreateResponse = true;
      await this.returnToolOutput(callId, result);
    }

    if (shouldCreateResponse) {
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

  private sendEvent(event: Record<string, unknown>): void {
    if (this.dc?.readyState === "open") {
      this.dc.send(JSON.stringify(event));
    }
  }

  private startOutputMeter(stream: MediaStream): void {
    this.stopOutputMeter();

    const audioContext = new AudioContext();
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
      this.outputMeterFrame = window.requestAnimationFrame(tick);
    };
    tick();
  }

  private stopOutputMeter(): void {
    if (this.outputMeterFrame) {
      window.cancelAnimationFrame(this.outputMeterFrame);
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
