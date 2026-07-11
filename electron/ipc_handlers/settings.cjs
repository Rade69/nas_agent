/** User-facing settings IPC handlers (display name in the prompt, future
 *  settings panel additions). Same thin-passthrough pattern as plans.cjs.
 *  Context: agent_reports/2026-07-11_settings-panel-foundation.md */
const { getSettings, updateSettings } = require("../services/pythonClient.cjs");

async function handleSettingsGet() {
  return await getSettings({});
}

async function handleSettingsUpdate(_event, payload) {
  return await updateSettings(payload || {});
}

module.exports = { handleSettingsGet, handleSettingsUpdate };
