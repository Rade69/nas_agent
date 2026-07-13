/** Unit tests for RickyRealtimeClient DI seam and fake-object wiring (R0).
 *  Verifies that the dependency-injection seam is backward-compatible,
 *  that fake objects can be injected for deterministic testing, and
 *  that the production constructor signature (callbacks only) still works.
 *  Context: docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md */
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  RickyRealtimeClient,
  defaultRealtimeDeps,
  type RealtimeClientDeps,
} from "../realtime";
import type { RealtimeCallbacks } from "../realtimeTypes";

// ---------- fake/mock objects ----------

/** Fake RTCPeerConnection that records calls and emits no events. */
class FakePeerConnection {
  localDescription: RTCSessionDescriptionInit | null = null;
  remoteDescription: RTCSessionDescriptionInit | null = null;
  ontrack: ((event: unknown) => void) | null = null;
  closed = false;
  _tracks: unknown[] = [];

  addTrack(track: unknown): void {
    this._tracks.push(track);
  }
  createDataChannel(_label: string): FakeDataChannel {
    return new FakeDataChannel();
  }
  async createOffer(): Promise<RTCSessionDescriptionInit> {
    return { type: "offer", sdp: "fake-sdp-offer" };
  }
  async setLocalDescription(desc: RTCSessionDescriptionInit): Promise<void> {
    this.localDescription = desc;
  }
  async setRemoteDescription(desc: RTCSessionDescriptionInit): Promise<void> {
    this.remoteDescription = desc;
  }
  close(): void {
    this.closed = true;
  }
}

/** Fake RTCDataChannel. */
class FakeDataChannel {
  readyState: RTCDataChannelState = "open";
  _sent: string[] = [];
  _listeners: Map<string, Set<EventListener>> = new Map();

  addEventListener(type: string, listener: EventListener): void {
    const set = this._listeners.get(type) ?? new Set();
    set.add(listener);
    this._listeners.set(type, set);
  }
  send(data: string): void {
    this._sent.push(data);
  }
  close(): void {
    this.readyState = "closed";
  }
}

/** Fake MediaStream with a single fake audio track. */
class FakeMediaStream {
  id = "fake-stream";
  _tracks: FakeMediaStreamTrack[] = [];

  constructor() {
    this._tracks.push(new FakeMediaStreamTrack());
  }
  getAudioTracks(): FakeMediaStreamTrack[] {
    return this._tracks;
  }
  getTracks(): FakeMediaStreamTrack[] {
    return this._tracks;
  }
}

class FakeMediaStreamTrack {
  id = "fake-track";
  kind = "audio";
  readyState: MediaStreamTrackState = "live";
  enabled = true;
  stopped = false;

  stop(): void {
    this.stopped = true;
    this.readyState = "ended";
  }
}

/** Fake AudioContext — no actual audio processing. */
class FakeAudioContext {
  closed = false;
  sampleRate = 48000;

  createMediaStreamSource(_stream: unknown): FakeAudioNode {
    return new FakeAudioNode();
  }
  createAnalyser(): FakeAnalyserNode {
    return new FakeAnalyserNode();
  }
  async close(): Promise<void> {
    this.closed = true;
  }
}

class FakeAudioNode {
  connect(_dest: unknown): void {}
}

class FakeAnalyserNode {
  fftSize = 1024;
  smoothingTimeConstant = 0.72;
  frequencyBinCount = 512;

  getByteTimeDomainData(_arr: Uint8Array): void {}
  getByteFrequencyData(_arr: Uint8Array): void {}
}

class FakeAudioElement {
  autoplay = false;
  srcObject: MediaStream | null = null;
}

// ---------- helpers ----------

function noopCallbacks(): RealtimeCallbacks {
  return {
    onConnectionState: vi.fn(),
    onMood: vi.fn(),
    onVoiceState: vi.fn(),
    onStatus: vi.fn(),
    onActivity: vi.fn(),
    onTranscript: vi.fn(),
    onArtifact: vi.fn(),
    onMouthShape: vi.fn(),
    onMode: vi.fn(),
    onThumbnailReady: vi.fn(),
  };
}

function fakeDeps(
  overrides?: Partial<RealtimeClientDeps>,
): RealtimeClientDeps {
  return {
    createPeerConnection: () => new FakePeerConnection() as unknown as RTCPeerConnection,
    getUserMedia: vi.fn().mockResolvedValue(new FakeMediaStream() as unknown as MediaStream),
    fetch: vi.fn().mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("fake-sdp-answer"),
    } as unknown as Response),
    createAudioElement: () => new FakeAudioElement() as unknown as HTMLAudioElement,
    createAudioContext: () => new FakeAudioContext() as unknown as AudioContext,
    setTimeout: ((fn: () => void, _ms?: number) => {
      // Don't actually fire the idle timer in tests
      return 1;
    }) as RealtimeClientDeps["setTimeout"],
    clearTimeout: vi.fn() as RealtimeClientDeps["clearTimeout"],
    requestAnimationFrame: ((_cb: FrameRequestCallback) => 1) as RealtimeClientDeps["requestAnimationFrame"],
    cancelAnimationFrame: vi.fn() as RealtimeClientDeps["cancelAnimationFrame"],
    ...overrides,
  };
}

// Fake window.ricky for the IPC calls inside connect().
// We need to mock the global window.ricky object.
function mockWindowRicky() {
  const mock = {
    getToolSpecs: vi.fn().mockResolvedValue([]),
    createRealtimeToken: vi.fn().mockResolvedValue({
      value: "fake-ephemeral-token",
      sttLanguageHint: "sr",
    }),
  };
  (globalThis as Record<string, unknown>).window = {
    ricky: mock,
    requestAnimationFrame: vi.fn(),
    cancelAnimationFrame: vi.fn(),
  };
  return mock;
}

// ---------- tests ----------

describe("RickyRealtimeClient — DI seam", () => {
  it("constructs with only callbacks (backward-compatible)", () => {
    const client = new RickyRealtimeClient(noopCallbacks());
    expect(client).toBeInstanceOf(RickyRealtimeClient);
  });

  it("constructs with callbacks + partial deps", () => {
    const customClearTimeout = vi.fn() as RealtimeClientDeps["clearTimeout"];
    const client = new RickyRealtimeClient(noopCallbacks(), {
      clearTimeout: customClearTimeout,
    });
    expect(client).toBeInstanceOf(RickyRealtimeClient);
  });

  it("uses default deps when none provided", () => {
    // Verify defaultDeps matches the expected shape
    expect(defaultRealtimeDeps.createPeerConnection).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.getUserMedia).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.fetch).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.createAudioElement).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.createAudioContext).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.setTimeout).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.clearTimeout).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.requestAnimationFrame).toBeInstanceOf(Function);
    expect(defaultRealtimeDeps.cancelAnimationFrame).toBeInstanceOf(Function);
  });
});

describe("RickyRealtimeClient — fake connect", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("connect with fake deps calls getUserMedia, fetch, and creates peer", async () => {
    const w = mockWindowRicky();
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("fake-sdp-answer"),
    } as unknown as Response);
    const getUserMediaSpy = vi
      .fn()
      .mockResolvedValue(new FakeMediaStream() as unknown as MediaStream);
    const createPeerSpy = vi
      .fn()
      .mockReturnValue(new FakePeerConnection() as unknown as RTCPeerConnection);

    const deps = fakeDeps({
      fetch: fetchSpy as unknown as typeof fetch,
      getUserMedia: getUserMediaSpy,
      createPeerConnection: createPeerSpy,
    });

    const client = new RickyRealtimeClient(noopCallbacks(), deps);

    // connect() should not throw with fake deps
    await expect(client.connect()).resolves.toBeUndefined();

    // Verify dependencies were called
    expect(w.getToolSpecs).toHaveBeenCalledTimes(1);
    expect(w.createRealtimeToken).toHaveBeenCalledTimes(1);
    expect(getUserMediaSpy).toHaveBeenCalledTimes(1);
    expect(createPeerSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    // Verify fetch was called with the right URL and SDP
    const fetchUrl = fetchSpy.mock.calls[0][0];
    expect(fetchUrl).toBe("https://api.openai.com/v1/realtime/calls");
  });

  it("connect reports error state when fetch fails", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      fetch: vi.fn().mockRejectedValue(new Error("Network down")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onConnectionState).toHaveBeenCalledWith("error");
    expect(cbs.onMood).toHaveBeenCalledWith("error");
    expect(cbs.onVoiceState).toHaveBeenCalledWith("error");
    expect(cbs.onStatus).toHaveBeenCalledWith("Network down");
  });

  it("connect reports error when SDP response is not ok", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      fetch: vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: vi.fn().mockResolvedValue("Unauthorized"),
      } as unknown as Response),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onConnectionState).toHaveBeenCalledWith("error");
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("401"),
    );
  });
});

describe("RickyRealtimeClient — callback contract", () => {
  it("all callback properties are called during connect lifecycle", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    // connect() should call at minimum: onConnectionState("connecting"),
    // onMood, onVoiceState, onStatus, onActivity
    expect(cbs.onConnectionState).toHaveBeenCalledWith("connecting");
    expect(cbs.onMood).toHaveBeenCalledWith("thinking");
    expect(cbs.onVoiceState).toHaveBeenCalledWith("thinking");
    expect(cbs.onStatus).toHaveBeenCalled();
    expect(cbs.onActivity).toHaveBeenCalled();
  });

  it("disconnect returns to idle states", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    // Reset mock call history after connect
    vi.clearAllMocks();

    client.disconnect();

    expect(cbs.onConnectionState).toHaveBeenCalledWith("idle");
    expect(cbs.onMood).toHaveBeenCalledWith("idle");
    expect(cbs.onVoiceState).toHaveBeenCalledWith("idle");
  });
});
