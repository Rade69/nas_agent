/** Full confirmation approval/rejection modal (FAZA 9).
 *  Renders payload fields with localized labels, risk badge, summary,
 *  plan reference, and approve/reject/cancel buttons. Rate-limited
 *  (250ms arm delay) to prevent accidental double-clicks (S-4/S30).
 *  Localized via i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import type { Confirmation, RiskLevel } from "../vite-env";
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
  onApprove: (confirmationId: string) => void;
  onReject: (confirmationId: string) => void;
  onCancel: (confirmationId: string) => void;
};

function riskClassName(risk: RiskLevel): string {
  return `confirmation-risk-pill confirmation-risk-${risk}`;
}

export function ConfirmationDialog({
  confirmation,
  busy,
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

  useEffect(() => {
    if (confirmation && confirmation.status === "pending") {
      setVisible(true);
      setArmed(false);
      const timer = setTimeout(() => setArmed(true), 250);
      return () => clearTimeout(timer);
    }
    setVisible(false);
    return undefined;
  }, [confirmation]);

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
    <div className="confirmation-overlay" role="dialog" aria-modal="true" aria-label={t("confirmation.dialogAria")}>
      <div className="confirmation-dialog">
        <header className="confirmation-header">
          <span className="confirmation-icon">
            <IconWarning className="confirmation-icon-svg" />
          </span>
          <div className="confirmation-title-block">
            <strong>{t("previews.confirmTitle")}</strong>
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
          {isEmailDraftConfirmation ? (
            <div className="confirmation-row confirmation-row-notice">
              <span className="confirmation-value confirmation-notice">{t("confirmation.emailNeverSent")}</span>
            </div>
          ) : null}
          <div className="confirmation-row">
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
