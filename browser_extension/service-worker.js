// Ricky Browser Bridge — MV3 service worker (C0: pairing token support)
//
// Connects to the local Python backend via WebSocket (127.0.0.1 only).
// C0: Supports credential-based auth with per-install credentials, plus
// one-time pairing token flow. Backward compatible with legacy global secret.
//
// NEVER sends page content, executes arbitrary JS, or reads the DOM.
// Only chrome.tabs metadata and chrome.windows focus actions.

const STATE = {
  connected: false,
  ws: null,
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
  console.log("[ricky-bridge] stored state loaded",
    "installationId:", STATE.installationId ? "set" : "not set",
    "credential:", STATE.credential ? "set" : "not set",
    "profileId:", STATE.profileId || "none",
    "browserKind:", STATE.browserKind || "none");
}

async function ensureInstallationId() {
  if (STATE.installationId) return STATE.installationId;
  STATE.installationId = "inst_" + crypto.randomUUID().replace(/-/g, "").slice(0, 24);
  await chrome.storage.local.set({ installationId: STATE.installationId });
  console.log("[ricky-bridge] generated installationId:", STATE.installationId);
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
  console.log("[ricky-bridge] credential saved for profile:", data.profile_id);
}

async function saveSecret(secret) {
  STATE.pairingSecret = secret;
  await chrome.storage.local.set({ pairingSecret: secret });
}

async function getBrokerUrl() {
  const stored = await chrome.storage.local.get("brokerUrl");
  return stored.brokerUrl || "ws://127.0.0.1:9119";
}

// ---------------------------------------------------------------------------
// WebSocket lifecycle (C0: credential-based auth with pair flow)
// ---------------------------------------------------------------------------
function connect() {
  if (STATE.ws && (STATE.ws.readyState === WebSocket.OPEN || STATE.ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  getBrokerUrl().then((url) => {
    console.log("[ricky-bridge] connecting to", url);
    try {
      STATE.ws = new WebSocket(url);
    } catch (e) {
      console.error("[ricky-bridge] WebSocket constructor failed:", e);
      scheduleReconnect();
      return;
    }

    STATE.ws.onopen = () => {
      console.log("[ricky-bridge] ws open, sending auth");
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
        console.error("[ricky-bridge] unparseable message");
        return;
      }
      handleMessage(msg);
    };

    STATE.ws.onclose = () => {
      console.log("[ricky-bridge] ws closed");
      STATE.connected = false;
      STATE.ws = null;
      scheduleReconnect();
    };

    STATE.ws.onerror = (e) => {
      console.error("[ricky-bridge] ws error", e);
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
    console.log("[ricky-bridge] max reconnect attempts reached");
    return;
  }
  const delay = STATE.reconnectBaseMs * Math.pow(2, STATE.reconnectAttempts) + Math.random() * 500;
  STATE.reconnectAttempts++;
  console.log(`[ricky-bridge] reconnect ${STATE.reconnectAttempts}/${STATE.maxReconnectAttempts} in ${Math.round(delay)}ms`);
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
      const ws = new WebSocket(url);
      const timeout = setTimeout(() => {
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
          ws.close();
          resolve({ ok: false, error: msg.reason || "Pairing failed." });
        } else {
          ws.close();
          resolve({ ok: false, error: "Unexpected response." });
        }
      };

      ws.onerror = () => {
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
      console.log("[ricky-bridge] authenticated",
        payload.profile_id ? `profile=${payload.profile_id}` : "(legacy)");
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
      console.log("[ricky-bridge] paired successfully");
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
// Extension lifecycle (C0: ensure installation_id on first load)
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  console.log("[ricky-bridge] installed");
  ensureInstallationId().then(() => loadStoredState()).then(() => connect());
});

chrome.runtime.onStartup.addListener(() => {
  console.log("[ricky-bridge] startup");
  loadStoredState().then(() => connect());
});

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