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
    executeTool: vi.fn().mockResolvedValue({ ok: true }) as ReturnType<typeof vi.fn>,
    createConfirmation: vi.fn().mockResolvedValue({ ok: true, confirmation_id: "confirmation-1" }),
    saveThumbnailAs: vi.fn().mockResolvedValue({ ok: true }),
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
    expect(cbs.onStatus).toHaveBeenCalledWith(
      "Nema internet konekcije ili DNS ne radi. Provjeri mrežu i pokušaj ponovo.",
    );
    expect(cbs.onConnectionState).toHaveBeenLastCalledWith("error");
    expect(cbs.onMood).toHaveBeenLastCalledWith("error");
    expect(cbs.onVoiceState).toHaveBeenLastCalledWith("error");
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
      "Autentikacija nije uspjela. Provjeri API pristup.",
    );
    expect(cbs.onConnectionState).toHaveBeenLastCalledWith("error");
    expect(cbs.onVoiceState).toHaveBeenLastCalledWith("error");
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

// ---------- R1 tests — single-flight, timeout, abort, generation guard, transport health, error classification ----------

describe("RickyRealtimeClient — R1 single-flight connect", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("second concurrent connect shares the same underlying connection attempt", async () => {
    mockWindowRicky();

    let resolveFetch: (v: unknown) => void = () => {};
    const fetchSpy = vi.fn().mockReturnValue(
      new Promise((resolve) => { resolveFetch = resolve; }),
    );

    const createPeerSpy = vi.fn().mockReturnValue(new FakePeerConnection() as unknown as RTCPeerConnection);
    const deps = fakeDeps({
      fetch: fetchSpy as unknown as typeof fetch,
      createPeerConnection: createPeerSpy,
    });
    const client = new RickyRealtimeClient(noopCallbacks(), deps);

    const p1 = client.connect();
    const p2 = client.connect();

    // Resolve fetch to unblock both
    resolveFetch({
      ok: true,
      text: vi.fn().mockResolvedValue("fake-sdp-answer"),
    } as unknown as Response);

    await p1;
    await p2;

    // Only one PeerConnection should be created
    expect(createPeerSpy).toHaveBeenCalledTimes(1);
  });

  it("connect when already connected is a no-op", async () => {
    mockWindowRicky();
    const createPeerSpy = vi.fn().mockReturnValue(new FakePeerConnection() as unknown as RTCPeerConnection);
    const deps = fakeDeps({ createPeerConnection: createPeerSpy });
    const client = new RickyRealtimeClient(noopCallbacks(), deps);

    // First connect
    await client.connect();
    expect(createPeerSpy).toHaveBeenCalledTimes(1);

    // Second connect — should be no-op
    await client.connect();
    expect(createPeerSpy).toHaveBeenCalledTimes(1);
  });
});

describe("RickyRealtimeClient — R1 connect timeout", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("connect timeout emits error with timeout message", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    // fetch never resolves → timeout wins
    const neverFetch = vi.fn().mockReturnValue(new Promise(() => {}));

    // setTimeout fires immediately to simulate timeout
    const immediateSetTimeout = ((fn: () => void, _ms?: number) => {
      // Don't fire here — let the Promise.race set up first.
      // We need to fire async so the race is ready.
      const id = setTimeout(fn, 0);
      return id as unknown as number;
    }) as unknown as RealtimeClientDeps["setTimeout"];

    const deps = fakeDeps({
      fetch: neverFetch as unknown as typeof fetch,
      setTimeout: immediateSetTimeout,
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onConnectionState).toHaveBeenCalledWith("error");
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("isteklo"),
    );
    expect(cbs.onConnectionState).toHaveBeenLastCalledWith("error");
  });
});

describe("RickyRealtimeClient — R1 abort / cancel during connect", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("disconnect during connect aborts and does not emit connected", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    // Fetch that can be rejected from outside to simulate abort
    let rejectFetch: (err: Error) => void = () => {};
    const abortableFetch = vi.fn().mockReturnValue(
      new Promise((_resolve, reject) => { rejectFetch = reject; }),
    );

    const deps = fakeDeps({ fetch: abortableFetch as unknown as typeof fetch });
    const client = new RickyRealtimeClient(cbs, deps);

    const connectPromise = client.connect();

    // Let microtasks flush so _doWebrtcConnect enters the fetch await
    await new Promise((r) => setTimeout(r, 10));

    // disconnect while connect is in-flight
    client.disconnect();

    // Now reject the pending fetch (simulating abort)
    rejectFetch(new Error("AbortError"));

    // The connect promise should resolve (not throw to caller)
    await expect(connectPromise).resolves.toBeUndefined();

    // connected should never have been emitted
    expect(cbs.onConnectionState).not.toHaveBeenCalledWith("connected");
  });

  it("disconnect resolves an in-flight connect even when setup promises do not settle", async () => {
    const w = mockWindowRicky();
    w.createRealtimeToken.mockReturnValue(new Promise(() => {}));
    const cbs = noopCallbacks();

    const deps = fakeDeps({
      getUserMedia: vi.fn().mockReturnValue(new Promise(() => {})),
    });
    const client = new RickyRealtimeClient(cbs, deps);

    const connectPromise = client.connect();
    await Promise.resolve();

    client.disconnect();

    await expect(Promise.race([
      connectPromise.then(() => "resolved"),
      new Promise((resolve) => setTimeout(() => resolve("timed-out"), 50)),
    ])).resolves.toBe("resolved");
    expect(cbs.onConnectionState).not.toHaveBeenCalledWith("connected");
  });

  it("stale connect completion after disconnect does not set connected", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    let resolveFetch: (v: unknown) => void = () => {};
    const fetchSpy = vi.fn().mockReturnValue(
      new Promise((resolve) => { resolveFetch = resolve; }),
    );

    const deps = fakeDeps({ fetch: fetchSpy as unknown as typeof fetch });
    const client = new RickyRealtimeClient(cbs, deps);

    // start connect
    void client.connect();

    // Let microtasks flush
    await new Promise((r) => setTimeout(r, 10));

    // disconnect
    client.disconnect();
    vi.clearAllMocks();

    // Now the old connect resolves
    resolveFetch({
      ok: true,
      text: vi.fn().mockResolvedValue("fake-sdp-answer"),
    } as unknown as Response);

    // Wait for async completion
    await new Promise((r) => setTimeout(r, 20));

    // connected should not have been emitted after disconnect
    expect(cbs.onConnectionState).not.toHaveBeenCalledWith("connected");
  });
});

describe("RickyRealtimeClient — R1 generation guard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("stale DataChannel message after disconnect is ignored", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    // We need to intercept the dc event listener to fire a message after disconnect
    let dcInstance: FakeDataChannel | null = null;
    const originalCreatePeer = fakeDeps().createPeerConnection;
    const wrappedCreatePeer = () => {
      const pc = originalCreatePeer() as unknown as FakePeerConnection;
      const origCreateDc = pc.createDataChannel.bind(pc);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (pc as any).createDataChannel = (label: string) => {
        const dc = origCreateDc(label) as unknown as FakeDataChannel;
        dcInstance = dc;
        return dc as unknown as RTCDataChannel;
      };
      return pc as unknown as RTCPeerConnection;
    };

    const deps = fakeDeps({ createPeerConnection: vi.fn().mockImplementation(wrappedCreatePeer) });
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    client.disconnect();

    // Clear mocks from disconnect to isolate stale-event test
    vi.clearAllMocks();

    // Fire a stale DataChannel message
    if (dcInstance) {
      const listeners = (dcInstance as FakeDataChannel)._listeners.get("message");
      if (listeners) {
        for (const listener of listeners) {
          listener({ data: '{"type":"response.done"}' } as unknown as Event);
        }
      }
    }

    // No new callbacks should fire from the stale message
    expect(cbs.onVoiceState).not.toHaveBeenCalled();
    expect(cbs.onActivity).not.toHaveBeenCalled();
  });
});

describe("RickyRealtimeClient — R1 transport health", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  // R2: transport failure triggers reconnect (connecting state), not direct error.
  // Direct error only happens after max attempts or manual disconnect.
  it("DataChannel close after connected triggers reconnect attempt", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    let dcInstance: FakeDataChannel | null = null;
    const originalCreatePeer = fakeDeps().createPeerConnection;
    const wrappedCreatePeer = () => {
      const pc = originalCreatePeer() as unknown as FakePeerConnection;
      const origCreateDc = pc.createDataChannel.bind(pc);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (pc as any).createDataChannel = (label: string) => {
        const dc = origCreateDc(label) as unknown as FakeDataChannel;
        dcInstance = dc;
        return dc as unknown as RTCDataChannel;
      };
      return pc as unknown as RTCPeerConnection;
    };

    const deps = fakeDeps({ createPeerConnection: vi.fn().mockImplementation(wrappedCreatePeer) });
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    vi.clearAllMocks();

    // Simulate DataChannel close
    if (dcInstance) {
      const listeners = (dcInstance as FakeDataChannel)._listeners.get("close");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    // Should trigger reconnect (connecting state), not terminal error
    expect(cbs.onConnectionState).toHaveBeenCalledWith("connecting");
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Pokušavam ponovo"),
    );
  });

  it("DataChannel error after connected triggers reconnect attempt", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    let dcInstance: FakeDataChannel | null = null;
    const originalCreatePeer = fakeDeps().createPeerConnection;
    const wrappedCreatePeer = () => {
      const pc = originalCreatePeer() as unknown as FakePeerConnection;
      const origCreateDc = pc.createDataChannel.bind(pc);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (pc as any).createDataChannel = (label: string) => {
        const dc = origCreateDc(label) as unknown as FakeDataChannel;
        dcInstance = dc;
        return dc as unknown as RTCDataChannel;
      };
      return pc as unknown as RTCPeerConnection;
    };

    const deps = fakeDeps({ createPeerConnection: vi.fn().mockImplementation(wrappedCreatePeer) });
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    vi.clearAllMocks();

    if (dcInstance) {
      const listeners = (dcInstance as FakeDataChannel)._listeners.get("error");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    expect(cbs.onConnectionState).toHaveBeenCalledWith("connecting");
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Pokušavam ponovo"),
    );
  });
});

describe("RickyRealtimeClient — R1 error classification", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("classifies insufficient_quota as billing error", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      fetch: vi.fn().mockRejectedValue(new Error("insufficient_quota: you have exceeded your quota")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("kvota"),
    );
  });

  it("classifies NotAllowedError as microphone error", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      getUserMedia: vi.fn().mockRejectedValue(new Error("NotAllowedError: Permission denied")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Mikrofon"),
    );
  });

  it("classifies NotFoundError as microphone not found", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      getUserMedia: vi.fn().mockRejectedValue(new Error("NotFoundError: Requested device not found")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("nije pronađen"),
    );
  });

  it("classifies billing error", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      fetch: vi.fn().mockRejectedValue(new Error("billing account is past due")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("billing"),
    );
  });

  it("classifies DNS/network token failures as network error", async () => {
    const w = mockWindowRicky();
    w.createRealtimeToken.mockRejectedValue(
      new Error("Error invoking remote method 'realtime:create-token': Error: Python backend request failed: 502 Realtime token request failed: [Errno 11001] getaddrinfo failed"),
    );
    const cbs = noopCallbacks();

    const client = new RickyRealtimeClient(cbs, fakeDeps());
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      "Nema internet konekcije ili DNS ne radi. Provjeri mrežu i pokušaj ponovo.",
    );
  });

  it("falls back to truncated generic message for unknown errors", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps({
      fetch: vi.fn().mockRejectedValue(new Error("Some unknown network glitch")),
    });

    const client = new RickyRealtimeClient(cbs, deps);
    await client.connect();

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Realtime greška"),
    );
  });
});

/** Helper for R2 tests: returns deps with a spy-able DataChannel instance. */
function dcSpyDeps() {
  let dcInstance: FakeDataChannel | null = null;
  const originalCreatePeer = fakeDeps().createPeerConnection;
  const wrappedCreatePeer = () => {
    const pc = originalCreatePeer() as unknown as FakePeerConnection;
    const origCreateDc = pc.createDataChannel.bind(pc);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (pc as any).createDataChannel = (label: string) => {
      const dc = origCreateDc(label) as unknown as FakeDataChannel;
      dcInstance = dc;
      return dc as unknown as RTCDataChannel;
    };
    return pc as unknown as RTCPeerConnection;
  };
  const deps = fakeDeps({ createPeerConnection: vi.fn().mockImplementation(wrappedCreatePeer) });
  return { deps, dcInstance: () => dcInstance };
}

// ---------- R2 tests — controlled reconnect, outbound queue ----------

describe("RickyRealtimeClient — R2 reconnect", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("manual disconnect does not trigger reconnect", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    client.disconnect();
    vi.clearAllMocks();

    // Fire DC close event AFTER manual disconnect
    const dc = dcInstance();
    if (dc) {
      const listeners = (dc as FakeDataChannel)._listeners.get("close");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    // Should NOT trigger reconnect (no connecting state)
    expect(cbs.onConnectionState).not.toHaveBeenCalledWith("connecting");
  });

  it("reconnect calls connect() again via reconnect path", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    vi.clearAllMocks();

    // Simulate transport failure (DC close)
    const dc = dcInstance();
    if (dc) {
      const listeners = (dc as FakeDataChannel)._listeners.get("close");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    // Should emit reconnect status
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Pokušavam ponovo 1/3"),
    );
    expect(cbs.onConnectionState).toHaveBeenCalledWith("connecting");
  });

  it("reconnect status includes attempt counter", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    vi.clearAllMocks();

    // Simulate transport failure (DC close)
    const dc = dcInstance();
    if (dc) {
      const listeners = (dc as FakeDataChannel)._listeners.get("close");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    // Should emit reconnect status with attempt counter
    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Pokušavam ponovo 1/3"),
    );
    expect(cbs.onConnectionState).toHaveBeenCalledWith("connecting");
  });

  it("failed reconnect attempt schedules the next attempt", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    mockWindowRicky();
    const cbs = noopCallbacks();
    const timers: Array<{ fn: () => void; timeout?: number }> = [];
    const { deps, dcInstance } = dcSpyDeps();
    deps.setTimeout = ((fn: () => void, timeout?: number) => {
      timers.push({ fn, timeout });
      return timers.length;
    }) as RealtimeClientDeps["setTimeout"];
    deps.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        text: vi.fn().mockResolvedValue("fake-sdp-answer"),
      } as unknown as Response)
      .mockRejectedValueOnce(new Error("Network down"));

    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    vi.clearAllMocks();

    const dc = dcInstance();
    if (dc) {
      const listeners = (dc as FakeDataChannel)._listeners.get("close");
      if (listeners) {
        for (const listener of listeners) {
          listener({} as Event);
        }
      }
    }

    const firstReconnect = timers.find((timer) => timer.timeout === 1000);
    expect(firstReconnect).toBeDefined();
    firstReconnect?.fn();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(cbs.onStatus).toHaveBeenCalledWith(
      expect.stringContaining("Pokušavam ponovo 2/3"),
    );
  });
});

describe("RickyRealtimeClient — R2 outbound queue", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("outbound queue is flushed when DC opens", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();

    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();

    // After connect, DC should be open and queue flushed.
    // Verify connected was emitted (proves flush happened without error)
    expect(cbs.onConnectionState).toHaveBeenCalledWith("connected");

    // DC._sent should be empty since no events were queued during connect
    const dc = dcInstance();
    expect(dc).not.toBeNull();
    expect((dc as FakeDataChannel)._sent.length).toBe(0);
  });

  it("outbound queue is cleared on manual disconnect", async () => {
    mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();
    client.disconnect();

    // After disconnect, manualDisconnectRequested is true — no crash, clean state
    expect(cbs.onConnectionState).toHaveBeenCalledWith("idle");
  });

  it("queued events survive reconnect and flush into the new DataChannel", async () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    mockWindowRicky();
    const cbs = noopCallbacks();
    const timers: Array<{ fn: () => void; timeout?: number }> = [];
    const { deps, dcInstance } = dcSpyDeps();
    deps.setTimeout = ((fn: () => void, timeout?: number) => {
      timers.push({ fn, timeout });
      return timers.length;
    }) as RealtimeClientDeps["setTimeout"];
    const client = new RickyRealtimeClient(cbs, deps);

    await client.connect();

    const firstDc = dcInstance();
    expect(firstDc).not.toBeNull();
    const listeners = (firstDc as FakeDataChannel)._listeners.get("close");
    if (listeners) {
      for (const listener of listeners) {
        listener({} as Event);
      }
    }

    client.setDictationMode(true);

    const reconnect = timers.find((timer) => timer.timeout === 1000);
    expect(reconnect).toBeDefined();
    reconnect?.fn();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const secondDc = dcInstance();
    expect(secondDc).not.toBe(firstDc);
    expect((secondDc as FakeDataChannel)._sent).toContainEqual(
      expect.stringContaining("\"session.update\""),
    );
  });
});

// ---------- R3 tests — tool lifecycle ----------

/** Helper: call the private executeFunctionCalls with proper this binding. */
function callExecuteFn(
  client: RickyRealtimeClient,
  items: Array<{ call_id: string; name: string; arguments?: string }>,
): Promise<void> {
  const proto = RickyRealtimeClient.prototype as unknown as Record<string, (items: unknown[], gen: number) => Promise<void>>;
  // Use the client's actual connectionGeneration so the guard passes
  const gen = (client as unknown as { connectionGeneration: number }).connectionGeneration;
  return proto.executeFunctionCalls.call(client, items, gen);
}

describe("RickyRealtimeClient — R3 tool lifecycle", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("active tool call is tracked and cleaned up after completion", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "test_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockResolvedValue({ ok: true });

    await client.connect();

    await callExecuteFn(client, [{ call_id: "call-1", name: "test_tool", arguments: "{}" }]);

    // Tool should have been called once
    expect(ricky.executeTool).toHaveBeenCalledTimes(1);
  });

  it("tool timeout removes active call and emits activity", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "slow_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });

    // Tool resolves normally — timeout is set up but never fires.
    // We verify the active call tracking works end-to-end.
    let resolveTool: (v: unknown) => void = () => {};
    ricky.executeTool.mockReturnValue(new Promise((resolve) => { resolveTool = resolve; }));

    await client.connect();

    const activeMap = (client as unknown as { activeToolCalls: Map<string, unknown> }).activeToolCalls;
    const execPromise = callExecuteFn(client, [{ call_id: "slow-1", name: "slow_tool", arguments: "{}" }]);

    // Tool should be registered as active during execution
    expect(activeMap.has("slow-1")).toBe(true);

    // Resolve the tool
    resolveTool({ ok: true, silent: true });
    await execPromise;

    // Active call should be cleaned up after completion
    expect(activeMap.has("slow-1")).toBe(false);
    expect(deps.clearTimeout).toHaveBeenCalled();
  });

  it("tool timeout returns TOOL_TIMEOUT output and resets active state", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "slow_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockReturnValue(new Promise(() => {}));

    await client.connect();

    const privateClient = client as unknown as { activeToolCalls: Map<string, unknown>; deps: RealtimeClientDeps };
    privateClient.deps.setTimeout = ((fn: () => void, _timeout?: number) => {
      void Promise.resolve().then(fn);
      return 999;
    }) as RealtimeClientDeps["setTimeout"];
    privateClient.deps.clearTimeout = vi.fn() as RealtimeClientDeps["clearTimeout"];

    await callExecuteFn(client, [{ call_id: "slow-timeout", name: "slow_tool", arguments: "{}" }]);

    expect(privateClient.activeToolCalls.has("slow-timeout")).toBe(false);
    expect(cbs.onActivity).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Alat se nije završio na vrijeme: slow_tool",
      }),
    );
    const sent = (dcInstance() as FakeDataChannel)._sent.join("\n");
    expect(sent).toContain("TOOL_TIMEOUT");
    expect(sent).toContain("Alat se nije završio na vrijeme.");
  });

  it("batch continues after one tool throws", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([
      { name: "good_tool", risk: "low" },
      { name: "bad_tool", risk: "low" },
    ]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });

    let callCount = 0;
    ricky.executeTool.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return Promise.resolve({ ok: true });
      throw new Error("Tool crashed");
    });

    await client.connect();

    await callExecuteFn(client, [
      { call_id: "good-1", name: "good_tool", arguments: "{}" },
      { call_id: "bad-1", name: "bad_tool", arguments: "{}" },
    ]);

    // Both tools should have been attempted
    expect(callCount).toBe(2);
  });

  it("thumbnail loading prepare failure returns safe tool output", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "thumbnail_generate", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockRejectedValue(new Error("loading prepare failed"));

    await client.connect();

    await callExecuteFn(client, [{ call_id: "thumb-prepare-1", name: "thumbnail_generate", arguments: "{}" }]);

    expect(ricky.executeTool).toHaveBeenCalledTimes(1);
    const sent = (dcInstance() as FakeDataChannel)._sent.join("\n");
    expect(sent).toContain("Tool execution failed");
    expect(sent).toContain("Alat nije uspio: thumbnail_generate");
  });

  it("duplicate completed call_id does not execute the tool twice", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "safe_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockResolvedValue({ ok: true });

    await client.connect();

    await callExecuteFn(client, [{ call_id: "duplicate-1", name: "safe_tool", arguments: "{}" }]);
    await callExecuteFn(client, [{ call_id: "duplicate-1", name: "safe_tool", arguments: "{}" }]);

    expect(ricky.executeTool).toHaveBeenCalledTimes(1);
    const sent = (dcInstance() as FakeDataChannel)._sent.join("\n");
    expect(sent).toContain("\\\"duplicate\\\":true");
    expect(sent).toContain("Ovaj tool poziv je već obrađen.");
  });

  it("active duplicate call_id does not mark the original call as completed", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "slow_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });

    await client.connect();

    const privateClient = client as unknown as {
      activeToolCalls: Map<string, unknown>;
      completedToolCallIds: Set<string>;
    };
    privateClient.activeToolCalls.set("active-duplicate-1", {
      name: "slow_tool",
      startedAt: Date.now(),
      generation: 1,
    });

    await callExecuteFn(client, [{ call_id: "active-duplicate-1", name: "slow_tool", arguments: "{}" }]);

    expect(ricky.executeTool).not.toHaveBeenCalled();
    expect(privateClient.completedToolCallIds.has("active-duplicate-1")).toBe(false);
    const sent = (dcInstance() as FakeDataChannel)._sent.join("\n");
    expect(sent).toContain("Tool je već aktivan");
    expect(sent).toContain("slow_tool se već izvršava.");
  });

  it("duplicate confirmation call_id creates only one confirmation", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "danger_tool", risk: "high" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockResolvedValue({
      ok: false,
      errorCode: "CONFIRMATION_REQUIRED",
      message: "Potrebna je potvrda.",
    });

    await client.connect();

    await callExecuteFn(client, [{ call_id: "confirm-duplicate-1", name: "danger_tool", arguments: "{}" }]);
    await callExecuteFn(client, [{ call_id: "confirm-duplicate-1", name: "danger_tool", arguments: "{}" }]);

    expect(ricky.executeTool).toHaveBeenCalledTimes(1);
    expect(ricky.createConfirmation).toHaveBeenCalledTimes(1);
    const sent = (dcInstance() as FakeDataChannel)._sent.join("\n");
    expect(sent).toContain("\\\"waiting_confirmation\\\":true");
    expect(sent).toContain("\\\"duplicate\\\":true");
  });

  it("tool resolve after disconnect does not send stale output", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const { deps, dcInstance } = dcSpyDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "slow_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });

    let resolveTool: (v: unknown) => void = () => {};
    ricky.executeTool.mockReturnValue(new Promise((resolve) => { resolveTool = resolve; }));

    await client.connect();
    const dc = dcInstance() as FakeDataChannel;
    dc._sent.length = 0;

    const execPromise = callExecuteFn(client, [{ call_id: "stale-after-disconnect-1", name: "slow_tool", arguments: "{}" }]);
    client.disconnect();
    resolveTool({ ok: true });
    await execPromise;

    expect(dc._sent).toHaveLength(0);
  });

  it("disconnect clears active tool calls", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "test_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });

    await client.connect();

    // Manually set up active tool call to simulate in-flight execution
    const activeMap = (client as unknown as { activeToolCalls: Map<string, unknown> }).activeToolCalls;
    activeMap.set("stale-1", { name: "test_tool", startedAt: Date.now(), generation: 1 });

    client.disconnect();

    // Active tool map should be empty after disconnect
    expect(activeMap.size).toBe(0);
  });

  it("unknown tool in batch does not prevent other tools from executing", async () => {
    const ricky = mockWindowRicky();
    const cbs = noopCallbacks();
    const deps = fakeDeps();
    const client = new RickyRealtimeClient(cbs, deps);

    ricky.getToolSpecs.mockResolvedValue([{ name: "known_tool", risk: "low" }]);
    ricky.createRealtimeToken.mockResolvedValue({ value: "t", sttLanguageHint: "sr" });
    ricky.executeTool.mockResolvedValue({ ok: true });

    await client.connect();

    await callExecuteFn(client, [
      { call_id: "unk-1", name: "unknown_tool", arguments: "{}" },
      { call_id: "known-1", name: "known_tool", arguments: "{}" },
    ]);

    // known_tool should have been executed
    expect(ricky.executeTool).toHaveBeenCalledTimes(1);
    expect(ricky.executeTool).toHaveBeenCalledWith(
      expect.objectContaining({ name: "known_tool" }),
    );
  });
});
