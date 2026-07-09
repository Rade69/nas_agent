/** FAZA 9 plans IPC handlers — verbatim move from electron/main.cjs (R2d). */
const {
  listPlans,
  createPlan,
  getPlan,
  updatePlan,
  updatePlanStep,
} = require("../services/pythonClient.cjs");

async function handlePlansList() {
  return await listPlans({});
}

async function handlePlanCreate(_event, payload) {
  return await createPlan(payload || {});
}

async function handlePlanGet(_event, planId) {
  return await getPlan(planId);
}

async function handlePlanUpdate(_event, { planId, payload }) {
  return await updatePlan(planId, payload || {});
}

async function handlePlanStepUpdate(_event, { planId, stepId, payload }) {
  return await updatePlanStep(planId, stepId, payload || {});
}

module.exports = { handlePlansList, handlePlanCreate, handlePlanGet, handlePlanUpdate, handlePlanStepUpdate };
