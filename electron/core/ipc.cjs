const { ipcMain } = require("electron");
const { debugLog, summarize } = require("./debugLog.cjs");

// Context: agent_reports/2026-07-05_split-main-cjs-faza3.md
// Thin IPC wiring layer only. Handler bodies (business logic) stay in main.cjs for now —
// migrating that logic is a separate, larger phase (tool registry / Python backend), not this
// one. This module exists so the exposed IPC channel allowlist is auditable in a single file
// (Security Gate 0 / Security PR-1 "generic IPC zabrana" check — see
// docs/SECURITY_HARDENING_PLAN.md section 5) instead of scattered across a 1400+ line file.
function registerIpcHandlers(handlers) {
  for (const [channel, handler] of Object.entries(handlers)) {
    ipcMain.handle(channel, async (_event, payload) => {
      debugLog("[ipc]", channel, summarize(payload));
      try {
        return await handler(_event, payload);
      } catch (error) {
        debugLog("[ipc:error]", channel, String(error && error.message ? error.message : error));
        throw error;
      }
    });
  }
}

module.exports = { registerIpcHandlers };
