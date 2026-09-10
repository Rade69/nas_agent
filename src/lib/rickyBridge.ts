/** rickyBridge — QWebChannel adapter koji kreira `window.ricky` u PySide6 hostu.
 *  Zamjenjuje Electron preload: React komponente ne znaju da Electron ne postoji.
 *  Ako native bridge nije dostupan (Vite dev), instalira se eksplicitan mock.
 *  Context: docs/NAS_AGENT_CANONICAL_REACT_QT_PYTHON_VOICE_MASTER_PLAN.md (CR-2) */

type Bridge = Record<string, (...args: unknown[]) => unknown> & {
  [key: string]: any;
};

declare global {
  interface Window {
    qt?: { webChannelTransport?: unknown };
    QWebChannel?: new (transport: unknown, cb: (channel: any) => void) => void;
  }
}

function call(bridge: Bridge, method: string, ...args: unknown[]): Promise<unknown> {
  return new Promise((resolve) => {
    const fn = bridge[method];
    if (typeof fn !== "function") {
      resolve(null);
      return;
    }
    try {
      fn.call(bridge, ...args, (result: unknown) => resolve(result));
    } catch {
      resolve(null);
    }
  });
}

function subscribe(bridge: Bridge, signal: string, handler: (value: unknown) => void): () => void {
  const sig = bridge[signal];
  if (sig && typeof sig.connect === "function") {
    sig.connect(handler);
    return () => {
      try {
        sig.disconnect(handler);
      } catch {
        /* noop */
      }
    };
  }
  return () => {};
}

function installBridge(bridge: Bridge): void {
  void call(bridge, "debugLog", "native bridge installed");
  window.ricky = {
    // settings
    getSettings: () => call(bridge, "getSettings"),
    updateSettings: (p: unknown) => call(bridge, "updateSettings", p),
    // events
    listEvents: (since: unknown) => call(bridge, "listEvents", since),
    // plans
    listPlans: () => call(bridge, "listPlans"),
    createPlan: (p: unknown) => call(bridge, "createPlan", p),
    getPlan: (id: unknown) => call(bridge, "getPlan", id),
    updatePlan: (planId: unknown, payload: unknown) => call(bridge, "updatePlan", { planId, ...(payload as object) }),
    updatePlanStep: (planId: unknown, stepId: unknown, payload: unknown) =>
      call(bridge, "updatePlanStep", { planId, stepId, ...(payload as object) }),
    // confirmations
    listPendingConfirmations: () => call(bridge, "listPendingConfirmations"),
    createConfirmation: (p: unknown) => call(bridge, "createConfirmation", p),
    approveConfirmation: (id: unknown) => call(bridge, "approveConfirmation", id),
    rejectConfirmation: (id: unknown) => call(bridge, "rejectConfirmation", id),
    cancelConfirmation: (id: unknown) => call(bridge, "cancelConfirmation", id),
    publishConfirmationResult: (p: unknown) => call(bridge, "publishConfirmationResult", p),
    rewriteText: (p: unknown) => call(bridge, "rewriteText", JSON.stringify(p)),
    // tools
    getToolSpecs: () => call(bridge, "getToolSpecs"),
    executeTool: (p: unknown) => call(bridge, "executeTool", p),
    cancelAllExecutions: () => call(bridge, "cancelAllExecutions"),
    // screenshots
    listScreenshots: () => call(bridge, "listScreenshots"),
    deleteAllScreenshots: () => call(bridge, "deleteAllScreenshots"),
    // browser bridge
    getBrowserBridgeStatus: () => call(bridge, "getBrowserBridgeStatus"),
    startBrowserPairing: (browserKind: unknown) => call(bridge, "startBrowserPairing", { browserKind }),
    cancelBrowserPairing: (pairingId: unknown) => call(bridge, "cancelBrowserPairing", { pairingId }),
    // native window
    minimizeApp: () => call(bridge, "minimizeApp"),
    toggleMaximizeApp: () => call(bridge, "toggleMaximizeApp"),
    quitApp: () => call(bridge, "quitApp"),
    setModeFromUI: (mode: unknown) => call(bridge, "setModeFromUI", mode),
    debugLog: (msg: unknown) => call(bridge, "debugLog", String(msg)),
    addThumbnailReference: () => call(bridge, "addThumbnailReference"),
    saveThumbnailAs: (p: unknown) => call(bridge, "saveThumbnailAs", p),
    companionMenu: () => call(bridge, "companionMenu"),
    companionStop: () => call(bridge, "companionStop"),
    // voice
    createRealtimeToken: () => call(bridge, "createRealtimeToken"),
    startVoice: () => call(bridge, "startVoice"),
    stopVoice: () => call(bridge, "stopVoice"),
    // signals
    onCompanionVoiceState: (h: (v: unknown) => void) => subscribe(bridge, "companionVoiceState", h),
    onCompanionToggleVoice: (h: () => void) => subscribe(bridge, "companionToggleVoice", h),
    onConfirmationResult: (h: (v: unknown) => void) => subscribe(bridge, "confirmationResult", h),
    onKillSwitch: (h: () => void) => subscribe(bridge, "killSwitchTriggered", h),
    // voice signals (CR-3)
    onVoiceStateChanged: (h: (v: unknown) => void) => subscribe(bridge, "voiceStateChanged", h),
    onVoiceUserTranscript: (h: (v: unknown) => void) => subscribe(bridge, "voiceUserTranscript", h),
    onVoiceAssistantTranscript: (h: (v: unknown) => void) => subscribe(bridge, "voiceAssistantTranscript", h),
    onVoiceConnectedChanged: (h: (v: unknown) => void) => subscribe(bridge, "voiceConnectedChanged", h),
    onVoiceInputLevel: (h: (v: unknown) => void) => subscribe(bridge, "voiceInputLevelChanged", h),
    onVoiceOutputLevel: (h: (v: unknown) => void) => subscribe(bridge, "voiceOutputLevelChanged", h),
    onVoiceError: (h: (v: unknown) => void) => subscribe(bridge, "voiceError", h),
    onVoiceReconnecting: (h: () => void) => subscribe(bridge, "voiceReconnecting", h),
    onVoiceInputStreamOpened: (h: (v: unknown) => void) => subscribe(bridge, "voiceInputStreamOpened", h),
    onVoiceInputWarning: (h: (v: unknown) => void) => subscribe(bridge, "voiceInputWarning", h),
  } as any;
}

function installMockBridge(): void {
  // Vite dev / bez native hosta — React može da se renderuje, ali bridge je očigledno mock.
  window.ricky = {
    getSettings: async () => ({
      user_name: "Riley",
      agent_name: "Ricky",
      interface_language: "sr-Latn",
      quick_commands: [],
      realtime_model: "gpt-realtime-2.1-mini",
    }),
    updateSettings: async (p: any) => p,
    listEvents: async () => ({ events: [] }),
    listPlans: async () => ({ plans: [] }),
    listPendingConfirmations: async () => ({ confirmations: [] }),
    getToolSpecs: async () => [],
    getBrowserBridgeStatus: async () => ({ connected: false }),
    listScreenshots: async () => ({ screenshots: [] }),
    createRealtimeToken: async () => ({ value: "", expiresAt: null, sttLanguageHint: "sr" }),
    minimizeApp: async () => null,
    toggleMaximizeApp: async () => null,
    quitApp: async () => null,
    debugLog: () => null,
    onCompanionVoiceState: () => () => {},
    onCompanionToggleVoice: () => () => {},
    onConfirmationResult: () => () => {},
    onKillSwitch: () => () => {},
  } as any;
  // eslint-disable-next-line no-console
  console.warn("[rickyBridge] native bridge nedostupan — koristi se mock (dev).");
}

async function loadQWebChannelScript(): Promise<void> {
  if (window.QWebChannel) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "qrc:///qtwebchannel/qwebchannel.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("qwebchannel.js load failed"));
    document.head.appendChild(script);
  });
}

export async function initRickyBridge(): Promise<void> {
  if (!window.qt?.webChannelTransport) {
    installMockBridge();
    return;
  }
  try {
    await loadQWebChannelScript();
    await Promise.race([
      new Promise<void>((resolve) => {
        const QWebChannelCtor = window.QWebChannel as new (
          transport: unknown,
          cb: (channel: any) => void,
        ) => void;
        new QWebChannelCtor(window.qt!.webChannelTransport, (channel: any) => {
          installBridge(channel.objects.ricky as Bridge);
          resolve();
        });
      }),
      new Promise<void>((resolve) =>
        setTimeout(() => {
          if (!window.ricky) {
            installMockBridge();
          }
          resolve();
        }, 2500),
      ),
    ]);
  } catch {
    installMockBridge();
  }
}
