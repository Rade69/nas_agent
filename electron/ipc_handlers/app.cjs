/** App lifecycle + tools-list IPC handlers — verbatim move from electron/main.cjs (R2d). */
const { app } = require("electron");
const { getMainWindow } = require("../core/window.cjs");
const { toolSpecs } = require("../core/realtimeToolSpecs.cjs");

function handleToolsList() {
  return toolSpecs;
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


module.exports = { handleToolsList, handleAppQuit, handleAppMinimize, handleAppToggleMaximize };
