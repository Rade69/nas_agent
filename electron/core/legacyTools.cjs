// Context: agent_reports/2026-07-06_faza17-disable-legacy-powershell.md
// FAZA 17: legacy PowerShell tool feature flag. When FAZA 13/14 add Python
// computer-use tools, the default flips to 0. Until then, legacy stays on so
// computer_* tools (open_app/type_text/press_key/click/scroll) keep working.
//
// Set RICKY_USE_LEGACY_POWERSHELL_TOOLS=0 in .env.local or via process env to
// disable all legacy PowerShell-based tools (computer_*, screen_snapshot,
// ui_inspect, note_add, records_*, artifact_*, web_search, image_generate).
// When disabled, the app relies exclusively on the Python backend for tool
// execution. Tools that have no Python equivalent yet (computer_open_app,
// computer_type_text, computer_press_key, computer_click, computer_scroll)
// will return an error until FAZA 13/14 land.

const LEGACY_FLAG = "RICKY_USE_LEGACY_POWERSHELL_TOOLS";

// Name this set to match the PHASE11_DELEGATED_TOOLS set — these are the tools
// that already have Python equivalents and should prefer Python unless the
// flag forces legacy mode.
const TOOLS_WITH_PYTHON_EQUIVALENT = new Set([
  "note_add",
  "note_search",
  "note_list",
  "records_create",
  "records_search",
  "records_update",
  "records_delete",
  "artifact_create",
  "artifact_get",
  "artifact_list",
  "artifact_show",
  "screen_snapshot",
  "ui_inspect",
  "web_search",
  "image_generate",
  // FAZA 13: computer-use tools now have Python equivalents.
  "computer_open_app",
  "computer_type_text",
  "computer_press_key",
  "computer_click",
  "computer_scroll",
  // FAZA 14: element-targeting tools now have Python equivalents.
  "computer_find_elements",
  "computer_click_element",
  "computer_set_text_element",
  "computer_get_element_text",
]);

// FAZA 13 added these; FAZA 14 will add more when element targeting lands.
const TOOLS_PENDING_PYTHON_EQUIVALENT = new Set([
]);

/**
 * Read the feature flag once per session. When unset or "1", legacy tools are
 * available. When explicitly "0", all legacy paths are gated — tools with
 * Python replacements use them exclusively, and tools without Python
 * replacements return a structured error.
 */
function isLegacyEnabled() {
  const raw = (process.env[LEGACY_FLAG] || "0").trim();
  return raw !== "0" && raw.toLowerCase() !== "false";
}

/**
 * Return true if the given tool name is known to have a Python equivalent that
 * should be preferred over the legacy Electron/JSON-db implementation.
 */
function hasPythonEquivalent(name) {
  return TOOLS_WITH_PYTHON_EQUIVALENT.has(name);
}

/**
 * Return true if the given tool name requires legacy PowerShell and has no
 * Python equivalent yet (computer_* tools pending FAZA 13/14).
 */
function hasNoPythonYet(name) {
  return TOOLS_PENDING_PYTHON_EQUIVALENT.has(name);
}

/**
 * Build a structured error response for when a legacy tool is blocked because
 * the feature flag is off and no Python equivalent exists yet.
 */
function blockLegacyResponse(name) {
  return {
    ok: false,
    error: `Legacy tool '${name}' is disabled (${LEGACY_FLAG}=0) and no Python equivalent is available yet. Enable the legacy flag or wait for FAZA 13/14.`,
    errorCode: "LEGACY_DISABLED",
  };
}

module.exports = {
  LEGACY_FLAG,
  isLegacyEnabled,
  hasPythonEquivalent,
  hasNoPythonYet,
  blockLegacyResponse,
};
