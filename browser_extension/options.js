// Ricky Browser Bridge — options page script

const statusEl = document.getElementById("connection-status");
const secretInput = document.getElementById("pairing-secret");
const brokerUrlInput = document.getElementById("broker-url");
const saveStatusEl = document.getElementById("save-status");
const toggleBtn = document.getElementById("toggle-visibility");

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------

async function init() {
  // Load saved values
  const stored = await chrome.storage.local.get(["pairingSecret", "brokerUrl"]);
  if (stored.pairingSecret) secretInput.value = stored.pairingSecret;
  brokerUrlInput.value = stored.brokerUrl || "ws://127.0.0.1:9119";

  // Query current status from service worker
  refreshStatus();

  // Poll status every 2 seconds
  setInterval(refreshStatus, 2000);
}

async function refreshStatus() {
  try {
    const resp = await chrome.runtime.sendMessage({ type: "get_status" });
    if (resp.connected) {
      statusEl.className = "status connected";
      statusEl.textContent = "✅ Connected — Ricky can see your tabs.";
    } else if (resp.pairingSecret === "not set") {
      statusEl.className = "status disconnected";
      statusEl.textContent = "⚠ Not paired — enter the pairing secret from Ricky's settings.";
    } else {
      const attempts = resp.reconnectAttempts || 0;
      const max = resp.maxReconnectAttempts || 6;
      if (attempts > 0 && attempts < max) {
        statusEl.className = "status disconnected";
        statusEl.textContent = `⏳ Reconnecting (${attempts}/${max})... Is Ricky running?`;
      } else if (attempts >= max) {
        statusEl.className = "status auth-failed";
        statusEl.textContent = "❌ Could not connect. Check that Ricky is running and the pairing secret is correct.";
      } else {
        statusEl.className = "status disconnected";
        statusEl.textContent = "⏳ Not connected. Save the secret and Ricky should detect it.";
      }
    }
  } catch {
    statusEl.className = "status disconnected";
    statusEl.textContent = "⚠ Service worker not responding. Try reloading the extension.";
  }
}

// ---------------------------------------------------------------------------
// Event handlers
// ---------------------------------------------------------------------------

document.getElementById("save-secret").addEventListener("click", async () => {
  const secret = secretInput.value.trim();
  if (!secret) {
    saveStatusEl.textContent = "Please enter a pairing secret.";
    saveStatusEl.style.color = "#F44336";
    return;
  }
  if (secret.length < 32) {
    saveStatusEl.textContent = "Secret seems too short (min 32 characters).";
    saveStatusEl.style.color = "#F44336";
    return;
  }
  try {
    const resp = await chrome.runtime.sendMessage({ type: "update_secret", secret });
    if (resp.ok) {
      saveStatusEl.textContent = "✅ Saved! Reconnecting...";
      saveStatusEl.style.color = "#4CAF50";
    } else {
      saveStatusEl.textContent = "Failed to save.";
      saveStatusEl.style.color = "#F44336";
    }
  } catch (e) {
    saveStatusEl.textContent = `Error: ${e.message}`;
    saveStatusEl.style.color = "#F44336";
  }
});

document.getElementById("save-url").addEventListener("click", async () => {
  const url = brokerUrlInput.value.trim();
  if (!url) {
    saveStatusEl.textContent = "Please enter a broker URL.";
    saveStatusEl.style.color = "#F44336";
    return;
  }
  try {
    const resp = await chrome.runtime.sendMessage({ type: "update_broker_url", url });
    if (resp.ok) {
      saveStatusEl.textContent = "✅ URL saved, reconnecting...";
      saveStatusEl.style.color = "#4CAF50";
    }
  } catch (e) {
    saveStatusEl.textContent = `Error: ${e.message}`;
    saveStatusEl.style.color = "#F44336";
  }
});

document.getElementById("reconnect-btn").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "reconnect" });
  saveStatusEl.textContent = "Reconnecting...";
  saveStatusEl.style.color = "#aaa";
});

toggleBtn.addEventListener("click", () => {
  const isPassword = secretInput.type === "password";
  secretInput.type = isPassword ? "text" : "password";
  toggleBtn.textContent = isPassword ? "🙈" : "👁";
});