/** Full plans drawer view (FAZA 9) — tab-filtered plan list with step
 *  advancement, status badges, and create/approve/run/complete/reject
 *  actions. Localized via i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import type { Plan, PlanStatus, PlanStep, PlanStepStatus } from "../vite-env";
import IconSuccess from "../../assets/brending/icons/status/icon-status-success.svg?react";
import IconRunning from "../../assets/brending/icons/status/icon-status-running.svg?react";
import IconError from "../../assets/brending/icons/status/icon-status-error.svg?react";

type PlansPanelProps = {
  visible: boolean;
  plans: Plan[];
  loading: boolean;
  error: string | null;
  busyPlanId: string | null;
  busyStepId: string | null;
  onUpdatePlanStatus: (planId: string, status: Plan["status"]) => void;
  onUpdateStepStatus: (planId: string, stepId: string, status: PlanStepStatus) => void;
  onCreatePlan: (title: string, dueAt?: string | null) => void;
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

// P5: use persisted plan.due_at. The title prefix is kept only as a
// backwards-compatible fallback for plans created by the first P5 pass.
function parseDueDate(title: string, dueAt?: string | null): { date: Date | null; displayTitle: string; value: string | null } {
  if (dueAt) {
    const parsed = new Date(dueAt + "T23:59:59");
    if (!isNaN(parsed.getTime())) return { date: parsed, displayTitle: title, value: dueAt };
  }
  const match = title.match(/^\[📅(\d{4}-\d{2}-\d{2})\]\s*/);
  if (!match) return { date: null, displayTitle: title, value: null };
  const parsed = new Date(match[1] + "T23:59:59");
  if (isNaN(parsed.getTime())) return { date: null, displayTitle: title, value: null };
  return { date: parsed, displayTitle: title.slice(match[0].length), value: match[1] };
}

function dueBadge(date: Date): { label: string; className: string } | null {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const due = new Date(date);
  due.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((due.getTime() - now.getTime()) / 86400000);
  if (diffDays < 0) return { label: i18n.t("plans.overdue"), className: "plan-due-overdue" };
  if (diffDays === 0) return { label: i18n.t("plans.dueToday"), className: "plan-due-today" };
  if (diffDays <= 3) return { label: i18n.t("plans.dueSoon"), className: "plan-due-soon" };
  return { label: i18n.t("plans.dueUpcoming"), className: "plan-due-upcoming" };
}

export function PlansPanel({
  visible,
  plans,
  loading,
  error,
  busyPlanId,
  busyStepId,
  onUpdatePlanStatus,
  onUpdateStepStatus,
  onCreatePlan,
}: PlansPanelProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<PlanTab>("aktivni");
  // P0: inline creation form
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");

  if (!visible) {
    return null;
  }

  const filteredPlans = plans
    .filter((plan) => TAB_STATUSES[tab].includes(plan.status))
    // P5: sort by due date: overdue first, then soonest, then no deadline
    .sort((a, b) => {
      const da = parseDueDate(a.title, a.due_at).date;
      const db = parseDueDate(b.title, b.due_at).date;
      if (da && !db) return -1;
      if (!da && db) return 1;
      if (da && db) return da.getTime() - db.getTime();
      return 0;
    });

  // P0: per-tab empty state descriptions (more concrete than generic "empty")
  const emptyDescriptions: Record<PlanTab, string> = {
    aktivni: t("plans.emptyActive"),
    predlozeni: t("plans.emptyProposed"),
    zavrseni: t("plans.emptyCompleted"),
  };

  const handleSubmitNewPlan = () => {
    const trimmed = newTitle.trim();
    if (!trimmed) return;
    const dueDate = newDueDate.trim();
    onCreatePlan(trimmed, dueDate || null);
    setNewTitle("");
    setNewDueDate("");
    setIsCreating(false);
  };

  const handleTabClick = (planTab: PlanTab) => {
    setTab(planTab);
  };

  return (
    <section className="plans-panel" aria-label="Ricky plans and proposals">
      <div className="plans-tabs">
        {(Object.keys(TAB_STATUSES) as PlanTab[]).map((planTab) => (
          <button
            key={planTab}
            className={`plans-tab${tab === planTab ? " active" : ""}`}
            onClick={() => handleTabClick(planTab)}
          >
            {tabLabel(planTab)}
          </button>
        ))}
      </div>

      <div className="plans-list">
        {loading ? (
          <div className="plans-status">
            <Loader2 size={18} className="plans-spinner" />
            <span>{t("plans.loading")}</span>
          </div>
        ) : error ? (
          <div className="plans-status plans-status-error">
            <span>{error}</span>
          </div>
        ) : filteredPlans.length === 0 ? (
          <div className="plans-empty-container">
            <p className="plans-empty">{emptyDescriptions[tab]}</p>
          </div>
        ) : (
          filteredPlans.map((plan) => {
            const badge = statusBadge(plan.status);
            const { Icon, className } = statusIcon(plan.status);
            const { date: dueDate, displayTitle, value: dueValue } = parseDueDate(plan.title, plan.due_at);
            const due = dueDate ? dueBadge(dueDate) : null;
            return (
              <article key={plan.id} className="plan-card">
                <header className="plan-card-header">
                  <span className={`activity-icon ${className}`}>
                    <Icon className="activity-icon-svg" />
                  </span>
                  <div className="plan-card-titles">
                    <strong>{displayTitle}</strong>
                    {due ? (
                      <span className={`plan-due-badge ${due.className}`} title={dueValue || undefined}>
                        {due.label}{dueValue ? ` · ${dueValue}` : ""}
                      </span>
                    ) : null}
                    {plan.summary ? <span className="plan-summary">{plan.summary}</span> : null}
                  </div>
                  {plan.steps.length > 0 ? (
                    <span className="plan-progress">
                      {plan.steps.filter((s) => s.status === "completed" || s.status === "skipped").length}/{plan.steps.length}
                    </span>
                  ) : null}
                  <span className={`plan-badge ${badge.className}`}>{badge.label}</span>
                </header>

                {plan.steps.length > 0 ? (
                  <ol className="plan-steps">
                    {plan.steps.map((step: PlanStep, idx: number) => {
                      const stepBusy = busyPlanId === plan.id && busyStepId === step.id;
                      const next = STEP_STATUS_NEXT[step.status];
                      // P1: first pending/in_progress step is the "next" step
                      const isNext = step.status === "pending" || step.status === "in_progress";
                      const isFirstNext = isNext && !plan.steps.slice(0, idx).some((s) => s.status === "pending" || s.status === "in_progress");
                      const errorDetail = step.details?.error as string | undefined;
                      return (
                        <li key={step.id} className={`plan-step plan-step-${step.status}${isFirstNext ? " plan-step-next" : ""}`}>
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
                          {errorDetail ? (
                            <span className="plan-step-error">{errorDetail}</span>
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
                    <>
                      <button
                        className="plan-action plan-pause"
                        onClick={() => onUpdatePlanStatus(plan.id, "approved")}
                        disabled={busyPlanId === plan.id}
                      >
                        {t("plans.pause")}
                      </button>
                      <button
                        className="plan-action plan-complete"
                        onClick={() => onUpdatePlanStatus(plan.id, "completed")}
                        disabled={busyPlanId === plan.id}
                      >
                        {t("plans.complete")}
                      </button>
                    </>
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

                {/* P4: receipt for completed plans in Završeni tab */}
                {tab === "zavrseni" && plan.status === "completed" ? (
                  <div className="plan-receipt">
                    <div className="plan-receipt-summary">
                      <span className="plan-receipt-stat plan-receipt-ok">
                        ✓ {plan.steps.filter((s) => s.status === "completed").length} {t("plans.done")}
                      </span>
                      {plan.steps.filter((s) => s.status === "failed").length > 0 ? (
                        <span className="plan-receipt-stat plan-receipt-fail">
                          ✗ {plan.steps.filter((s) => s.status === "failed").length} {t("plans.failed")}
                        </span>
                      ) : null}
                      {plan.steps.filter((s) => s.status === "skipped").length > 0 ? (
                        <span className="plan-receipt-stat plan-receipt-skip">
                          — {plan.steps.filter((s) => s.status === "skipped").length} {t("plans.skipped")}
                        </span>
                      ) : null}
                    </div>
                    {plan.steps.filter((s) => s.status === "failed").length > 0 ? (
                      <div className="plan-receipt-failures">
                        <span className="plan-receipt-failures-label">{t("plans.failuresLabel")}:</span>
                        {plan.steps.filter((s) => s.status === "failed").map((s) => (
                          <div key={s.id} className="plan-receipt-failure">
                            <span>{s.step_index + 1}. {s.title}</span>
                            {s.details?.error ? (
                              <span className="plan-receipt-failure-reason">{String(s.details.error)}</span>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                    <div className="plan-receipt-actions">
                      <button
                        className="plan-action plan-report"
                        onClick={() => {
                          // P4: generate agent report draft
                          const report = [
                            `# Agent Report — ${plan.title}`,
                            ``,
                            `- Plan ID: ${plan.id}`,
                            `- Status: completed`,
                            `- Steps: ${plan.steps.filter((s) => s.status === "completed").length}/${plan.steps.length} done`,
                            ``,
                            `## Steps`,
                            ...plan.steps.map((s) =>
                              `- [${s.status === "completed" ? "x" : " "}] ${s.title}${s.details?.error ? ` — ERROR: ${s.details.error}` : ""}`
                            ),
                          ].join("\n");
                          navigator.clipboard.writeText(report).catch(() => {});
                          alert(t("plans.reportCopied"));
                        }}
                      >
                        {t("plans.saveReport")}
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </div>

      {/* P0: inline creation form or new-plan button */}
      {isCreating ? (
        <div className="plans-create-form">
          <input
            className="plans-create-input"
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmitNewPlan();
              if (e.key === "Escape") { setIsCreating(false); setNewTitle(""); setNewDueDate(""); }
            }}
            placeholder={t("plans.newPlanPlaceholder")}
            autoFocus
          />
          <input
            className="plans-create-input"
            type="date"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            placeholder={t("plans.dueDate")}
            title={t("plans.dueDateHint")}
          />
          <div className="plans-create-actions">
            <button className="pixel-primary" onClick={handleSubmitNewPlan} disabled={!newTitle.trim()}>
              {t("plans.create")}
            </button>
            <button
              className="pixel-secondary"
              onClick={() => { setIsCreating(false); setNewTitle(""); }}
            >
              {t("plans.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <button className="plans-new-btn" onClick={() => setIsCreating(true)}>
          {t("previews.newPlan")}
        </button>
      )}
    </section>
  );
}
