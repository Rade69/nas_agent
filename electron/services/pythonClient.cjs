const DEFAULT_BACKEND_URL = "http://127.0.0.1:8765";

function normalizeBaseUrl(baseUrl = process.env.RICKY_BACKEND_URL || DEFAULT_BACKEND_URL) {
  return String(baseUrl).replace(/\/+$/, "");
}

async function requestJson(path, options = {}) {
  const baseUrl = normalizeBaseUrl(options.baseUrl);
  const timeoutMs = Number(options.timeoutMs || 5000);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: options.method || "GET",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });

    const text = await response.text();
    const body = text ? JSON.parse(text) : null;

    if (!response.ok) {
      const message = body?.error?.message || body?.detail || text || `HTTP ${response.status}`;
      throw new Error(`Python backend request failed: ${response.status} ${message}`);
    }

    return body;
  } finally {
    clearTimeout(timeout);
  }
}

async function getHealth(options = {}) {
  try {
    const body = await requestJson("/health", { ...options, timeoutMs: options.timeoutMs || 1000 });
    return { ok: body?.ok === true, body };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function listTools(options = {}) {
  return await requestJson("/tools", options);
}

async function executeTool(payload, options = {}) {
  return await requestJson("/tools/execute", {
    ...options,
    method: "POST",
    body: payload,
  });
}

async function createRealtimeSession(session, options = {}) {
  return await requestJson("/realtime/session", {
    ...options,
    method: "POST",
    body: { session },
  });
}

module.exports = {
  DEFAULT_BACKEND_URL,
  createRealtimeSession,
  executeTool,
  getHealth,
  listTools,
  normalizeBaseUrl,
};