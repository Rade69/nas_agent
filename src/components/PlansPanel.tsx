/** Full plans drawer view (FAZA 9) — tab-filtered plan list with step
 *  advancement, status badges, and create/approve/run/complete/reject
 *  actions. Localized via i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useState } from "react";
import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
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

// Plain function van React stabla — koristi i18n.t() direktno (isti pattern
// kao voiceStateLabel() i planStatusLabel() iz PR-1).
function stepStatusLabel(status: PlanStepStatus): string {
  const map: Record<PlanStepStatus, string> = {
    pending: "plans.stepStatus.pending",
    in_progress: "plans.stepStatus.inProgress",
    completed: "plans.stepStatus.completed",
    skipped: "plans.stepStatus.skipped",
    failed: "plans.stepStatus.failed",
  };
  return i18n.t(map[status]);
}

// Matches assets/GUI-SETS/GUI-SET-5.png "Plans Drawer" — three tabs
// grouping the backend's finer-grained PlanStatus values.
type PlanTab = "aktivni" | "predlozeni" | "zavrseni";

const TAB_STATUSES: Record<PlanTab, PlanStatus[]> = {
  aktivni: ["approved", "running"],
  predlozeni: ["draft", "proposed"],
  zavrseni: ["completed", "rejected", "cancelled"],
};

// Reuse previews.tabActive / previews.tabProposed / previews.tabCompleted —
// identičan tekst kao Previews.tsx PlansDrawerPreview, jedan izvor istine.
function tabLabel(tab: PlanTab): string {
  const map: Record<PlanTab, string> = {
    aktivni: "previews.tabActive",
    predlozeni: "previews.tabProposed",
    zavrseni: "previews.tabCompleted",
  };
  return i18n.t(map[tab]);
}

// plans.status.* — NAMJERNO zaseban namespace od planStatus.* (Previews.tsx).
// Tekst je bio drugačiji i prije i18n-a (npr. "ZAVRŠEN" vs "ZAVRŠENO"), plus
// PlansPanel ima peti status "ODBAČENO" koji Previews nema. Vjerno prevedeno
// onakvo kakvo jeste — ne "ispravljati" postojeću nekonzistentnost usput.
// Context: docs/PI_TASK_GUI_LOCALIZATION_PR2_BRIEF.md
function statusBadge(status: PlanStatus): { label: string; className: string } {
  if (status === "approved" || status === "running") return { label: i18n.t("plans.status.active"), className: "plan-badge-active" };
  if (status === "draft" || status === "proposed") return { label: i18n.t("plans.status.pending"), className: "plan-badge-pending" };
  if (status === "completed") return { label: i18n.t("plans.status.completed"), className: "plan-badge-done" };
  // Original: "OTKAZANO" : "ODBAČENO"
  return {
    label: status === "cancelled" ? i18n.t("plans.status.cancelled") : i18n.t("plans.status.rejected"),
    className: "plan-badge-rejected",
  };
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
  const { t } = useTranslation();
  const [tab, setTab] = useState<PlanTab>("aktivni");
  if (!visible) return null;

  const filteredPlans = plans.filter((plan) => TAB_STATUSES[tab].includes(plan.status));

  return (
    <section className="plans-panel" aria-label="Ricky plans and proposals">
      <div className="plans-tabs">
        {(Object.keys(TAB_STATUSES) as PlanTab[]).map((planTab) => (
          <button
            key={planTab}
            className={`plans-tab${tab === planTab ? " active" : ""}`}
            onClick={() => setTab(planTab)}
          >
            {tabLabel(planTab)}
          </button>
        ))}
      </div>

      <div className="plans-list">
        {filteredPlans.length === 0 ? (
          <p className="plans-empty">{t("plans.empty")}</p>
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
                          <span className="plan-step-status">{stepStatusLabel(step.status)}</span>
                          {next ? (
                            <button
                              className="plan-step-advance"
                              onClick={() => onUpdateStepStatus(plan.id, step.id, next)}
                              disabled={stepBusy}
                              title={t("plans.advanceTo", { status: stepStatusLabel(next) })}
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
                      {t("plans.approve")}
                    </button>
                  ) : null}
                  {plan.status === "approved" ? (
                    <button
                      className="plan-action plan-run"
                      onClick={() => onUpdatePlanStatus(plan.id, "running")}
                      disabled={busyPlanId === plan.id}
                    >
                      {t("plans.run")}
                    </button>
                  ) : null}
                  {plan.status === "running" ? (
                    <button
                      className="plan-action plan-complete"
                      onClick={() => onUpdatePlanStatus(plan.id, "completed")}
                      disabled={busyPlanId === plan.id}
                    >
                      {t("plans.complete")}
                    </button>
                  ) : null}
                  {plan.status !== "completed" && plan.status !== "rejected" && plan.status !== "cancelled" ? (
                    <button
                      className="plan-action plan-reject"
                      onClick={() => onUpdatePlanStatus(plan.id, "rejected")}
                      disabled={busyPlanId === plan.id}
                    >
                      {t("plans.reject")}
                    </button>
                  ) : null}
                </footer>
              </article>
            );
          })
        )}
      </div>

      <button className="plans-new-btn" onClick={onCreatePlan}>
        {t("previews.newPlan")}
      </button>
    </section>
  );
}
