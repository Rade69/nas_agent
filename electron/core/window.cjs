/** Main BrowserWindow factory and lifecycle.
 *  createWindow, setWindowMode (display/computer mini-window toggle),
 *  and getMainWindow singleton accessor. Window is frameless with
 *  -webkit-app-region drag zones for custom title-bar behavior.
 *  Context: agent_reports/2026-07-11_i18n-foundation.md (rund 3, window drag saga) */

const path = require("node:path");
const { BrowserWindow, nativeImage, screen } = require("electron");
const { getSecureWebPreferences } = require("./secureWebPreferences.cjs");

let mainWindow = null;
// Separate mini window for Computer Mode. We do NOT resize the main window
// down to 190x190 because a frameless + transparent Electron window on
// Windows gets spontaneously re-maximized by DWM ~2s after setBounds(), no
// matter what combination of setMaximizable(false) / setAlwaysOnTop / opacity
// is applied. A
// dedicated mini BrowserWindow never enters the maximized state, so DWM has
// nothing to "restore" — the spontaneous maximize cannot happen.
let miniWindow = null;
let savedNormalBounds = null;
let savedWasMaximized = false;

function buildMiniDevUrl(devUrl) {
  const url = new URL(devUrl);
  url.searchParams.set("window", "mini");
  url.searchParams.set("mode", "computer");
  return url.toString();
}

// Context: agent_reports/2026-07-05_split-main-cjs-faza3.md
// beforeShow is dependency-injected (not a direct ensureData()/clearStartupLoadingThumbnails()
// call) so this module stays decoupled from the DB/storage layer, which is still owned by main.cjs.
async function createWindow({ beforeShow } = {}) {
  if (beforeShow) await beforeShow();
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1120,
    minHeight: 700,
    title: "Ricky",
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    icon: nativeImage.createEmpty(),
    webPreferences: getSecureWebPreferences(),
  });
  mainWindow = win;
  win.center();

  win.webContents.session.setPermissionRequestHandler((_webContents, permission, callback) => {
    callback(permission === "media");
  });

  if (process.env.RICKY_DEBUG_CONSOLE) {
    win.webContents.on("console-message", (_event, level, message, line, sourceId) => {
      console.log(`[renderer] ${message} (${sourceId}:${line})`);
    });
    win.webContents.session.webRequest.onErrorOccurred((details) => {
      console.log(`[network-error] ${details.method} ${details.url} -> ${details.error}`);
    });
  }

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    await win.loadURL(devUrl);
  } else {
    await win.loadFile(path.join(process.cwd(), "dist", "index.html"));
  }

  return win;
}

// Computer Mode shows a small floating controller in the bottom-left corner.
// Instead of resizing the main window (which triggers DWM's spontaneous
// re-maximize bug on frameless transparent windows), we hide the main window
// and create/show a dedicated mini window. Display mode reverses this.
function setWindowMode(mode) {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  if (mode === "computer") {
    savedNormalBounds = mainWindow.getNormalBounds();
    savedWasMaximized = mainWindow.isMaximized();
    // Block DWM from spontaneously re-maximizing the hidden main window.
    // setMaximizable(false) on the hidden window keeps restore predictable.
    mainWindow.setMaximizable(false);
    mainWindow.hide();

    const cursorPoint = screen.getCursorScreenPoint();
    const targetDisplay = screen.getDisplayNearestPoint(cursorPoint) || screen.getPrimaryDisplay();
    const { workArea } = targetDisplay;
    const miniSize = 236;
    const margin = 18;
    const miniBounds = {
      x: workArea.x + margin,
      y: workArea.y + workArea.height - miniSize - margin,
      width: miniSize,
      height: miniSize,
    };

    if (miniWindow && !miniWindow.isDestroyed()) {
      miniWindow.show();
    } else {
      miniWindow = new BrowserWindow({
        x: miniBounds.x,
        y: miniBounds.y,
        width: miniBounds.width,
        height: miniBounds.height,
        minWidth: miniSize,
        minHeight: miniSize,
        maxWidth: miniSize,
        maxHeight: miniSize,
        title: "Ricky",
        frame: false,
        transparent: true,
        backgroundColor: "#00000000",
        resizable: false,
        maximizable: false,
        minimizable: false,
        fullscreenable: false,
        alwaysOnTop: true,
        skipTaskbar: false,
        icon: nativeImage.createEmpty(),
        webPreferences: getSecureWebPreferences(),
      });

      const devUrl = process.env.VITE_DEV_SERVER_URL;
      if (devUrl) {
        const miniDevUrl = buildMiniDevUrl(devUrl);
        miniWindow.loadURL(miniDevUrl);
      } else {
        miniWindow.loadFile(path.join(process.cwd(), "dist", "index.html"), {
          query: { window: "mini", mode: "computer" },
        });
      }

      miniWindow.on("closed", () => {
        miniWindow = null;
      });
    }
    return;
  }

  // display mode — hide the mini window and restore the main window.
  if (miniWindow && !miniWindow.isDestroyed()) {
    miniWindow.hide();
  }
  mainWindow.setMaximizable(true);

  // Prepare the target geometry while the main window is still hidden. Showing
  // first and then applying setBounds/maximize produces a visible one-frame
  // "small then normal" jump on Windows.
  if (savedWasMaximized) {
    if (savedNormalBounds) {
      mainWindow.setBounds(savedNormalBounds);
    }
  } else {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    }
    if (savedNormalBounds) {
      mainWindow.setBounds(savedNormalBounds);
    }
  }

  mainWindow.show();

  if (savedWasMaximized) {
    mainWindow.maximize();
  }
}

function getMainWindow() {
  return mainWindow;
}

module.exports = { createWindow, setWindowMode, getMainWindow };
