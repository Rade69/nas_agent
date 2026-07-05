const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const { DEFAULT_BACKEND_URL, getHealth, normalizeBaseUrl } = require("./pythonClient.cjs");

const DEFAULT_PORT = 8765;

const backendState = {
  process: null,
  status: "stopped",
  url: DEFAULT_BACKEND_URL,
  error: null,
  external: false,
};

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
  return { backendDir, pythonCommand };
}

async function startPythonBackend(options = {}) {
  const enabled = options.enabled ?? !options.isPackaged;
  const port = Number(options.port || process.env.RICKY_BACKEND_PORT || DEFAULT_PORT);
  const host = "127.0.0.1";
  const baseUrl = normalizeBaseUrl(options.baseUrl || `http://${host}:${port}`);
  backendState.url = baseUrl;

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
    backendState.error = "Python backend auto-start is enabled only in dev mode for FAZA 5.";
    console.log(`[python-backend] ${backendState.error}`);
    return getBackendStatus();
  }

  const { backendDir, pythonCommand } = resolveBackendPaths(options);
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