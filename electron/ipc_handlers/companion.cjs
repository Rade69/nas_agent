/** FAZA 12 companion orb IPC handlers — verbatim move from electron/main.cjs (R2d).
 *  Includes VALID_VOICE_STATES allowlist (moved from main.cjs, used only here). */
const {
  showCompanion,
  hideCompanion,
  toggleCompanion,
  forwardVoiceStateToCompanion,
  setLockedPosition,
} = require("../core/companionWindow.cjs");
const { getMainWindow } = require("../core/window.cjs");

function handleCompanionShow() {
  showCompanion();
  return { ok: true };
}

function handleCompanionHide() {
  hideCompanion();
  return { ok: true };
}

function handleCompanionToggle() {
  toggleCompanion();
  return { ok: true };
}

// Valid VoiceState values (mirror of src/lib/voiceState.ts VoiceState union).
// Kept here so the main process can validate before forwarding to the companion
// renderer without importing TS.
const VALID_VOICE_STATES = new Set([
  "idle",
  "listening",
  "transcribing",
  "thinking",
  "speaking",
  "waiting_confirmation",
  "interrupted",
  "muted",
  "error",
]);

// Main renderer -> main process -> companion renderer: forward VoiceState so
// the orb can display it without running its own Realtime client.
// FAZA S-4 (audit R3): validate against a fixed allowlist before forwarding.
// The payload comes from the (potentially XSS-compromised) main renderer and is
// pushed into a *second* renderer; only known state strings are allowed through
// so an attacker can't smuggle an arbitrary object/markup across windows.
function handleCompanionVoiceStateUpdate(_event, state) {
  if (typeof state !== "string" || !VALID_VOICE_STATES.has(state)) {
    return { ok: false, error: "Invalid voice state." };
  }
  forwardVoiceStateToCompanion(state);
  return { ok: true };
}

// Orb renderer -> main process: user clicked the orb (quick voice entry).
function handleCompanionClick() {
  // Bring main window forward and focus it so the user sees the conversation.
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    if (!main.isVisible()) main.show();
    main.focus();
  }
  return { ok: true };
}

// Orb renderer -> main process: user wants the main window.
function handleCompanionOpenMain() {
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    if (!main.isVisible()) main.show();
    main.focus();
  }
  return { ok: true };
}

// Orb renderer -> main process: toggle voice (start/stop listening). The actual
// voice start/stop lives in the main renderer's Realtime client; main forwards
// a request to it.
function handleCompanionToggleVoice() {
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    main.webContents.send("companion:toggle-voice");
  }
  return { ok: true };
}

function handleCompanionToggleLock(_event, locked) {
  setLockedPosition(locked === true);
  return { ok: true };
}

module.exports = { handleCompanionShow, handleCompanionHide, handleCompanionToggle, handleCompanionVoiceStateUpdate, handleCompanionClick, handleCompanionOpenMain, handleCompanionToggleVoice, handleCompanionToggleLock };
