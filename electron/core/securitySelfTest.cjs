/** Electron-side Production Security Self-Test (Security Gate 0).
 *  Checks webPreferences (sandbox, webSecurity, devTools), preload path,
 *  and backend auth token presence. Combines with the backend-side
 *  self-test (GET /security/self-test) for the full Gate 0 check.
 *  Context: agent_reports/2026-07-06_gate0-selftest-pathsandbox.md */

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

// FAZA S-3: the packaged renderer loads via file:// (window.cjs loadFile), where
// a response-header CSP cannot apply — the CSP lives as a <meta> tag injected
// into dist/index.html at build time (vite.config.ts cspMetaPlugin). This check
// confirms that meta tag actually shipped, with the directives that matter most
// (locked script-src, no plugins, tight egress). Dev is exempt: the CSP is
// build-only and the dev server intentionally has none.
function checkContentSecurityPolicy(isPackaged) {
  if (!isPackaged) {
    return { name: "content_security_policy", passed: true, detail: "dev build — CSP is injected at build time only" };
  }
  const indexPath = path.join(process.cwd(), "dist", "index.html");
  if (!fs.existsSync(indexPath)) {
    return { name: "content_security_policy", passed: false, detail: `built index.html not found at ${indexPath}` };
  }
  const html = fs.readFileSync(indexPath, "utf8");
  const cspMatch = html.match(/http-equiv=["']Content-Security-Policy["'][^>]*content=["']([^"']+)["']/i);
  if (!cspMatch) {
    return { name: "content_security_policy", passed: false, detail: "no Content-Security-Policy meta tag in dist/index.html" };
  }
  // Vite serializes the attribute with HTML-encoded quotes (&#39;); the browser
  // decodes these before reading the CSP, so decode them here too before
  // matching directive strings that contain single quotes.
  const csp = cspMatch[1]
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&");
  const required = ["default-src 'self'", "script-src 'self'", "object-src 'none'", "connect-src"];
  const missing = required.filter((directive) => !csp.includes(directive));
  if (missing.length > 0) {
    return { name: "content_security_policy", passed: false, detail: `CSP missing directives: ${missing.join(", ")}` };
  }
  // script-src must not weaken back to inline/eval (style-src 'unsafe-inline'
  // is fine and expected, so we inspect only the script-src directive).
  const scriptSrc = (csp.split(";").find((d) => d.trim().startsWith("script-src")) || "").trim();
  if (scriptSrc.includes("'unsafe-eval'") || scriptSrc.includes("'unsafe-inline'")) {
    return { name: "content_security_policy", passed: false, detail: `script-src allows unsafe code: ${scriptSrc}` };
  }
  return { name: "content_security_policy", passed: true, detail: "ok" };
}

function runElectronSelfTestChecks(isPackaged) {
  return [
    checkSecureWebPreferences(),
    checkPreloadSurface(),
    checkNoDevtoolsInProduction(isPackaged),
    checkContentSecurityPolicy(isPackaged),
  ];
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
