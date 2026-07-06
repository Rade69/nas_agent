// Security Gate 0 (docs/SECURITY_HARDENING_PLAN.md section 18, "Production
// Security Self-Test"). Single source of truth for the webPreferences every
// BrowserWindow in this app must use, so window.cjs, companionWindow.cjs, and
// securitySelfTest.cjs all read the same object instead of three copies that
// could silently drift out of sync.
const path = require("node:path");

function getSecureWebPreferences() {
  return {
    preload: path.join(__dirname, "..", "preload.cjs"),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
    webSecurity: true,
    allowRunningInsecureContent: false,
  };
}

module.exports = { getSecureWebPreferences };
