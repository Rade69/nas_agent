/** Companion orb BrowserWindow manager (FAZA 12).
 *  Creates and manages a separate transparent always-on-top window that
 *  hosts the CompanionOrb renderer. Handles drag/position, context menu,
 *  tray, and VoiceState IPC forwarding.
 *  Context: agent_reports/2026-07-05_faza12-companion-orb.md */

const path = require("node:path");
const { BrowserWindow, nativeImage, screen, ipcMain, Tray, Menu, shell } = require("electron");
const { getSecureWebPreferences } = require("./secureWebPreferences.cjs");
const { getSettings } = require("../services/pythonClient.cjs");

// Native Electron Menu labels (tray + orb right-click) can't use react-i18next
// (main process, no React tree) — same reasoning as electron/ipc_handlers/
// realtime.cjs's LANGUAGE_CONFIG. de/es/fr are best-effort, not native-speaker
// confirmed, same disclaimer as every other locale in this project.
// Context: agent_reports/2026-07-13_companion-orb-menu-localization.md
const MENU_LABELS = {
  "sr-Latn": {
    trayShow: "Prikaži Ricky orb",
    trayHide: "Sakrij Ricky orb",
    trayOpenMain: "Otvori glavni prozor",
    trayQuit: "Zatvori Ricky",
    orbOpen: "Otvori Ricky",
    orbToggleVoice: "Uključi/isključi glas",
    orbLockPosition: "Zaključaj poziciju",
    orbQuit: "Zatvori Ricky",
  },
  en: {
    trayShow: "Show companion orb",
    trayHide: "Hide companion orb",
    trayOpenMain: "Open main window",
    trayQuit: "Quit Ricky",
    orbOpen: "Open Ricky",
    orbToggleVoice: "Toggle voice",
    orbLockPosition: "Lock position",
    orbQuit: "Close Ricky",
  },
  de: {
    trayShow: "Ricky-Orb anzeigen",
    trayHide: "Ricky-Orb ausblenden",
    trayOpenMain: "Hauptfenster öffnen",
    trayQuit: "Ricky beenden",
    orbOpen: "Ricky öffnen",
    orbToggleVoice: "Sprache umschalten",
    orbLockPosition: "Position sperren",
    orbQuit: "Ricky schließen",
  },
  es: {
    trayShow: "Mostrar orbe de Ricky",
    trayHide: "Ocultar orbe de Ricky",
    trayOpenMain: "Abrir ventana principal",
    trayQuit: "Salir de Ricky",
    orbOpen: "Abrir Ricky",
    orbToggleVoice: "Alternar voz",
    orbLockPosition: "Bloquear posición",
    orbQuit: "Cerrar Ricky",
  },
  fr: {
    trayShow: "Afficher l'orbe Ricky",
    trayHide: "Masquer l'orbe Ricky",
    trayOpenMain: "Ouvrir la fenêtre principale",
    trayQuit: "Quitter Ricky",
    orbOpen: "Ouvrir Ricky",
    orbToggleVoice: "Activer/désactiver la voix",
    orbLockPosition: "Verrouiller la position",
    orbQuit: "Fermer Ricky",
  },
};
const DEFAULT_MENU_LABELS = MENU_LABELS["sr-Latn"];

// Best-effort — falls back to the default language if settings can't be
// fetched (e.g. Python backend not up yet), same fail-open-to-default
// philosophy as realtime.cjs's LANGUAGE_CONFIG lookup. Never throws.
async function resolveMenuLabels() {
  try {
    const settings = await getSettings();
    return MENU_LABELS[settings?.interface_language] ?? DEFAULT_MENU_LABELS;
  } catch {
    return DEFAULT_MENU_LABELS;
  }
}

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
// Window must fit: orb (ORB_SIZE) + state pill + the Stop button below it.
// Wider than the orb so the Stop pill isn't clipped horizontally either.
const ORB_WIN_W = ORB_SIZE + 48; // 144
const ORB_WIN_H = ORB_SIZE + 64; // 160

function createCompanionWindow() {
  if (companionWindow && !companionWindow.isDestroyed()) return companionWindow;

  const cursorPoint = screen.getCursorScreenPoint();
  const display = screen.getDisplayNearestPoint(cursorPoint) || screen.getPrimaryDisplay();
  const { workArea } = display;
  const margin = 24;

  const win = new BrowserWindow({
    width: ORB_WIN_W,
    height: ORB_WIN_H,
    x: workArea.x + workArea.width - ORB_WIN_W - margin,
    y: workArea.y + workArea.height - ORB_WIN_H - margin - 40,
    // Electron defaults new windows to visible. createCompanionWindow() is
    // called unconditionally at app startup (main.cjs) regardless of Computer
    // Mode, so without this the orb popped up immediately on every launch —
    // showCompanion()/hideCompanion() (tied to set_mode) are what should
    // control visibility, not window creation itself.
    // Context: agent_reports/2026-07-10_orb-startup-visibility-fix.md
    show: false,
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
    webPreferences: getSecureWebPreferences(),
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
async function ensureTray() {
  if (tray) return tray;
  try {
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    tray.setToolTip("Ricky");
    const labels = await resolveMenuLabels();
    tray.setContextMenu(
      Menu.buildFromTemplate([
        { label: labels.trayShow, click: () => showCompanion() },
        { label: labels.trayHide, click: () => hideCompanion() },
        { type: "separator" },
        { label: labels.trayOpenMain, click: () => focusMainWindow() },
        { type: "separator" },
        { label: labels.trayQuit, click: () => quitApp() },
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
let toggleVoiceCallback = null;

function setMainWindowFocusCallback(cb) {
  focusMainWindowCallback = cb;
}
function setQuitAppCallback(cb) {
  quitAppCallback = cb;
}
function setToggleVoiceCallback(cb) {
  toggleVoiceCallback = cb;
}

function focusMainWindow() {
  if (focusMainWindowCallback) focusMainWindowCallback();
}

function quitApp() {
  if (quitAppCallback) quitAppCallback();
}

// Native context menu for the orb. Replaces the HTML menu, which overflowed the
// small orb window and got clipped — a native Menu.popup is not bounded by the
// window size. Reuses the same actions as the tray + companion IPC handlers.
async function showOrbContextMenu() {
  const win = companionWindow && !companionWindow.isDestroyed() ? companionWindow : null;
  const labels = await resolveMenuLabels();
  const menu = Menu.buildFromTemplate([
    { label: labels.orbOpen, click: () => focusMainWindow() },
    { label: labels.orbToggleVoice, click: () => toggleVoiceCallback && toggleVoiceCallback() },
    { type: "separator" },
    {
      label: labels.orbLockPosition,
      type: "checkbox",
      checked: lockedPosition,
      click: () => setLockedPosition(!lockedPosition),
    },
    { type: "separator" },
    { label: labels.orbQuit, click: () => quitApp() },
  ]);
  menu.popup(win ? { window: win } : {});
}

module.exports = {
  createCompanionWindow,
  showCompanion,
  hideCompanion,
  toggleCompanion,
  getCompanionWindow,
  forwardVoiceStateToCompanion,
  setLockedPosition,
  showOrbContextMenu,
  ensureTray,
  setMainWindowFocusCallback,
  setQuitAppCallback,
  setToggleVoiceCallback,
};
