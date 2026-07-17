// Ricky Browser Bridge — MV3 service worker (C0: pairing token support)
//
// Connects to the local Python backend via WebSocket (127.0.0.1 only).
// C0: Supports credential-based auth with per-install credentials, plus
// one-time pairing token flow. Backward compatible with legacy global secret.
//
// NEVER sends page content, executes arbitrary JS, or reads the DOM.
// Only chrome.tabs metadata and chrome.windows focus actions.

function ts() {
  return new Date().toISOString();
}

const STATE = {
  connected: false,
  ws: null,
  // Bug found 2026-07-16 (live log evidence): connect()'s original guard
  // checked `STATE.ws.readyState` synchronously, but STATE.ws is only
  // assigned inside an async getBrokerUrl().then() callback. Two
  // near-simultaneous connect() calls (observed: onStartup's own connect()
  // racing the keepalive alarm's connect(), which can fire immediately on
  // startup if chrome.alarms carried over a due firing time from before the
  // service worker restarted) both saw STATE.ws as not-yet-set and both
  // proceeded, opening two real WebSocket connections to the backend
  // (confirmed in the backend log: two [bridge:xxxxxxxx] accept() calls
  // 20ms apart). Only one completed auth; the other sat open and
  // authenticated with nobody home. `connecting` is set synchronously,
  // before anything async happens, so a second call in the same tick (or
  // before the first's broker-URL lookup resolves) is correctly blocked.
  connecting: false,
  reconnectTimer: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 6,
  reconnectBaseMs: 1000,
  // C0: per-install identity + credential
  installationId: null,
  credential: null,
  profileId: null,
  browserKind: null,
  profileLabel: null,
  // Legacy: global secret (backward compat)
  pairingSecret: null,
  // Deduplication
  processedRequestIds: new Set(),
};

// ---------------------------------------------------------------------------
// Storage helpers (C0: added installation_id, credential, profile metadata)
// ---------------------------------------------------------------------------
async function loadStoredState() {
  const stored = await chrome.storage.local.get([
    "installationId", "credential", "profileId",
    "browserKind", "profileLabel", "pairingSecret",
  ]);
  STATE.installationId = stored.installationId || null;
  STATE.credential = stored.credential || null;
  STATE.profileId = stored.profileId || null;
  STATE.browserKind = stored.browserKind || null;
  STATE.profileLabel = stored.profileLabel || null;
  STATE.pairingSecret = stored.pairingSecret || null;
}

async function ensureInstallationId() {
  if (STATE.installationId) return STATE.installationId;
  STATE.installationId = "inst_" + crypto.randomUUID().replace(/-/g, "").slice(0, 24);
  await chrome.storage.local.set({ installationId: STATE.installationId });
  return STATE.installationId;
}

async function saveCredential(data) {
  STATE.credential = data.credential;
  STATE.profileId = data.profile_id;
  STATE.browserKind = data.browser_kind;
  STATE.profileLabel = data.profile_label;
  await chrome.storage.local.set({
    credential: data.credential,
    profileId: data.profile_id,
    browserKind: data.browser_kind,
    profileLabel: data.profile_label,
  });
}

async function saveSecret(secret) {
  STATE.pairingSecret = secret;
  await chrome.storage.local.set({ pairingSecret: secret });
}

async function getBrokerUrl() {
  const stored = await chrome.storage.local.get("brokerUrl");
  return stored.brokerUrl || "ws://127.0.0.1:8765/browser-bridge";
}

// ---------------------------------------------------------------------------
// WebSocket lifecycle (C0: credential-based auth with pair flow)
// ---------------------------------------------------------------------------
function connect() {
  if (STATE.ws && (STATE.ws.readyState === WebSocket.OPEN || STATE.ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  // Synchronous guard against the race described above STATE.connecting's
  // declaration — must be set before the first `await`/`.then`, not after.
  if (STATE.connecting) {
    return;
  }
  STATE.connecting = true;

  getBrokerUrl().then((url) => {
    try {
      STATE.ws = new WebSocket(url);
    } catch (e) {
      console.error(`[ricky-bridge][${ts()}] WebSocket constructor failed:`, e);
      STATE.connecting = false;
      scheduleReconnect();
      return;
    }
    // From here on, STATE.ws.readyState (CONNECTING/OPEN) is an accurate,
    // race-free guard on its own — this flag's only job was covering the
    // async gap before STATE.ws existed.
    STATE.connecting = false;

    STATE.ws.onopen = () => {
      STATE.connected = true;
      STATE.reconnectAttempts = 0;
      STATE.processedRequestIds.clear();

      // C0: prefer credential-based auth, fall back to legacy secret
      if (STATE.credential && STATE.installationId) {
        sendMessage({
          type: "auth",
          credential: STATE.credential,
          installation_id: STATE.installationId,
        });
      } else {
        const secret = STATE.pairingSecret || "";
        sendMessage({ type: "auth", secret });
      }
    };

    STATE.ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        console.error(`[ricky-bridge][${ts()}] unparseable message:`, event.data);
        return;
      }
      handleMessage(msg);
    };

    STATE.ws.onclose = (event) => {
      STATE.connected = false;
      STATE.ws = null;
      // Bug found 2026-07-16 (live log evidence — a reconnect storm firing
      // every ~1-1.5s, matching scheduleReconnect()'s first-attempt delay
      // exactly): code 4000 means the BACKEND itself closed this connection
      // because a newer connection for the same profile already replaced
      // it (see _register_connection in browser_extension_broker.py).
      // Blindly reconnecting after that is self-defeating — this instance
      // is the one that just LOST, and reconnecting immediately just
      // re-triggers the same replace-and-close on whichever connection is
      // now current, forever. Only reconnect on close reasons that mean
      // "the connection genuinely died," not "a newer one is already here."
      if (event.code === 4000) {
        console.log(`[ricky-bridge][${ts()}] ws closed (code 4000: replaced by a newer connection) — NOT reconnecting`);
        return;
      }
      scheduleReconnect();
    };

    STATE.ws.onerror = (e) => {
      console.error(`[ricky-bridge][${ts()}] ws error`, e);
    };
  });
}

function disconnect() {
  if (STATE.reconnectTimer) {
    clearTimeout(STATE.reconnectTimer);
    STATE.reconnectTimer = null;
  }
  STATE.reconnectAttempts = STATE.maxReconnectAttempts;
  if (STATE.ws) {
    STATE.ws.onclose = null;
    STATE.ws.close();
    STATE.ws = null;
  }
  STATE.connected = false;
}

function scheduleReconnect() {
  if (STATE.reconnectAttempts >= STATE.maxReconnectAttempts) {
    return;
  }
  const delay = STATE.reconnectBaseMs * Math.pow(2, STATE.reconnectAttempts) + Math.random() * 500;
  STATE.reconnectAttempts++;
  STATE.reconnectTimer = setTimeout(() => {
    STATE.reconnectTimer = null;
    connect();
  }, delay);
}

// ---------------------------------------------------------------------------
// Pairing (C0: one-time code flow)
// ---------------------------------------------------------------------------
async function pairWithCode(code, browserKind, profileLabel) {
  await ensureInstallationId();

  return new Promise((resolve) => {
    getBrokerUrl().then((url) => {
      let ws;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        console.error("[ricky-bridge][pair] WebSocket constructor threw:", e);
        resolve({ ok: false, error: "Invalid broker URL: " + e.message });
        return;
      }
      const timeout = setTimeout(() => {
        console.error("[ricky-bridge][pair] timed out after 15s, readyState =", ws.readyState);
        ws.close();
        resolve({ ok: false, error: "Pairing timed out." });
      }, 15000);

      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: "pair",
          code: code.toUpperCase(),
          browser_kind: browserKind,
          installation_id: STATE.installationId,
          profile_label: profileLabel || "Default",
          extension_version: "1.0.0",
        }));
      };

      ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);
        clearTimeout(timeout);

        if (msg.type === "paired") {
          await saveCredential(msg);
          ws.close();
          // Reconnect with the new credential
          STATE.reconnectAttempts = 0;
          connect();
          resolve({
            ok: true,
            profile_id: msg.profile_id,
            browser_kind: msg.browser_kind,
            profile_label: msg.profile_label,
          });
        } else if (msg.type === "pair_failed") {
          console.error("[ricky-bridge][pair] pair_failed:", msg.reason);
          ws.close();
          resolve({ ok: false, error: msg.reason || "Pairing failed." });
        } else {
          console.error("[ricky-bridge][pair] unexpected message type:", msg.type);
          ws.close();
          resolve({ ok: false, error: "Unexpected response." });
        }
      };

      ws.onclose = (event) => {
        // The most diagnostic field: a WS close BEFORE onopen fired with
        // code 1006 means the browser could not even complete the TCP/HTTP
        // handshake (wrong port, nothing listening, blocked). A close AFTER
        // onopen with an app-level code (4001/4002/1008) means the backend
        // accepted the connection but rejected it at the protocol level.
      };

      ws.onerror = (e) => {
        console.error("[ricky-bridge][pair] ws error event:", e, "readyState was:", ws.readyState);
        clearTimeout(timeout);
        resolve({ ok: false, error: "Could not connect to Ricky backend." });
      };
    });
  });
}

// ---------------------------------------------------------------------------
// Message handling
// ---------------------------------------------------------------------------
function sendMessage(msg) {
  if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
  STATE.ws.send(JSON.stringify(msg));
}

async function handleMessage(msg) {
  const { type, request_id, ...payload } = msg;

  switch (type) {
    case "auth_ok": {
      if (payload.profile_id) {
        STATE.profileId = payload.profile_id;
        STATE.browserKind = payload.browser_kind;
        STATE.profileLabel = payload.profile_label;
      }
      chrome.action.setBadgeText({ text: "ON" });
      chrome.action.setBadgeBackgroundColor({ color: "#4CAF50" });
      break;
    }

    case "auth_failed": {
      console.error("[ricky-bridge] auth failed:", payload.reason);
      STATE.connected = false;
      chrome.action.setBadgeText({ text: "!" });
      chrome.action.setBadgeBackgroundColor({ color: "#F44336" });
      break;
    }

    case "paired": {
      // Handled in pairWithCode — here as fallback if received after reconnect
      await saveCredential(payload);
      break;
    }

    case "list_tabs": {
      await handleListTabs(request_id, payload);
      break;
    }

    case "activate_tab": {
      await handleActivateTab(request_id, payload);
      break;
    }

    case "close_tab": {
      await handleCloseTab(request_id, payload);
      break;
    }

    case "open_tab": {
      await handleOpenTab(request_id, payload);
      break;
    }

    case "ping": {
      sendMessage({ type: "pong", request_id });
      break;
    }

    default:
      console.warn("[ricky-bridge] unknown message type:", type);
  }
}

// ---------------------------------------------------------------------------
// Command handlers (unchanged from PR 1-3)
// ---------------------------------------------------------------------------

async function handleListTabs(requestId, { scope }) {
  if (requestId && STATE.processedRequestIds.has(requestId)) return;
  if (requestId) STATE.processedRequestIds.add(requestId);

  try {
    const queryInfo = scope === "all_windows" ? {} : { currentWindow: true };
    const tabs = await chrome.tabs.query(queryInfo);

    const listed = tabs.map((tab, index) => ({
      position: index + 1,
      tab_id: String(tab.id),
      title: tab.title || "",
      url: tab.url || "",
      active: !!tab.active,
      pinned: !!tab.pinned,
      audible: !!tab.audible,
      incognito: !!tab.incognito,
      window_id: String(tab.windowId),
    }));

    sendMessage({
      type: "tab_list",
      request_id: requestId,
      scope: scope || "current_window",
      count: listed.length,
      tabs: listed,
    });
  } catch (err) {
    sendMessage({
      type: "error",
      request_id: requestId,
      code: "TAB_LIST_FAILED",
      message: `Failed to list tabs: ${err.message}`,
    });
  }
}

async function handleActivateTab(requestId, { tab_id, window_id }) {
  if (requestId && STATE.processedRequestIds.has(requestId)) return;
  if (requestId) STATE.processedRequestIds.add(requestId);

  try {
    await chrome.windows.update(Number(window_id), { focused: true });
    await chrome.tabs.update(Number(tab_id), { active: true });

    sendMessage({
      type: "tab_activated",
      request_id: requestId,
      tab_id,
      window_id,
    });
  } catch (err) {
    sendMessage({
      type: "error",
      request_id: requestId,
      code: "TAB_ACTIVATE_FAILED",
      message: `Failed to activate tab: ${err.message}`,
    });
  }
}

async function handleCloseTab(requestId, { tab_id }) {
  if (requestId && STATE.processedRequestIds.has(requestId)) return;
  if (requestId) STATE.processedRequestIds.add(requestId);

  try {
    await chrome.tabs.remove(Number(tab_id));
    sendMessage({
      type: "tab_closed",
      request_id: requestId,
      tab_id,
    });
  } catch (err) {
    sendMessage({
      type: "error",
      request_id: requestId,
      code: "TAB_CLOSE_FAILED",
      message: `Failed to close tab: ${err.message}`,
    });
  }
}

async function handleOpenTab(requestId, { url, activate }) {
  if (requestId && STATE.processedRequestIds.has(requestId)) return;
  if (requestId) STATE.processedRequestIds.add(requestId);

  try {
    const tab = await chrome.tabs.create({
      url: url || "about:blank",
      active: activate !== false,
    });
    sendMessage({
      type: "tab_opened",
      request_id: requestId,
      tab_id: String(tab.id),
      title: tab.title || "",
      url: tab.url || url,
    });
  } catch (err) {
    sendMessage({
      type: "error",
      request_id: requestId,
      code: "TAB_OPEN_FAILED",
      message: `Failed to open tab: ${err.message}`,
    });
  }
}

// ---------------------------------------------------------------------------
// Keep-alive (found 2026-07-16: connection was dropping mid-session during
// normal pauses — voice round-trips, waiting for user confirmation, deciding
// which tab to close). Root cause: MV3 service workers are suspended by the
// browser after ~30s of no activity, which silently kills any open
// WebSocket and — critically — wipes the whole JS context (STATE, pending
// reconnect timers, everything), so the existing ws.onclose/scheduleReconnect
// logic never even gets a chance to run. Only chrome.alarms is guaranteed to
// wake a fully-suspended service worker back up (setInterval/setTimeout do
// not survive suspension). ALARM_PERIOD_MINUTES is the Chrome-enforced floor
// for repeating alarms — this can't be tightened further; the fix is
// "self-heals within ~1 minute", not "never drops".
// ---------------------------------------------------------------------------
const KEEPALIVE_ALARM_NAME = "ricky-bridge-keepalive";
const ALARM_PERIOD_MINUTES = 1;

function ensureKeepAliveAlarm() {
  chrome.alarms.create(KEEPALIVE_ALARM_NAME, { periodInMinutes: ALARM_PERIOD_MINUTES });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== KEEPALIVE_ALARM_NAME) return;
  if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) {
    connect();
    return;
  }
  // WS is open — send a ping. This both confirms the connection is genuinely
  // alive (not a stale readyState) and generates traffic that helps keep the
  // service worker from being judged idle before the next alarm.
  sendMessage({ type: "ping", request_id: `keepalive_${Date.now()}` });
});

// ---------------------------------------------------------------------------
// Extension lifecycle (C0: ensure installation_id on first load)
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  ensureKeepAliveAlarm();
  ensureInstallationId().then(() => loadStoredState()).then(() => connect());
});

chrome.runtime.onStartup.addListener(() => {
  ensureKeepAliveAlarm();
  loadStoredState().then(() => connect());
});

// The service worker can be woken by the alarm alone (browser restart
// without onInstalled/onStartup firing again in some cases) — re-arm
// defensively on every fresh script evaluation, not just install/startup.
ensureKeepAliveAlarm();

// Listen for messages from the options page
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  // C0: pair with one-time code
  if (msg.type === "pair") {
    pairWithCode(msg.code, msg.browserKind, msg.profileLabel).then((result) => {
      sendResponse(result);
    });
    return true; // async
  }
  // C0: get full status including pairing info
  if (msg.type === "get_status") {
    sendResponse({
      connected: STATE.connected,
      installationId: STATE.installationId,
      credential: STATE.credential ? "set" : "not set",
      profileId: STATE.profileId,
      browserKind: STATE.browserKind,
      profileLabel: STATE.profileLabel,
      pairingSecret: STATE.pairingSecret ? "set" : "not set",
      reconnectAttempts: STATE.reconnectAttempts,
      maxReconnectAttempts: STATE.maxReconnectAttempts,
    });
    return false;
  }
  // Legacy: update global secret
  if (msg.type === "update_secret") {
    saveSecret(msg.secret).then(() => {
      disconnect();
      connect();
      sendResponse({ ok: true });
    });
    return true;
  }
  if (msg.type === "update_broker_url") {
    chrome.storage.local.set({ brokerUrl: msg.url }).then(() => {
      disconnect();
      connect();
      sendResponse({ ok: true });
    });
    return true;
  }
  if (msg.type === "reconnect") {
    disconnect();
    STATE.reconnectAttempts = 0;
    connect();
    sendResponse({ ok: true });
    return false;
  }
  // C0: reset pairing (clear stored credential)
  if (msg.type === "reset_pairing") {
    STATE.credential = null;
    STATE.profileId = null;
    STATE.browserKind = null;
    STATE.profileLabel = null;
    chrome.storage.local.remove(["credential", "profileId", "browserKind", "profileLabel"]).then(() => {
      disconnect();
      sendResponse({ ok: true });
    });
    return true;
  }
  return false;
});

// Start on load
loadStoredState().then(() => connect());
