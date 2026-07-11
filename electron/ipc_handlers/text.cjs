/** Dictation Mode "Doradi" menu IPC handler. Same thin-passthrough pattern
 *  as settings.cjs. Context: agent_reports/2026-07-11_dictation-rewrite-menu.md */
const { rewriteText } = require("../services/pythonClient.cjs");

async function handleTextRewrite(_event, payload) {
  return await rewriteText(payload || {});
}

module.exports = { handleTextRewrite };
