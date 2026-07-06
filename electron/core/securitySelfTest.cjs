const fs = require("node:fs");
const path = require("node:path");
const { getSecureWebPreferences } = require("./secureWebPreferences.cjs");
const { getSecuritySelfTest } = require("../services/pythonClient.cjs");

// Security Gate 0 (docs/SECURITY_HARDENING_PLAN.md section 18, "Production
// Security Self-Test"). This module covers the checks knowable only from the
// Electron main process (webPreferences, preload surface, devtools); it calls
// GET /security/self-test for the Python-side half (host binding, auth token,
// CORS, critical-tool confirmation gating, log redaction) and combines both.
//
// In a packaged (production) build, any failed check means
// runSecuritySelfTest() reports ok: false — main.cjs is responsible for
// failing closed (block window creation, show an error, quit) in that case.
// In a dev build, main.cjs only logs the failures so iteration isn't blocked.

const EXPECTED_WEB_PREFERENCES = {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
};

function checkSecureWebPreferences() {
  const prefs = getSecureWebPreferences();
  const mismatches = Object.entries(EXPECTED_WEB_PREFERENCES)
    .filter(([key, expected]) => prefs[key] !== expected)
    .map(([key]) => key);
  return {
    name: "electron_web_preferences",
    passed: mismatches.length === 0,
    detail: mismatches.length === 0 ? "ok" : `mismatch: ${mismatches.join(", ")}`,
  };
}

function checkPreloadSurface() {
  const preloadPath = path.join(__dirname, "..", "preload.cjs");
  if (!fs.existsSync(preloadPath)) {
    return { name: "preload_surface", passed: false, detail: `preload.cjs not found at ${preloadPath}` };
  }
  const source = fs.readFileSync(preloadPath, "utf8");
  const problems = [];
  if (/OPENAI/i.test(source)) {
    problems.push("preload.cjs references OPENAI — API keys must never reach the renderer");
  }
  if (/ipcRenderer\.invoke\(\s*channel\b/.test(source)) {
    problems.push("preload.cjs looks like it forwards an arbitrary channel name (generic invoke passthrough)");
  }
  return {
    name: "preload_surface",
    passed: problems.length === 0,
    detail: problems.length === 0 ? "ok" : problems.join("; "),
  };
}

function checkNoDevtoolsInProduction(isPackaged) {
  if (!isPackaged) {
    return { name: "no_devtools_in_production", passed: true, detail: "dev build — this check only gates production" };
  }
  const filesToScan = ["window.cjs", "companionWindow.cjs"].map((name) => path.join(__dirname, name));
  const problems = [];
  for (const file of filesToScan) {
    if (!fs.existsSync(file)) continue;
    const source = fs.readFileSync(file, "utf8");
    if (/openDevTools\s*\(/.test(source)) {
      problems.push(`${path.basename(file)} calls openDevTools()`);
    }
  }
  return {
    name: "no_devtools_in_production",
    passed: problems.length === 0,
    detail: problems.length === 0 ? "ok" : problems.join("; "),
  };
}

function runElectronSelfTestChecks(isPackaged) {
  return [checkSecureWebPreferences(), checkPreloadSurface(), checkNoDevtoolsInProduction(isPackaged)];
}

async function runSecuritySelfTest({ isPackaged = false } = {}) {
  const electronChecks = runElectronSelfTestChecks(isPackaged);

  let backendChecks;
  try {
    const backendResult = await getSecuritySelfTest({ timeoutMs: 5000 });
    backendChecks = (backendResult.checks || []).map((check) => ({
      name: `backend_${check.name}`,
      passed: check.passed,
      detail: check.detail,
    }));
  } catch (error) {
    backendChecks = [
      {
        name: "backend_self_test_reachable",
        passed: false,
        detail: error instanceof Error ? error.message : String(error),
      },
    ];
  }

  const checks = [...electronChecks, ...backendChecks];
  return { ok: checks.every((check) => check.passed), checks };
}

module.exports = { runSecuritySelfTest };
