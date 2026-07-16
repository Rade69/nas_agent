// Ricky Browser Bridge — MV3 service worker
//
// Connects to the local Python backend via WebSocket (127.0.0.1 only),
// authenticates with a pairing secret, then executes commands:
//   list_tabs  → returns current-window tab metadata
//   activate   → focuses a window and activates a tab by id
//   close      → closes a tab by id (only if confirmed)
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
  pairingSecret: null,
  processedRequestIds: new Set(), // deduplication
};

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------
async function loadSecret() {
  const stored = await chrome.storage.local.get("pairingSecret");
  STATE.pairingSecret = stored.pairingSecret || null;
  console.log(
    "[ricky-bridge] pairingSecret",
    STATE.pairingSecret ? "loaded" : "not set"
  );
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
// WebSocket lifecycle
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

      // Send auth handshake
      const secret = STATE.pairingSecret || "";
      sendMessage({ type: "auth", secret });
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
      // onclose will fire after this
    };
  });
}

function disconnect() {
  if (STATE.reconnectTimer) {
    clearTimeout(STATE.reconnectTimer);
    STATE.reconnectTimer = null;
  }
  STATE.reconnectAttempts = STATE.maxReconnectAttempts; // stop reconnecting
  if (STATE.ws) {
    STATE.ws.onclose = null; // don't schedule reconnect
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
      console.log("[ricky-bridge] authenticated");
      // After successful auth, store session_id for reconnects if needed
      if (payload.session_id) {
        await chrome.storage.local.set({ sessionId: payload.session_id });
      }
      // Update extension badge
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

    case "ping": {
      sendMessage({ type: "pong", request_id });
      break;
    }

    default:
      console.warn("[ricky-bridge] unknown message type:", type);
  }
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

async function handleListTabs(requestId, { scope }) {
  // Deduplicate
  if (requestId && STATE.processedRequestIds.has(requestId)) {
    console.log("[ricky-bridge] duplicate list_tabs, ignoring", requestId);
    return;
  }
  if (requestId) STATE.processedRequestIds.add(requestId);

  try {
    const queryInfo = scope === "all_windows" ? {} : { currentWindow: true };
    const tabs = await chrome.tabs.query(queryInfo);

    // Chrome returns tabs in display order; pinned tabs come first
    const listed = tabs.map((tab, index) => ({
      position: index + 1, // 1-based for the user
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
    const tabId = Number(tab_id);
    const windowId = Number(window_id);

    // First focus the window
    await chrome.windows.update(windowId, { focused: true });
    // Then activate the tab
    await chrome.tabs.update(tabId, { active: true });

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
    const tabId = Number(tab_id);
    await chrome.tabs.remove(tabId);

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

// ---------------------------------------------------------------------------
// Extension lifecycle
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  console.log("[ricky-bridge] installed");
  loadSecret().then(() => connect());
});

chrome.runtime.onStartup.addListener(() => {
  console.log("[ricky-bridge] startup");
  loadSecret().then(() => connect());
});

// Listen for messages from the options page
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "update_secret") {
    saveSecret(msg.secret).then(() => {
      disconnect();
      connect();
      sendResponse({ ok: true });
    });
    return true; // async response
  }
  if (msg.type === "get_status") {
    sendResponse({
      connected: STATE.connected,
      pairingSecret: STATE.pairingSecret ? "set" : "not set",
      reconnectAttempts: STATE.reconnectAttempts,
      maxReconnectAttempts: STATE.maxReconnectAttempts,
    });
    return false;
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
  return false;
});

// Start connection on load
loadSecret().then(() => connect());