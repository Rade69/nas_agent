/** Full confirmation approval/rejection modal (FAZA 9).
 *  Renders payload fields with localized labels, risk badge, summary,
 *  plan reference, and approve/reject/cancel buttons. Rate-limited
 *  (250ms arm delay) to prevent accidental double-clicks (S-4/S30).
 *  Localized via i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import type { Confirmation, Plan, RiskLevel } from "../vite-env";
import IconWarning from "../../assets/brending/icons/safety/icon-warning.svg?react";
import IconConfirm from "../../assets/brending/icons/safety/icon-confirm.svg?react";
import IconCancel from "../../assets/brending/icons/safety/icon-cancel.svg?react";

// i18n key-evi za payload polja — plain funkcija, koristi i18n.t() direktno
// (isti pattern kao voiceStateLabel i planStatusLabel). PAYLOAD_FIELD_KEYS
// je jedini izvor istine za "koji payload ključevi imaju labelu" — koristi
// se i ovdje i za recognizedEntries/unrecognizedPayload filtere ispod.
const PAYLOAD_FIELD_KEYS = ["to", "recipient", "email", "subject", "title", "text", "body", "appName"];

function fieldLabel(key: string): string {
  const map: Record<string, string> = {
    to: "confirmation.field.to",
    recipient: "confirmation.field.to",
    email: "confirmation.field.to",
    subject: "confirmation.field.subject",
    title: "confirmation.field.subject",
    text: "confirmation.field.content",
    body: "confirmation.field.content",
    appName: "confirmation.field.app",
  };
  return i18n.t(map[key] || key);
}

// Risk label — plain funkcija, direktan i18n.t(). NE skraćivati/mijenjati
// značenje: ovo su bezbjednosno značajne poruke (S-2/permission_engine).
// Context: docs/PI_TASK_GUI_LOCALIZATION_PR2_BRIEF.md
function riskLabel(risk: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    low: "confirmation.risk.low",
    medium: "confirmation.risk.medium",
    high: "confirmation.risk.high",
    critical: "confirmation.risk.critical",
  };
  return i18n.t(map[risk]);
}

type ConfirmationDialogProps = {
  confirmation: Confirmation | null;
  busy: boolean;
  plans: Plan[];
  onApprove: (confirmationId: string) => void;
  onReject: (confirmationId: string) => void;
  onCancel: (confirmationId: string) => void;
};

function riskClassName(risk: RiskLevel): string {
  return `confirmation-risk-pill confirmation-risk-${risk}`;
}

/** A2: Testable focus-trap + Escape decision logic.
 *  Returns what the keydown handler should do, without touching the DOM.
 *  - Escape → reject/cancel (safe, NEVER approve)
 *  - Shift+Tab on first focusable (or container) → wrap to last
 *  - Tab on last focusable → wrap to first
 */
export type DialogKeyDownAction =
  | { type: "escape" }
  | { type: "wrap-focus"; target: "first" | "last" }
  | { type: "default" };

export function resolveDialogKeyDown(
  key: string,
  shiftKey: boolean,
  isPending: boolean,
  busy: boolean,
  focusableCount: number,
  activeElementIndex: number, // -1 = container itself
): DialogKeyDownAction {
  // Escape → reject/cancel (safe action). NEVER approve.
  if (key === "Escape") {
    return isPending && !busy ? { type: "escape" } : { type: "default" };
  }
  if (key !== "Tab" || focusableCount === 0) return { type: "default" };
  if (shiftKey) {
    // Shift+Tab: wrap from first (or container) → last
    if (activeElementIndex === 0 || activeElementIndex === -1) {
      return { type: "wrap-focus", target: "last" };
    }
  } else {
    // Tab: wrap from last → first
    if (activeElementIndex === focusableCount - 1) {
      return { type: "wrap-focus", target: "first" };
    }
  }
  return { type: "default" };
}

export function ConfirmationDialog({
  confirmation,
  busy,
  plans,
  onApprove,
  onReject,
  onCancel,
}: ConfirmationDialogProps) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  // FAZA S-4 (S30): rate-limit the confirm action. The approve button stays
  // disabled for a short window after the dialog appears so a stray
  // double-click, macro, or programmatic click can't sail through a high-risk
  // confirmation the instant it renders.
  const [armed, setArmed] = useState(false);

  // A2: focus management — save the previously-focused element so we can
  // restore it when the dialog closes. The dialog container itself receives
  // focus on open (NEVER the Approve button — section 8: approval must stay
  // a deliberate action).
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (confirmation && confirmation.status === "pending") {
      setVisible(true);
      setArmed(false);
      // A2: save the element that had focus before the dialog opened.
      if (document.activeElement instanceof HTMLElement) {
        previousFocusRef.current = document.activeElement;
      }
      const timer = setTimeout(() => setArmed(true), 250);
      return () => clearTimeout(timer);
    }
    // A2: dialog closing — restore focus to the element that opened it.
    setVisible(false);
    const prev = previousFocusRef.current;
    if (prev && typeof prev.focus === "function") {
      // Defer so the dialog is fully unmounted first.
      requestAnimationFrame(() => prev.focus());
    }
    previousFocusRef.current = null;
    return undefined;
  }, [confirmation]);

  // A2: focus the dialog container when it becomes visible. We focus the
  // CONTAINER (tabIndex={-1}), never a button — so Enter does nothing on
  // a freshly-opened dialog and approval stays deliberate (section 8).
  // With aria-labelledby/aria-describedby, the screen reader reads the
  // dialog content when the container receives focus.
  useEffect(() => {
    if (visible && dialogRef.current) {
      // requestAnimationFrame ensures the element is in the DOM.
      requestAnimationFrame(() => dialogRef.current?.focus());
    }
  }, [visible]);

  // A2: Escape = reject/cancel (safe, non-destructive — NEVER approve).
  // Focus trap: Tab/Shift+Tab wraps within the dialog so focus can't
  // escape into the background while it's open. Decision logic lives in
  // resolveDialogKeyDown() (pure function, tested).
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
    const activeIndex = focusable.findIndex((el) => el === document.activeElement);
    // -1 = dialog container itself has focus (activeElement not in focusable list)
    const action = resolveDialogKeyDown(
      e.key, e.shiftKey, isPending, busy, focusable.length, activeIndex === -1 ? -1 : activeIndex,
    );
    switch (action.type) {
      case "escape":
        e.preventDefault();
        if (confirmation) onCancel(confirmation.id);
        break;
      case "wrap-focus": {
        e.preventDefault();
        const target = action.target === "first" ? focusable[0] : focusable[focusable.length - 1];
        target?.focus();
        break;
      }
      case "default":
      default:
        break;
    }
  };

  if (!visible || !confirmation) return null;
  const isPending = confirmation.status === "pending";

  const payload = confirmation.payload || {};
  const recognizedEntries = Object.entries(payload).filter(([key]) => PAYLOAD_FIELD_KEYS.includes(key));
  const unrecognizedPayload = Object.fromEntries(
    Object.entries(payload).filter(([key]) => !PAYLOAD_FIELD_KEYS.includes(key)),
  );
  const hasUnrecognized = Object.keys(unrecognizedPayload).length > 0;

  // email_prepare_draft (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md poglavlje 5,
  // review 4.5): the old /email|mail/i substring check on action_name would
  // have matched this exact tool name and shown "Pošalji email" (Send Email)
  // for a tool that never sends — security-relevant label, so it must be an
  // exact tool_name check, never a fuzzy heuristic. No tool this session
  // matched the old pattern anyway (verified before removing it).
  const isEmailDraftConfirmation = confirmation.tool_name === "email_prepare_draft";
  const confirmLabel = isEmailDraftConfirmation ? t("confirmation.prepareDraft") : t("confirmation.run");

  return (
    <div
      className="confirmation-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirmation-dialog-title"
      aria-describedby="confirmation-dialog-desc"
      ref={dialogRef}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      <div className="confirmation-dialog">
        <header className="confirmation-header">
          <span className="confirmation-icon">
            <IconWarning className="confirmation-icon-svg" />
          </span>
          <div className="confirmation-title-block">
            <strong id="confirmation-dialog-title">{t("previews.confirmTitle")}</strong>
            <small>{t("previews.confirmDefaultSummary")}</small>
          </div>
          <button
            className="confirmation-close"
            onClick={() => confirmation && onCancel(confirmation.id)}
            disabled={!isPending || busy}
            aria-label={t("confirmation.discardAria")}
            title={t("confirmation.discard")}
          >
            <IconCancel className="confirmation-icon-svg" />
          </button>
        </header>

        <section className="confirmation-body">
          {/* P3: show plan context if this confirmation belongs to a plan */}
          {confirmation.plan_id ? (() => {
            const linkedPlan = plans.find((p) => p.id === confirmation.plan_id);
            if (!linkedPlan) return null;
            const activeStep = linkedPlan.steps.find((s) => s.status === "in_progress" || s.status === "pending");
            return (
              <div className="confirmation-row confirmation-row-plan">
                <span className="confirmation-label">{t("plans.planLabel")}</span>
                <span className="confirmation-value">{linkedPlan.title}</span>
                {activeStep ? (
                  <span className="confirmation-value confirmation-step-ref">
                    {t("plans.stepLabel")} {activeStep.step_index + 1}: {activeStep.title}
                  </span>
                ) : null}
              </div>
            );
          })() : null}
          {isEmailDraftConfirmation ? (
            <div className="confirmation-row confirmation-row-notice">
              <span className="confirmation-value confirmation-notice">{t("confirmation.emailNeverSent")}</span>
            </div>
          ) : null}
          <div className="confirmation-row" id="confirmation-dialog-desc">
            <span className="confirmation-label">{t("previews.actionLabel")}</span>
            <span className="confirmation-value">{confirmation.action_name}</span>
          </div>
          {confirmation.summary ? (
            <div className="confirmation-row">
              <span className="confirmation-label">{t("confirmation.summary")}</span>
              <span className="confirmation-value">{confirmation.summary}</span>
            </div>
          ) : null}
          {recognizedEntries.map(([key, value]) => (
            <div className="confirmation-row" key={key}>
              <span className="confirmation-label">{fieldLabel(key)}</span>
              <span className="confirmation-value">{String(value)}</span>
            </div>
          ))}
          <div className="confirmation-row">
            <span className="confirmation-label">{t("previews.riskLabel")}</span>
            <span className={riskClassName(confirmation.risk_level)}>
              {riskLabel(confirmation.risk_level)}
            </span>
          </div>
          {confirmation.plan_id ? (
            <div className="confirmation-row">
              <span className="confirmation-label">{t("confirmation.plan")}</span>
              <span className="confirmation-value confirmation-mono">{confirmation.plan_id}</span>
            </div>
          ) : null}
          {hasUnrecognized ? (
            <div className="confirmation-row confirmation-row-payload">
              <span className="confirmation-label">{t("confirmation.details")}</span>
              <pre className="confirmation-payload">{JSON.stringify(unrecognizedPayload, null, 2)}</pre>
            </div>
          ) : null}
        </section>

        <footer className="confirmation-actions">
          <button
            className="confirmation-button confirmation-reject"
            onClick={() => confirmation && onReject(confirmation.id)}
            disabled={!isPending || busy}
          >
            <IconCancel className="confirmation-icon-svg" />
            <span>{t("confirmation.cancel")}</span>
          </button>
          <button
            className="confirmation-button confirmation-approve"
            onClick={() => confirmation && onApprove(confirmation.id)}
            disabled={!isPending || busy || !armed}
            title={!armed ? t("confirmation.wait") : undefined}
          >
            <IconConfirm className="confirmation-icon-svg" />
            <span>{confirmLabel}</span>
          </button>
        </footer>
      </div>
    </div>
  );
}
