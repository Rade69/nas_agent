const path = require("node:path");
const { BrowserWindow, nativeImage, screen, ipcMain, Tray, Menu, shell } = require("electron");

// Context: agent_reports/2026-07-05_faza12-companion-orb.md
// FAZA 12: Companion orb — a separate always-on-top transparent BrowserWindow
// that displays VoiceState and acts as a quick voice entry point. The orb does
// NOT run an audio pipeline; VoiceState is forwarded from the main window's
// Realtime client over IPC (voice:state-update). See
// docs/ARCHITECTURE_VOICE_FIRST_REVISED.md "Companion Orb kao voice entry point".

let companionWindow = null;
let tray = null;
let lockedPosition = false;

const ORB_SIZE = 96;

function createCompanionWindow() {
  if (companionWindow && !companionWindow.isDestroyed()) return companionWindow;

  const cursorPoint = screen.getCursorScreenPoint();
  const display = screen.getDisplayNearestPoint(cursorPoint) || screen.getPrimaryDisplay();
  const { workArea } = display;
  const margin = 24;

  const win = new BrowserWindow({
    width: ORB_SIZE,
    height: ORB_SIZE + 18, // extra room for the state pill
    x: workArea.x + workArea.width - ORB_SIZE - margin,
    y: workArea.y + workArea.height - ORB_SIZE - margin - 40,
    frame: false,
    transparent: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    backgroundColor: "#00000000",
    focusable: true,
    title: "Ricky Companion",
    webPreferences: {
      preload: path.join(__dirname, "..", "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  companionWindow = win;

  win.setAlwaysOnTop(true, "floating");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // Drag: the orb renderer calls startDrag on mousedown of the orb; this is
  // handled in-process via -webkit-app-region: drag, but we also support an
  // explicit IPC drag for the locked-position toggle flow below.
  win.on("moved", () => {
    if (lockedPosition) {
      // Restore last unlocked position if dragging is locked.
      // (Position lock is advisory — fully hard-locking would require ignoring
      // the moved event, which Electron doesn't support cleanly. MVP: the
      // renderer hides the drag affordance when locked.)
    }
  });

  win.on("closed", () => {
    companionWindow = null;
  });

  loadCompanionView(win);
  return win;
}

async function loadCompanionView(win) {
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    // Dev server: append ?view=companion to the same Vite entry.
    const separator = devUrl.includes("?") ? "&" : "?";
    await win.loadURL(`${devUrl}${separator}view=companion`);
  } else {
    // Production: load the built index.html with a query string. Electron's
    // loadFile supports a hash/query second argument.
    await win.loadFile(path.join(process.cwd(), "dist", "index.html"), {
      query: { view: "companion" },
    });
  }
}

function showCompanion() {
  const win = companionWindow || createCompanionWindow();
  if (win.isDestroyed()) {
    companionWindow = null;
    return;
  }
  if (!win.isVisible()) win.show();
  win.focus();
}

function hideCompanion() {
  if (companionWindow && !companionWindow.isDestroyed() && companionWindow.isVisible()) {
    companionWindow.hide();
  }
}

function toggleCompanion() {
  if (!companionWindow || companionWindow.isDestroyed()) {
    showCompanion();
    return;
  }
  if (companionWindow.isVisible()) {
    hideCompanion();
  } else {
    showCompanion();
  }
}

function getCompanionWindow() {
  return companionWindow;
}

// Forward VoiceState from the main window to the companion orb renderer.
function forwardVoiceStateToCompanion(state) {
  if (!companionWindow || companionWindow.isDestroyed()) return;
  // Use webContents.send so the orb renderer can subscribe via the preload's
  // onCompanionVoiceState callback. Channel name follows the dotted internal
  // event convention (voice.state_changed) per ARCHITECTURE_VOICE_FIRST_REVISED.
  companionWindow.webContents.send("companion:voice-state", state);
}

function setLockedPosition(locked) {
  lockedPosition = Boolean(locked);
  if (companionWindow && !companionWindow.isDestroyed()) {
    // Movable=false fully prevents user dragging on Windows; this is the
    // cleanest way to honor "lock position" from the context menu.
    companionWindow.setMovable(!lockedPosition);
  }
}

// Optional tray icon: gives users a persistent way to bring Ricky back even
// if the orb is hidden. Tray is created lazily on first companion creation.
function ensureTray() {
  if (tray) return tray;
  try {
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    tray.setToolTip("Ricky");
    tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: "Show companion orb", click: () => showCompanion() },
        { label: "Hide companion orb", click: () => hideCompanion() },
        { type: "separator" },
        { label: "Open main window", click: () => focusMainWindow() },
        { type: "separator" },
        { label: "Quit Ricky", click: () => quitApp() },
      ]),
    );
  } catch {
    // Tray creation can fail in headless / CI environments; non-fatal.
    tray = null;
  }
  return tray;
}

// Lazy-bound callbacks to avoid coupling companion module to main.cjs internals.
let focusMainWindowCallback = null;
let quitAppCallback = null;

function setMainWindowFocusCallback(cb) {
  focusMainWindowCallback = cb;
}
function setQuitAppCallback(cb) {
  quitAppCallback = cb;
}

function focusMainWindow() {
  if (focusMainWindowCallback) focusMainWindowCallback();
}

function quitApp() {
  if (quitAppCallback) quitAppCallback();
}

module.exports = {
  createCompanionWindow,
  showCompanion,
  hideCompanion,
  toggleCompanion,
  getCompanionWindow,
  forwardVoiceStateToCompanion,
  setLockedPosition,
  ensureTray,
  setMainWindowFocusCallback,
  setQuitAppCallback,
};
