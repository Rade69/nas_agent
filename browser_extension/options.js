// Ricky Browser Bridge — options page script (C0: pairing code flow)

const statusEl = document.getElementById("connection-status");
const codeInput = document.getElementById("pairing-code");
const browserKindSelect = document.getElementById("browser-kind");
const profileLabelInput = document.getElementById("profile-label");
const saveStatusEl = document.getElementById("save-status");
const pairBtn = document.getElementById("pair-btn");
const secretInput = document.getElementById("pairing-secret");
const brokerUrlInput = document.getElementById("broker-url");
const toggleBtn = document.getElementById("toggle-visibility");
const legacySection = document.getElementById("legacy-section");

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------
async function init() {
  // Load saved broker URL
  const stored = await chrome.storage.local.get(["brokerUrl", "pairingSecret", "browserKind"]);
  brokerUrlInput.value = stored.brokerUrl || "ws://127.0.0.1:9119";
  if (stored.pairingSecret) secretInput.value = stored.pairingSecret;
  if (stored.browserKind) browserKindSelect.value = stored.browserKind;

  refreshStatus();
  setInterval(refreshStatus, 2000);
}

async function refreshStatus() {
  try {
    const resp = await chrome.runtime.sendMessage({ type: "get_status" });
    if (resp.connected) {
      statusEl.className = "status connected";
      const profile = resp.profileLabel || "Default";
      const browser = resp.browserKind || "browser";
      statusEl.innerHTML = `✅ <strong>Connected</strong> — ${browser} / ${profile}<br><small>Profile: ${resp.profileId || "—"} | Install: ${resp.installationId || "—"}</small>`;
      hidePairingSection();
    } else if (resp.credential === "set") {
      statusEl.className = "status disconnected";
      statusEl.textContent = "⏳ Paired but not connected. Is Ricky running?";
    } else if (resp.pairingSecret === "set" || resp.installationId) {
      statusEl.className = "status disconnected";
      statusEl.textContent = "⚠ Not paired. Enter a pairing code from Ricky's Settings or use the Legacy section.";
    } else {
      statusEl.className = "status disconnected";
      statusEl.textContent = "⚠ Not configured. Enter a pairing code to get started.";
    }

    if (resp.reconnectAttempts > 0 && resp.reconnectAttempts < resp.maxReconnectAttempts) {
      statusEl.className = "status pairing";
      statusEl.textContent = `⏳ Reconnecting (${resp.reconnectAttempts}/${resp.maxReconnectAttempts})...`;
    }
  } catch {
    statusEl.className = "status disconnected";
    statusEl.textContent = "⚠ Service worker not responding. Try reloading the extension.";
  }
}

function hidePairingSection() {
  // Don't hide completely — user might want to re-pair
}

// ---------------------------------------------------------------------------
// C0: Pair with one-time code
// ---------------------------------------------------------------------------
pairBtn.addEventListener("click", async () => {
  const code = codeInput.value.trim().toUpperCase();
  const browserKind = browserKindSelect.value;
  const profileLabel = profileLabelInput.value.trim() || "Default";

  if (!code || code.length < 4) {
    saveStatusEl.textContent = "Enter the 6-character pairing code.";
    saveStatusEl.style.color = "#F44336";
    return;
  }

  pairBtn.disabled = true;
  pairBtn.textContent = "Pairing...";
  saveStatusEl.textContent = "Connecting to Ricky backend...";
  saveStatusEl.style.color = "#aaa";

  try {
    const resp = await chrome.runtime.sendMessage({
      type: "pair",
      code,
      browserKind,
      profileLabel,
    });

    if (resp.ok) {
      saveStatusEl.textContent = "✅ Paired! Connected as " + browserKind + " / " + profileLabel;
      saveStatusEl.style.color = "#4CAF50";
      codeInput.value = "";
    } else {
      saveStatusEl.textContent = "❌ " + (resp.error || "Pairing failed.");
      saveStatusEl.style.color = "#F44336";
    }
  } catch (e) {
    saveStatusEl.textContent = "Error: " + e.message;
    saveStatusEl.style.color = "#F44336";
  } finally {
    pairBtn.disabled = false;
    pairBtn.textContent = "Pair Now";
  }
});

// ---------------------------------------------------------------------------
// Legacy: manual secret
// ---------------------------------------------------------------------------
document.getElementById("save-secret").addEventListener("click", async () => {
  const secret = secretInput.value.trim();
  if (!secret || secret.length < 32) {
    saveStatusEl.textContent = "Secret too short (min 32 chars).";
    saveStatusEl.style.color = "#F44336";
    return;
  }
  try {
    await chrome.runtime.sendMessage({ type: "update_secret", secret });
    saveStatusEl.textContent = "✅ Saved! Reconnecting...";
    saveStatusEl.style.color = "#4CAF50";
  } catch (e) {
    saveStatusEl.textContent = "Error: " + e.message;
    saveStatusEl.style.color = "#F44336";
  }
});

document.getElementById("save-url").addEventListener("click", async () => {
  const url = brokerUrlInput.value.trim();
  if (!url) return;
  try {
    await chrome.runtime.sendMessage({ type: "update_broker_url", url });
    saveStatusEl.textContent = "✅ URL saved.";
    saveStatusEl.style.color = "#4CAF50";
  } catch (e) {
    saveStatusEl.textContent = "Error: " + e.message;
    saveStatusEl.style.color = "#F44336";
  }
});

document.getElementById("reconnect-btn").addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "reconnect" });
  saveStatusEl.textContent = "Reconnecting...";
  saveStatusEl.style.color = "#aaa";
});

document.getElementById("reset-btn").addEventListener("click", async () => {
  if (!confirm("Reset pairing? You'll need to re-pair with a new code from Ricky's Settings.")) return;
  await chrome.runtime.sendMessage({ type: "reset_pairing" });
  saveStatusEl.textContent = "Pairing reset.";
  saveStatusEl.style.color = "#aaa";
  location.reload();
});

toggleBtn.addEventListener("click", () => {
  const isPassword = secretInput.type === "password";
  secretInput.type = isPassword ? "text" : "password";
  toggleBtn.textContent = isPassword ? "🙈" : "👁";
});