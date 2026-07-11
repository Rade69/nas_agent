const DEFAULT_BACKEND_URL = "http://127.0.0.1:8765";

// Security PR-1: local session token (SECURITY_HARDENING_PLAN.md section 6).
// Set once by electron/services/pythonProcess.cjs right after it generates the
// token and before it spawns the backend. Never logged, never persisted.
let localToken = null;

function setLocalToken(token) {
  localToken = token || null;
}

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
        ...(localToken ? { Authorization: `Bearer ${localToken}` } : {}),
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

// Stop button ("stop everything"): flag every in-flight tool for cancellation.
// The renderer also tears down the Realtime voice connection separately; this
// is the backend half so a running tool actually receives the cancel flag.
async function cancelAllExecutions(options = {}) {
  return await requestJson("/tools/executions/cancel-all", {
    ...options,
    method: "POST",
    body: {},
  });
}

async function createRealtimeSession(session, options = {}) {
  return await requestJson("/realtime/session", {
    ...options,
    method: "POST",
    body: { session },
  });
}

// --- FAZA 9: confirmations + plans bridge ---
// Context: agent_reports/2026-07-05_faza9-confirmations-plans.md
// These wrap the Python backend endpoints so the renderer can propose/approve
// confirmations and store/retrieve plans via IPC. The permission/risk layer that
// *issues* confirmations from tool execution is FAZA 10 — here we only expose
// storage + state machine transitions.

async function listConfirmations(options = {}) {
  return await requestJson("/confirmations", options);
}

async function listPendingConfirmations(options = {}) {
  return await requestJson("/confirmations/pending", options);
}

async function createConfirmation(payload, options = {}) {
  return await requestJson("/confirmations", {
    ...options,
    method: "POST",
    body: payload,
  });
}

async function approveConfirmation(confirmationId, options = {}) {
  return await requestJson(`/confirmations/${encodeURIComponent(confirmationId)}/approve`, {
    ...options,
    method: "POST",
    body: {},
  });
}

async function rejectConfirmation(confirmationId, options = {}) {
  return await requestJson(`/confirmations/${encodeURIComponent(confirmationId)}/reject`, {
    ...options,
    method: "POST",
    body: {},
  });
}

async function cancelConfirmation(confirmationId, options = {}) {
  return await requestJson(`/confirmations/${encodeURIComponent(confirmationId)}`, {
    ...options,
    method: "DELETE",
    body: {},
  });
}

async function listPlans(options = {}) {
  return await requestJson("/plans", options);
}

async function createPlan(payload, options = {}) {
  return await requestJson("/plans", {
    ...options,
    method: "POST",
    body: payload,
  });
}

async function getPlan(planId, options = {}) {
  return await requestJson(`/plans/${encodeURIComponent(planId)}`, options);
}

async function updatePlan(planId, payload, options = {}) {
  return await requestJson(`/plans/${encodeURIComponent(planId)}`, {
    ...options,
    method: "PATCH",
    body: payload,
  });
}

async function updatePlanStep(planId, stepId, payload, options = {}) {
  return await requestJson(
    `/plans/${encodeURIComponent(planId)}/steps/${encodeURIComponent(stepId)}`,
    {
      ...options,
      method: "PATCH",
      body: payload,
    },
  );
}

// FAZA 11: event bridge — backend -> UI events (artifact.created, tool.*,
// backend.ready, permission.confirmation_required). The UI polls /events with a
// `since` timestamp cursor to receive new events in order.
async function listEvents(since, options = {}) {
  const query = since ? `?since=${encodeURIComponent(since)}` : "";
  return await requestJson(`/events${query}`, options);
}

// Security Gate 0 (docs/SECURITY_HARDENING_PLAN.md section 18). Backend half
// of the Production Security Self-Test; electron/core/securitySelfTest.cjs
// combines this with its own Electron-side checks.
async function getSecuritySelfTest(options = {}) {
  return await requestJson("/security/self-test", options);
}

// User-facing preferences (display name in the prompt, future settings panel
// additions — see docs/RICKY_GUI_LOCALIZATION_PLAN.md STT-choice backlog note).
// Context: agent_reports/2026-07-11_settings-panel-foundation.md
async function getSettings(options = {}) {
  return await requestJson("/settings", options);
}

async function updateSettings(payload, options = {}) {
  return await requestJson("/settings", {
    ...options,
    method: "PATCH",
    body: payload,
  });
}

module.exports = {
  DEFAULT_BACKEND_URL,
  approveConfirmation,
  cancelAllExecutions,
  cancelConfirmation,
  createConfirmation,
  createPlan,
  createRealtimeSession,
  executeTool,
  getHealth,
  getPlan,
  getSecuritySelfTest,
  listConfirmations,
  listEvents,
  listPlans,
  listPendingConfirmations,
  listTools,
  normalizeBaseUrl,
  rejectConfirmation,
  requestJson,
  setLocalToken,
  getSettings,
  updatePlan,
  updatePlanStep,
  updateSettings,
};