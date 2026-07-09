const path = require("node:path");
const { BrowserWindow, nativeImage, screen } = require("electron");
const { getSecureWebPreferences } = require("./secureWebPreferences.cjs");

let mainWindow = null;
// Separate mini window for Computer Mode. We do NOT resize the main window
// down to 190x190 because a frameless + transparent Electron window on
// Windows gets spontaneously re-maximized by DWM ~2s after setBounds(), no
// matter what combination of setMaximizable(false) / setAlwaysOnTop / opacity
// is applied (confirmed across 4 iterations via [window-debug] logs). A
// dedicated mini BrowserWindow never enters the maximized state, so DWM has
// nothing to "restore" — the spontaneous maximize cannot happen.
let miniWindow = null;
let savedNormalBounds = null;
let savedWasMaximized = false;
let activeModeTraceId = null;

function windowSnapshot(win) {
  if (!win || win.isDestroyed()) return null;
  return {
    bounds: win.getBounds(),
    normalBounds: win.getNormalBounds(),
    visible: win.isVisible(),
    minimized: win.isMinimized(),
    maximized: win.isMaximized(),
    focused: win.isFocused(),
    resizable: win.isResizable(),
    maximizable: win.isMaximizable(),
    alwaysOnTop: win.isAlwaysOnTop(),
  };
}

function logModeTrace(traceId, step, extra = {}) {
  const id = traceId || activeModeTraceId || "no-trace";
  console.log(`[mode-trace:${id}] window:${step}`, {
    main: windowSnapshot(mainWindow),
    mini: windowSnapshot(miniWindow),
    savedNormalBounds,
    savedWasMaximized,
    ...extra,
  });
}

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
function setWindowMode(mode, traceId = `mode-window-${Date.now()}`) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  activeModeTraceId = traceId;
  logModeTrace(traceId, "setWindowMode:start", { mode });

  if (mode === "computer") {
    savedNormalBounds = mainWindow.getNormalBounds();
    savedWasMaximized = mainWindow.isMaximized();
    logModeTrace(traceId, "computer:saved-main-state", { mode });
    // Block DWM from spontaneously re-maximizing the hidden main window.
    // Logs show Windows does this ~2s after hide() on frameless transparent
    // windows, even while visible:false. setMaximizable(false) on the hidden
    // window prevents it (different from the resize approach where it failed).
    logModeTrace(traceId, "computer:before-main-setMaximizable-false", { mode });
    mainWindow.setMaximizable(false);
    logModeTrace(traceId, "computer:after-main-setMaximizable-false", { mode });
    logModeTrace(traceId, "computer:before-main-hide", { mode });
    mainWindow.hide();
    logModeTrace(traceId, "computer:after-main-hide", { mode });

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
    logModeTrace(traceId, "computer:computed-mini-bounds", {
      mode,
      cursorPoint,
      workArea,
      miniBounds,
    });

    if (miniWindow && !miniWindow.isDestroyed()) {
      logModeTrace(traceId, "computer:before-mini-show-existing", { mode });
      miniWindow.show();
      logModeTrace(traceId, "computer:after-mini-show-existing", { mode });
    } else {
      logModeTrace(traceId, "computer:before-mini-create", { mode, miniBounds });
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
      logModeTrace(traceId, "computer:after-mini-create", { mode });

      const devUrl = process.env.VITE_DEV_SERVER_URL;
      if (devUrl) {
        const miniDevUrl = buildMiniDevUrl(devUrl);
        logModeTrace(traceId, "computer:before-mini-loadURL", { mode, devUrl: miniDevUrl });
        miniWindow.loadURL(miniDevUrl);
        logModeTrace(traceId, "computer:after-mini-loadURL", { mode, devUrl: miniDevUrl });
      } else {
        logModeTrace(traceId, "computer:before-mini-loadFile", { mode });
        miniWindow.loadFile(path.join(process.cwd(), "dist", "index.html"), {
          query: { window: "mini", mode: "computer" },
        });
        logModeTrace(traceId, "computer:after-mini-loadFile", { mode });
      }

      miniWindow.on("closed", () => {
        logModeTrace(activeModeTraceId, "mini:closed-event");
        miniWindow = null;
      });
    }
    logModeTrace(traceId, "setWindowMode:end", { mode });
    return;
  }

  // display mode — hide the mini window and restore the main window.
  if (miniWindow && !miniWindow.isDestroyed()) {
    logModeTrace(traceId, "display:before-mini-hide", { mode });
    miniWindow.hide();
    logModeTrace(traceId, "display:after-mini-hide", { mode });
  }
  logModeTrace(traceId, "display:before-main-setMaximizable-true", { mode });
  mainWindow.setMaximizable(true);
  logModeTrace(traceId, "display:after-main-setMaximizable-true", { mode });

  // Prepare the target geometry while the main window is still hidden. Showing
  // first and then applying setBounds/maximize produces a visible one-frame
  // "small then normal" jump on Windows.
  if (savedWasMaximized) {
    if (savedNormalBounds) {
      logModeTrace(traceId, "display:before-hidden-main-setBounds-before-maximize", { mode, savedNormalBounds });
      mainWindow.setBounds(savedNormalBounds);
      logModeTrace(traceId, "display:after-hidden-main-setBounds-before-maximize", { mode, savedNormalBounds });
    }
  } else {
    if (mainWindow.isMaximized()) {
      logModeTrace(traceId, "display:before-hidden-main-unmaximize", { mode });
      mainWindow.unmaximize();
      logModeTrace(traceId, "display:after-hidden-main-unmaximize", { mode });
    }
    if (savedNormalBounds) {
      logModeTrace(traceId, "display:before-hidden-main-setBounds", { mode, savedNormalBounds });
      mainWindow.setBounds(savedNormalBounds);
      logModeTrace(traceId, "display:after-hidden-main-setBounds", { mode, savedNormalBounds });
    }
  }

  logModeTrace(traceId, "display:before-main-show", { mode });
  mainWindow.show();
  logModeTrace(traceId, "display:after-main-show", { mode });

  if (savedWasMaximized) {
    logModeTrace(traceId, "display:before-main-maximize", { mode });
    mainWindow.maximize();
    logModeTrace(traceId, "display:after-main-maximize", { mode });
  }
  logModeTrace(traceId, "setWindowMode:end", { mode });
}

function getMainWindow() {
  return mainWindow;
}

module.exports = { createWindow, setWindowMode, getMainWindow };
