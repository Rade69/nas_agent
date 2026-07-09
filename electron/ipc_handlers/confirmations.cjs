/** FAZA 9 confirmations IPC handlers — verbatim move from electron/main.cjs (R2d). */
const {
  requestJson,
  listPendingConfirmations,
  createConfirmation,
  approveConfirmation,
  rejectConfirmation,
  cancelConfirmation,
} = require("../services/pythonClient.cjs");

async function handleConfirmationsList(_event, payload = {}) {
  const { status, limit } = payload || {};
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  const path = params.toString() ? `/confirmations?${params.toString()}` : "/confirmations";
  return await requestJson(path, {});
}

async function handleConfirmationsPending() {
  return await listPendingConfirmations({});
}

async function handleConfirmationCreate(_event, payload) {
  return await createConfirmation(payload || {});
}

async function handleConfirmationApprove(_event, confirmationId) {
  return await approveConfirmation(confirmationId);
}

async function handleConfirmationReject(_event, confirmationId) {
  return await rejectConfirmation(confirmationId);
}

async function handleConfirmationCancel(_event, confirmationId) {
  return await cancelConfirmation(confirmationId);
}

module.exports = { handleConfirmationsList, handleConfirmationsPending, handleConfirmationCreate, handleConfirmationApprove, handleConfirmationReject, handleConfirmationCancel };
