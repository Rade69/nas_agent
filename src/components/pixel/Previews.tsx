/** Pixel mockup drawer previews — confirmation / activity / plans empty states.
 *  Verbatim move from App.tsx (R3 refactor). Later localized (Localization
 *  PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md). */
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import IconWarning from "../../../assets/brending/icons/safety/icon-warning.svg?react";
import IconSuccess from "../../../assets/brending/icons/status/icon-status-success.svg?react";
import IconBackend from "../../../assets/brending/icons/system/icon-backend.svg?react";
import { categoryForActivity } from "../../lib/activityIcons";
import type { ActivityEvent } from "../../lib/realtime";
import type { Confirmation, Plan } from "../../vite-env";

// Was previously hardcoded example content (fake "Pošalji email" card) shown
// unconditionally regardless of real state — that caused a real confirmation
// (via the separate ConfirmationDialog modal) to visually look like it was
// being asked twice. Now reflects the actual pendingConfirmation state; the
// real approve/reject/cancel actions stay exclusively on ConfirmationDialog
// (this panel is read-only glanceable awareness, not a second action surface).
// Context: agent_reports/2026-07-10_dictation-and-dashboard-fixes.md
export function ConfirmationPreview({ confirmation }: { confirmation: Confirmation | null }) {
  const { t } = useTranslation();
  if (!confirmation) {
    return (
      <div className="pixel-confirmation-preview">
        <EmptyPreviewState
          title={t("previews.noConfirmation")}
          detail={t("previews.noConfirmationDetail")}
        />
      </div>
    );
  }
  return (
    <div className="pixel-confirmation-preview">
      <div className="pixel-blurred-shell" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <article className="pixel-confirm-card">
        <div className="pixel-warning-icon">
          <IconWarning />
        </div>
        <div className="pixel-confirm-content">
          <h3>{t("previews.confirmTitle")}</h3>
          <p>{confirmation.summary || t("previews.confirmDefaultSummary")}</p>
          <dl className="pixel-confirm-table">
            <div>
              <dt>{t("previews.actionLabel")}</dt>
              <dd>{confirmation.action_name}</dd>
            </div>
            <div>
              <dt>{t("previews.riskLabel")}</dt>
              <dd>
                <span className="pixel-risk-badge">{confirmation.risk_level.toUpperCase()}</span>
              </dd>
            </div>
          </dl>
          <p className="pixel-confirm-link">{t("previews.respondInDialog")}</p>
        </div>
      </article>
    </div>
  );
}

export function ActivityDrawerPreview({ activityEvents }: { activityEvents: ActivityEvent[] }) {
  const { t } = useTranslation();
  return (
    <aside className="pixel-preview-drawer">
      <header>
        <strong>{t("tabs.activity")}</strong>
      </header>
      <div className="pixel-preview-list">
        {activityEvents.length > 0 ? (
          activityEvents.slice(0, 5).map((event) => {
            const { Icon, className } = categoryForActivity(event);
            return (
              <article className="pixel-preview-row" key={event.id}>
                <span className={`pixel-preview-icon ${className}`}>
                  <Icon />
                </span>
                <span>
                  <strong>{event.title}</strong>
                  {event.detail ? <small>{event.detail}</small> : null}
                </span>
                <time>{event.at}</time>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title={t("previews.noActivityShort")} detail={t("previews.noActivityShortDetail")} />
        )}
      </div>
      <button className="pixel-full-history">{t("previews.showFullHistory")}</button>
    </aside>
  );
}

export function PlansDrawerPreview({ plans }: { plans: Plan[] }) {
  const { t } = useTranslation();
  return (
    <aside className="pixel-preview-drawer pixel-preview-plans">
      <header>
        <strong>{t("tabs.plans")}</strong>
      </header>
      <div className="pixel-plan-tabs">
        <button className="active">{t("previews.tabActive")}</button>
        <button>{t("previews.tabProposed")}</button>
        <button>{t("previews.tabCompleted")}</button>
      </div>
      <div className="pixel-preview-list">
        {plans.length > 0 ? (
          plans.slice(0, 4).map((plan) => {
            const status = planStatusLabel(plan.status);
            return (
              <article className="pixel-plan-row" key={plan.id}>
                <span className={`pixel-preview-icon ${plan.status === "completed" ? "success" : "voice"}`}>
                  {plan.status === "completed" ? <IconSuccess /> : <IconBackend />}
                </span>
                <span>
                  <strong>{plan.title}</strong>
                  <small>{plan.summary || t("previews.stepsCount", { count: plan.steps.length })}</small>
                </span>
                <em className={status.tone}>{status.label}</em>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title={t("previews.noPlans")} detail={t("previews.noPlansDetail")} />
        )}
      </div>
      <button className="pixel-full-history">{t("previews.newPlan")}</button>
    </aside>
  );
}

export function EmptyPreviewState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="pixel-empty-preview">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

// Plain function, not a component — uses i18n.t() directly, same pattern as
// voiceStateLabel() in src/lib/voiceState.ts.
export function planStatusLabel(status: Plan["status"]): { label: string; tone: "active" | "pending" } {
  switch (status) {
    case "approved":
    case "running":
      return { label: i18n.t("planStatus.active"), tone: "active" };
    case "completed":
      return { label: i18n.t("planStatus.completed"), tone: "active" };
    case "rejected":
    case "cancelled":
      return { label: i18n.t("planStatus.cancelled"), tone: "pending" };
    case "draft":
      return { label: i18n.t("planStatus.draft"), tone: "pending" };
    case "proposed":
    default:
      return { label: i18n.t("planStatus.pending"), tone: "pending" };
  }
}
