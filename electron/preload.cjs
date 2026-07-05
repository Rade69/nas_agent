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
  // App
  quitApp: () => ipcRenderer.invoke("app:quit"),
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
});
