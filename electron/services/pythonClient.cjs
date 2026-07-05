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

module.exports = {
  DEFAULT_BACKEND_URL,
  approveConfirmation,
  cancelConfirmation,
  createConfirmation,
  createPlan,
  createRealtimeSession,
  executeTool,
  getHealth,
  getPlan,
  listConfirmations,
  listEvents,
  listPlans,
  listPendingConfirmations,
  listTools,
  normalizeBaseUrl,
  rejectConfirmation,
  requestJson,
  setLocalToken,
  updatePlan,
  updatePlanStep,
};