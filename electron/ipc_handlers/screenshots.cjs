/** Screenshot gallery/retention IPC handlers. Same thin-passthrough pattern
 *  as settings.cjs. Context: agent_reports/2026-07-12_screenshot-privacy.md */
const { listScreenshots, deleteAllScreenshots } = require("../services/pythonClient.cjs");

async function handleScreenshotsList() {
  return await listScreenshots({});
}

async function handleScreenshotsDeleteAll() {
  return await deleteAllScreenshots({});
}

module.exports = { handleScreenshotsList, handleScreenshotsDeleteAll };
