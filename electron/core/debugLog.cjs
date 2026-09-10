/** Debug log — piše timestampovane događaje u data/debug.log (gitignored).
 *  Prati IPC pozive (korisničke klikove) i backend requestove radi dijagnoze.
 *  Nikad ne loguje API ključeve, tokene ni SDP blobove — samo kanale/path-ove. */
const fs = require("node:fs");
const path = require("node:path");

let logPath = null;

function initDebugLog(repoRoot) {
  logPath = path.join(repoRoot, "data", "debug.log");
}

function debugLog(...parts) {
  if (!logPath) return;
  try {
    const line = `${new Date().toISOString()} ${parts.join(" ")}\n`;
    fs.appendFileSync(logPath, line);
  } catch {
    /* best-effort, nikad ne ruši app */
  }
}

function summarize(value) {
  try {
    const s = JSON.stringify(value);
    return s.length > 300 ? s.slice(0, 300) + "…" : s;
  } catch {
    return String(value);
  }
}

module.exports = { initDebugLog, debugLog, summarize };
