/** Python backend process manager (FAZA 5 + 19 packaging).
 *  Spawns the Python backend as a child process (uvicorn in dev,
 *  PyInstaller-frozen executable in packaged builds), generates and
 *  injects RICKY_LOCAL_TOKEN, waits for /health before resolving,
 *  and forwards stdout/stderr to the Electron console.
 *  Context: agent_reports/2026-07-05_faza5-electron-starts-python-backend.md */

const { randomBytes } = require("node:crypto");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const { DEFAULT_BACKEND_URL, getHealth, normalizeBaseUrl, setLocalToken } = require("./pythonClient.cjs");

const DEFAULT_PORT = 8765;

const backendState = {
  process: null,
  status: "stopped",
  url: DEFAULT_BACKEND_URL,
  error: null,
  external: false,
};

// Security PR-1: one short-lived local session token per Electron app session
// (SECURITY_HARDENING_PLAN.md section 6). Generated once, never logged, never
// persisted to disk — lives only in process memory for as long as Electron runs.
let localSessionToken = null;

function getOrCreateLocalToken() {
  if (!localSessionToken) {
    localSessionToken = randomBytes(32).toString("hex");
    setLocalToken(localSessionToken);
  }
  return localSessionToken;
}

function getBackendStatus() {
  return {
    status: backendState.status,
    url: backendState.url,
    error: backendState.error,
    pid: backendState.process?.pid || null,
    external: backendState.external,
  };
}

function resolveBackendPaths(options = {}) {
  const repoRoot = options.repoRoot || process.cwd();
  const backendDir = options.backendDir || path.join(repoRoot, "python_backend");
  const venvPython = path.join(backendDir, ".venv", "Scripts", "python.exe");
  const pythonCommand = process.env.RICKY_PYTHON_PATH || (fs.existsSync(venvPython) ? venvPython : "python");
  return { repoRoot, backendDir, pythonCommand };
}

async function startPythonBackend(options = {}) {
  const enabled = options.enabled ?? true;
  const port = Number(options.port || process.env.RICKY_BACKEND_PORT || DEFAULT_PORT);
  const host = "127.0.0.1";
  const baseUrl = normalizeBaseUrl(options.baseUrl || `http://${host}:${port}`);
  backendState.url = baseUrl;
  const localToken = getOrCreateLocalToken();

  if (backendState.status === "running" || backendState.status === "starting") {
    return getBackendStatus();
  }

  const existingHealth = await getHealth({ baseUrl, timeoutMs: 500 });
  if (existingHealth.ok) {
    backendState.status = "running";
    backendState.error = null;
    backendState.external = true;
    console.log(`[python-backend] Reusing existing backend at ${baseUrl}`);
    return getBackendStatus();
  }

  if (!enabled) {
    backendState.status = "skipped";
    backendState.error = "Python backend auto-start is disabled.";
    console.log(`[python-backend] ${backendState.error}`);
    return getBackendStatus();
  }

  const { repoRoot, backendDir, pythonCommand } = resolveBackendPaths(options);

  // FAZA 19: u packaged (production) build-u pokreni bundlovani PyInstaller
  // sidecar (.exe) umjesto python -m uvicorn. Dev ostaje na postojećem toku.
  // Context: agent_reports/2026-07-06_faza19-packaging-plan.md
  if (options.isPackaged) {
    return await startPackagedBackend({ host, port, baseUrl, localToken, options });
  }

  if (!fs.existsSync(backendDir)) {
    backendState.status = "error";
    backendState.error = `Python backend directory not found: ${backendDir}`;
    throw new Error(backendState.error);
  }

  backendState.status = "starting";
  backendState.error = null;
  backendState.external = false;

  const args = ["-m", "uvicorn", "app.main:app", "--host", host, "--port", String(port)];
  console.log(`[python-backend] Starting: ${pythonCommand} ${args.join(" ")}`);

  const child = spawn(pythonCommand, args, {
    cwd: backendDir,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      // Share one data directory with the Electron-side legacy JSON db
      // (electron/main.cjs `dataDir`) instead of Python defaulting to its own
      // python_backend/data/ — otherwise screenshots/SQLite land in a folder
      // the rest of the app never looks in. See app/core/config.py RICKY_DATA_DIR.
      RICKY_DATA_DIR: path.join(repoRoot, "data"),
      // Security PR-1: local session token, see app/core/auth.py.
      RICKY_LOCAL_TOKEN: localToken,
    },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendState.process = child;

  child.stdout.on("data", (chunk) => {
    process.stdout.write(`[python-backend] ${chunk}`);
  });

  child.stderr.on("data", (chunk) => {
    process.stderr.write(`[python-backend] ${chunk}`);
  });

  child.on("exit", (code, signal) => {
    if (backendState.process === child) {
      backendState.process = null;
      if (backendState.status !== "stopping") {
        backendState.status = code === 0 ? "stopped" : "error";
        backendState.error = code === 0 ? null : `Python backend exited with code ${code ?? "null"} signal ${signal ?? "null"}`;
      }
    }
  });

  child.on("error", (error) => {
    backendState.status = "error";
    backendState.error = error.message;
  });

  try {
    await waitForBackendHealth({ baseUrl, timeoutMs: options.timeoutMs || 30000 });
    backendState.status = "running";
    backendState.error = null;
    console.log(`[python-backend] Ready at ${baseUrl}`);
    return getBackendStatus();
  } catch (error) {
    backendState.status = "error";
    backendState.error = error instanceof Error ? error.message : String(error);
    stopPythonBackend();
    throw error;
  }
}

async function waitForBackendHealth({ baseUrl, timeoutMs }) {
  const startedAt = Date.now();
  let lastError = "Backend did not respond.";

  while (Date.now() - startedAt < timeoutMs) {
    const health = await getHealth({ baseUrl, timeoutMs: 1000 });
    if (health.ok) return health;
    if (health.error) lastError = health.error;
    await delay(300);
  }

  throw new Error(`Python backend health check timed out: ${lastError}`);
}

// FAZA 19: pokreni PyInstaller-bundlovani ricky_backend.exe sidecar.
// Sidecar se nalazi u process.resourcesPath/ricky_backend/ (electron-builder
// extraFiles ga kopira tamo iz python_backend/dist/ricky_backend/).
// Context: agent_reports/2026-07-06_faza19-packaging-plan.md
async function startPackagedBackend({ host, port, baseUrl, localToken, options }) {
  const resourcesPath = process.resourcesPath || path.join(__dirname, "..", "..");
  const sidecarDir = path.join(resourcesPath, "ricky_backend");
  const sidecarExe = path.join(sidecarDir, "ricky_backend.exe");

  if (!fs.existsSync(sidecarExe)) {
    backendState.status = "error";
    backendState.error = `Packaged backend executable not found: ${sidecarExe}. Ensure the sidecar was built (pyinstaller ricky_backend.spec) and included in the electron-builder package.`;
    throw new Error(backendState.error);
  }

  backendState.status = "starting";
  backendState.error = null;
  backendState.external = false;

  // Sidecar prima iste env varijable kao dev backend:
  // - RICKY_DATA_DIR → data/ folder unutar sidecar direktorija (čitanje/pisanje)
  // - RICKY_LOCAL_TOKEN → Security PR-1 lokalni auth token
  // - OPENAI_API_KEY, EXA_API_KEY → proslijeđeni iz roditeljskog procesa preko ...process.env
  //
  // .env.local NIJE u paketu (electron-builder extraFiles filter + .gitignore)
  // tako da API ključevi dolaze SAMO iz env varijabli roditeljskog procesa.
  // Ako korisnik nije postavio ključeve, backend će se pokrenuti ali realtime
  // i web_search/image_generate će vratiti MISSING_API_KEY (fail closed).
  const dataDir = path.join(sidecarDir, "data");
  fs.mkdirSync(dataDir, { recursive: true });

  console.log(`[python-backend] Starting packaged: ${sidecarExe}`);
  const child = spawn(sidecarExe, [], {
    cwd: sidecarDir,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      RICKY_DATA_DIR: dataDir,
      RICKY_LOCAL_TOKEN: localToken,
      // Uvicorn sluša na zadatom host:port — sidecar .exe je entry point
      // isti kao "python -m uvicorn app.main:app --host ... --port ..."
      // pa env varijable kontrolišu host/port.
      RICKY_HOST: host,
      RICKY_PORT: String(port),
    },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendState.process = child;

  child.stdout.on("data", (chunk) => {
    process.stdout.write(`[python-backend] ${chunk}`);
  });

  child.stderr.on("data", (chunk) => {
    process.stderr.write(`[python-backend] ${chunk}`);
  });

  child.on("exit", (code, signal) => {
    if (backendState.process === child) {
      backendState.process = null;
      if (backendState.status !== "stopping") {
        backendState.status = code === 0 ? "stopped" : "error";
        backendState.error =
          code === 0 ? null : `Python backend exited with code ${code ?? "null"} signal ${signal ?? "null"}`;
      }
    }
  });

  child.on("error", (error) => {
    backendState.status = "error";
    backendState.error = error.message;
  });

  try {
    await waitForBackendHealth({ baseUrl, timeoutMs: options.timeoutMs || 30000 });
    backendState.status = "running";
    backendState.error = null;
    console.log(`[python-backend] Ready at ${baseUrl}`);
    return getBackendStatus();
  } catch (error) {
    backendState.status = "error";
    backendState.error = error instanceof Error ? error.message : String(error);
    stopPythonBackend();
    throw error;
  }
}

function stopPythonBackend() {
  const child = backendState.process;
  if (!child) {
    if (backendState.status !== "running" || !backendState.external) {
      backendState.status = "stopped";
    }
    return;
  }

  backendState.status = "stopping";
  backendState.process = null;
  child.kill();
  backendState.status = "stopped";
  backendState.error = null;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = {
  getBackendStatus,
  startPythonBackend,
  stopPythonBackend,
};