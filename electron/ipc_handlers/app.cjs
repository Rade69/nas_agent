/** App lifecycle + tools-list IPC handlers — verbatim move from electron/main.cjs (R2d). */
const { app } = require("electron");
const { getMainWindow } = require("../core/window.cjs");
const { toolSpecs } = require("../core/realtimeToolSpecs.cjs");
const { cancelAllExecutions } = require("../services/pythonClient.cjs");

function handleToolsList() {
  return toolSpecs;
}

// Stop button ("stop everything"): ask the backend to flag all in-flight tools
// for cancellation. The renderer also tears down the Realtime voice session; the
// two are separate layers (SECURITY_HARDENING_PLAN.md section 25).
async function handleCancelAllExecutions() {
  return await cancelAllExecutions();
}

function handleAppQuit() {
  app.quit();
}

function handleAppMinimize() {
  const win = getMainWindow();
  if (win && !win.isDestroyed()) {
    win.minimize();
  }
}

function handleAppToggleMaximize() {
  const win = getMainWindow();
  if (!win || win.isDestroyed()) return;
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
}


module.exports = {
  handleToolsList,
  handleCancelAllExecutions,
  handleAppQuit,
  handleAppMinimize,
  handleAppToggleMaximize,
};
