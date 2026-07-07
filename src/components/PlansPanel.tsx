import { useState } from "react";
import { Check } from "lucide-react";
import type { Plan, PlanStatus, PlanStep, PlanStepStatus } from "../vite-env";
import IconSuccess from "../../assets/brending/icons/status/icon-status-success.svg?react";
import IconRunning from "../../assets/brending/icons/status/icon-status-running.svg?react";
import IconError from "../../assets/brending/icons/status/icon-status-error.svg?react";

type PlansPanelProps = {
  visible: boolean;
  plans: Plan[];
  busyPlanId: string | null;
  busyStepId: string | null;
  onUpdatePlanStatus: (planId: string, status: Plan["status"]) => void;
  onUpdateStepStatus: (planId: string, stepId: string, status: PlanStepStatus) => void;
  onCreatePlan: () => void;
};

const STEP_STATUS_NEXT: Record<PlanStepStatus, PlanStepStatus | null> = {
  pending: "in_progress",
  in_progress: "completed",
  completed: "pending",
  skipped: "pending",
  failed: "pending",
};

const STEP_STATUS_LABEL: Record<PlanStepStatus, string> = {
  pending: "Na čekanju",
  in_progress: "U toku",
  completed: "Završeno",
  skipped: "Preskočeno",
  failed: "Neuspješno",
};

// Matches assets/GUI-SETS/GUI-SET-5.png "Plans Drawer" — three tabs
// grouping the backend's finer-grained PlanStatus values.
type PlanTab = "aktivni" | "predlozeni" | "zavrseni";

const TAB_STATUSES: Record<PlanTab, PlanStatus[]> = {
  aktivni: ["approved", "running"],
  predlozeni: ["draft", "proposed"],
  zavrseni: ["completed", "rejected", "cancelled"],
};

const TAB_LABEL: Record<PlanTab, string> = {
  aktivni: "Aktivni",
  predlozeni: "Predloženi",
  zavrseni: "Završeni",
};

function statusBadge(status: PlanStatus): { label: string; className: string } {
  if (status === "approved" || status === "running") return { label: "AKTIVAN", className: "plan-badge-active" };
  if (status === "draft" || status === "proposed") return { label: "NA ČEKANJU", className: "plan-badge-pending" };
  if (status === "completed") return { label: "ZAVRŠENO", className: "plan-badge-done" };
  return { label: status === "cancelled" ? "OTKAZANO" : "ODBAČENO", className: "plan-badge-rejected" };
}

function statusIcon(status: PlanStatus) {
  if (status === "approved" || status === "running" || status === "completed") {
    return { Icon: IconSuccess, className: "activity-icon-success" };
  }
  if (status === "draft" || status === "proposed") {
    return { Icon: IconRunning, className: "activity-icon-tool" };
  }
  return { Icon: IconError, className: "activity-icon-error" };
}

export function PlansPanel({
  visible,
  plans,
  busyPlanId,
  busyStepId,
  onUpdatePlanStatus,
  onUpdateStepStatus,
  onCreatePlan,
}: PlansPanelProps) {
  const [tab, setTab] = useState<PlanTab>("aktivni");
  if (!visible) return null;

  const filteredPlans = plans.filter((plan) => TAB_STATUSES[tab].includes(plan.status));

  return (
    <section className="plans-panel" aria-label="Ricky plans and proposals">
      <div className="plans-tabs">
        {(Object.keys(TAB_LABEL) as PlanTab[]).map((t) => (
          <button
            key={t}
            className={`plans-tab${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {TAB_LABEL[t]}
          </button>
        ))}
      </div>

      <div className="plans-list">
        {filteredPlans.length === 0 ? (
          <p className="plans-empty">Nema planova u ovoj kategoriji.</p>
        ) : (
          filteredPlans.map((plan) => {
            const badge = statusBadge(plan.status);
            const { Icon, className } = statusIcon(plan.status);
            return (
              <article key={plan.id} className="plan-card">
                <header className="plan-card-header">
                  <span className={`activity-icon ${className}`}>
                    <Icon className="activity-icon-svg" />
                  </span>
                  <div className="plan-card-titles">
                    <strong>{plan.title}</strong>
                    {plan.summary ? <span className="plan-summary">{plan.summary}</span> : null}
                  </div>
                  <span className={`plan-badge ${badge.className}`}>{badge.label}</span>
                </header>

                {plan.steps.length > 0 ? (
                  <ol className="plan-steps">
                    {plan.steps.map((step: PlanStep) => {
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
                              title={`Pomjeri na: ${STEP_STATUS_LABEL[next]}`}
                            >
                              <Check size={12} />
                            </button>
                          ) : null}
                        </li>
                      );
                    })}
                  </ol>
                ) : null}

                <footer className="plan-card-actions">
                  {plan.status === "proposed" || plan.status === "draft" ? (
                    <button
                      className="plan-action plan-approve"
                      onClick={() => onUpdatePlanStatus(plan.id, "approved")}
                      disabled={busyPlanId === plan.id}
                    >
                      Odobri plan
                    </button>
                  ) : null}
                  {plan.status === "approved" ? (
                    <button
                      className="plan-action plan-run"
                      onClick={() => onUpdatePlanStatus(plan.id, "running")}
                      disabled={busyPlanId === plan.id}
                    >
                      Pokreni
                    </button>
                  ) : null}
                  {plan.status === "running" ? (
                    <button
                      className="plan-action plan-complete"
                      onClick={() => onUpdatePlanStatus(plan.id, "completed")}
                      disabled={busyPlanId === plan.id}
                    >
                      Označi završenim
                    </button>
                  ) : null}
                  {plan.status !== "completed" && plan.status !== "rejected" && plan.status !== "cancelled" ? (
                    <button
                      className="plan-action plan-reject"
                      onClick={() => onUpdatePlanStatus(plan.id, "rejected")}
                      disabled={busyPlanId === plan.id}
                    >
                      Odbaci
                    </button>
                  ) : null}
                </footer>
              </article>
            );
          })
        )}
      </div>

      <button className="plans-new-btn" onClick={onCreatePlan}>
        Novi plan
      </button>
    </section>
  );
}
