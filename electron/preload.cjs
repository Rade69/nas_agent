const { contextBridge, ipcRenderer } = require("electron");

// Allowlisted IPC surface. Each function maps to exactly one named channel — no
// generic ipcRenderer.invoke pass-through (Security Gate 0 / Security PR-1
// "generic IPC zabrana" check — see docs/SECURITY_HARDENING_PLAN.md section 5).
contextBridge.exposeInMainWorld("ricky", {
  // Voice / realtime
  createRealtimeToken: () => ipcRenderer.invoke("realtime:create-token"),
  // Tools
  executeTool: (toolCall) => ipcRenderer.invoke("tools:execute", toolCall),
  getToolSpecs: () => ipcRenderer.invoke("tools:list"),
  // Stop button: ask the backend to cancel every in-flight tool.
  cancelAllExecutions: () => ipcRenderer.invoke("tools:cancel-all"),
  // User-facing preferences (Settings panel). Context:
  // agent_reports/2026-07-11_settings-panel-foundation.md
  getSettings: () => ipcRenderer.invoke("settings:get"),
  updateSettings: (payload) => ipcRenderer.invoke("settings:update", payload),
  // Dictation Mode "Doradi" menu. Context:
  // agent_reports/2026-07-11_dictation-rewrite-menu.md
  rewriteText: (payload) => ipcRenderer.invoke("text:rewrite", payload),
  // Screenshot gallery/retention. Context:
  // agent_reports/2026-07-12_screenshot-privacy.md
  listScreenshots: () => ipcRenderer.invoke("screenshots:list"),
  deleteAllScreenshots: () => ipcRenderer.invoke("screenshots:delete-all"),
  // S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): opens a native
  // file picker — the only way a thumbnail reference image can be registered.
  addThumbnailReference: () => ipcRenderer.invoke("thumbnails:add-reference"),
  // User-reported gap (2026-07-13): export a generated thumbnail to a
  // user-chosen location via a native save dialog.
  saveThumbnailAs: (payload) => ipcRenderer.invoke("thumbnails:save-as", payload),
  // App
  quitApp: () => ipcRenderer.invoke("app:quit"),
  minimizeApp: () => ipcRenderer.invoke("app:minimize"),
  toggleMaximizeApp: () => ipcRenderer.invoke("app:toggle-maximize"),
  // FAZA 9: confirmations + plans (storage + state machine transitions only;
  // permission/risk layer that issues confirmations from tool execution is FAZA 10).
  listConfirmations: (filter = {}) => ipcRenderer.invoke("confirmations:list", filter),
  listPendingConfirmations: () => ipcRenderer.invoke("confirmations:pending"),
  createConfirmation: (payload) => ipcRenderer.invoke("confirmations:create", payload),
  approveConfirmation: (confirmationId) => ipcRenderer.invoke("confirmations:approve", confirmationId),
  rejectConfirmation: (confirmationId) => ipcRenderer.invoke("confirmations:reject", confirmationId),
  cancelConfirmation: (confirmationId) => ipcRenderer.invoke("confirmations:cancel", confirmationId),
  listPlans: () => ipcRenderer.invoke("plans:list"),
  createPlan: (payload) => ipcRenderer.invoke("plans:create", payload),
  getPlan: (planId) => ipcRenderer.invoke("plans:get", planId),
  updatePlan: (planId, payload) => ipcRenderer.invoke("plans:update", { planId, payload }),
  updatePlanStep: (planId, stepId, payload) =>
    ipcRenderer.invoke("plans:update-step", { planId, stepId, payload }),
  // FAZA 11: event bridge.
  listEvents: (since) => ipcRenderer.invoke("events:list", since),
  // FAZA 12: companion orb lifecycle + voice state forwarding.
  // onCompanionVoiceState is a subscribe-style listener (returns an unsubscribe
  // function); it is bound to the single named channel "companion:voice-state"
  // and does NOT expose a generic ipcRenderer.on pass-through.
  companionShow: () => ipcRenderer.invoke("companion:show"),
  companionHide: () => ipcRenderer.invoke("companion:hide"),
  companionToggle: () => ipcRenderer.invoke("companion:toggle"),
  companionUpdateVoiceState: (state) =>
    ipcRenderer.invoke("companion:voice-state-update", state),
  companionClick: () => ipcRenderer.invoke("companion:click"),
  companionOpenMain: () => ipcRenderer.invoke("companion:open-main"),
  companionToggleVoice: () => ipcRenderer.invoke("companion:toggle-voice"),
  companionToggleLock: (locked) => ipcRenderer.invoke("companion:toggle-lock", locked),
  companionStop: () => ipcRenderer.invoke("companion:stop"),
  companionMenu: () => ipcRenderer.invoke("companion:menu"),
  onCompanionVoiceState: (handler) => {
    const listener = (_event, state) => handler(state);
    ipcRenderer.on("companion:voice-state", listener);
    return () => {
      ipcRenderer.removeListener("companion:voice-state", listener);
    };
  },
  onCompanionToggleVoice: (handler) => {
    const listener = () => handler();
    ipcRenderer.on("companion:toggle-voice", listener);
    return () => {
      ipcRenderer.removeListener("companion:toggle-voice", listener);
    };
  },
  // FAZA S-4: global kill-switch. Main registers a global hotkey and pushes
  // this event so the renderer can tear down the voice/mic session immediately,
  // even when the window is not focused. Single named channel, no generic
  // ipcRenderer.on pass-through (Security Gate 0 preload surface check).
  onKillSwitch: (handler) => {
    const listener = () => handler();
    ipcRenderer.on("app:kill-switch", listener);
    return () => {
      ipcRenderer.removeListener("app:kill-switch", listener);
    };
  },
});
