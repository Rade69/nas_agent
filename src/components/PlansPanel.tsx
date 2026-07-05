import { Check, ListChecks, X } from "lucide-react";
import type { Plan, PlanStep, PlanStepStatus } from "../vite-env";

type PlansPanelProps = {
  visible: boolean;
  plans: Plan[];
  busyPlanId: string | null;
  busyStepId: string | null;
  onClose: () => void;
  onUpdatePlanStatus: (planId: string, status: Plan["status"]) => void;
  onUpdateStepStatus: (planId: string, stepId: string, status: PlanStepStatus) => void;
};

const STEP_STATUS_NEXT: Record<PlanStepStatus, PlanStepStatus | null> = {
  pending: "in_progress",
  in_progress: "completed",
  completed: "pending",
  skipped: "pending",
  failed: "pending",
};

const STEP_STATUS_LABEL: Record<PlanStepStatus, string> = {
  pending: "Pending",
  in_progress: "In progress",
  completed: "Completed",
  skipped: "Skipped",
  failed: "Failed",
};

function planStatusClass(status: Plan["status"]): string {
  return `plan-status-pill plan-status-${status}`;
}

export function PlansPanel({
  visible,
  plans,
  busyPlanId,
  busyStepId,
  onClose,
  onUpdatePlanStatus,
  onUpdateStepStatus,
}: PlansPanelProps) {
  if (!visible) return null;

  return (
    <section className="plans-panel" aria-label="Ricky plans and proposals">
      <header className="plans-header">
        <span className="plans-title">
          <ListChecks size={15} />
          <span>Ricky predlaže korake</span>
        </span>
        <small>{plans.length} planova</small>
        <button className="plans-close" onClick={onClose} aria-label="Close plans panel">
          <X size={14} />
        </button>
      </header>

      <div className="plans-list">
        {plans.length === 0 ? (
          <p className="plans-empty">Nema aktivnih planova.</p>
        ) : (
          plans.map((plan) => (
            <article key={plan.id} className="plan-card">
              <header className="plan-card-header">
                <strong>{plan.title}</strong>
                <span className={planStatusClass(plan.status)}>{plan.status}</span>
              </header>
              {plan.summary ? <p className="plan-summary">{plan.summary}</p> : null}

              <ol className="plan-steps">
                {plan.steps.map((step) => {
                  const stepBusy = busyPlanId === plan.id && busyStepId === step.id;
                  const next = STEP_STATUS_NEXT[step.status];
                  return (
                    <li key={step.id} className={`plan-step plan-step-${step.status}`}>
                      <span className="plan-step-index">{step.step_index + 1}</span>
                      <span className="plan-step-title">{step.title}</span>
                      <span className="plan-step-status">{STEP_STATUS_LABEL[step.status]}</span>
                      {next ? (
                        <button
                          className="plan-step-advance"
                          onClick={() => onUpdateStepStatus(plan.id, step.id, next)}
                          disabled={stepBusy}
                          title={`Advance to ${STEP_STATUS_LABEL[next]}`}
                        >
                          <Check size={12} />
                        </button>
                      ) : null}
                    </li>
                  );
                })}
              </ol>

              <footer className="plan-card-actions">
                {plan.status === "proposed" || plan.status === "draft" ? (
                  <button
                    className="plan-action plan-approve"
                    onClick={() => onUpdatePlanStatus(plan.id, "approved")}
                    disabled={busyPlanId === plan.id}
                  >
                    Approve plan
                  </button>
                ) : null}
                {plan.status === "approved" ? (
                  <button
                    className="plan-action plan-run"
                    onClick={() => onUpdatePlanStatus(plan.id, "running")}
                    disabled={busyPlanId === plan.id}
                  >
                    Start
                  </button>
                ) : null}
                {plan.status === "running" ? (
                  <button
                    className="plan-action plan-complete"
                    onClick={() => onUpdatePlanStatus(plan.id, "completed")}
                    disabled={busyPlanId === plan.id}
                  >
                    Mark completed
                  </button>
                ) : null}
                {plan.status !== "completed" && plan.status !== "rejected" && plan.status !== "cancelled" ? (
                  <button
                    className="plan-action plan-reject"
                    onClick={() => onUpdatePlanStatus(plan.id, "rejected")}
                    disabled={busyPlanId === plan.id}
                  >
                    Reject
                  </button>
                ) : null}
              </footer>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
