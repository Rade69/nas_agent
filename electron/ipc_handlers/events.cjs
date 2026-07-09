/** FAZA 11 event bridge IPC handler — verbatim move from electron/main.cjs (R2d). */
const { listEvents } = require("../services/pythonClient.cjs");

async function handleEventsList(_event, since) {
  return await listEvents(typeof since === "string" ? since : undefined);
}

module.exports = { handleEventsList };
