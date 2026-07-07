import { useEffect, useState } from "react";
import type { Confirmation, RiskLevel } from "../vite-env";
import IconWarning from "../../assets/brending/icons/safety/icon-warning.svg?react";
import IconConfirm from "../../assets/brending/icons/safety/icon-confirm.svg?react";
import IconCancel from "../../assets/brending/icons/safety/icon-cancel.svg?react";

// Common payload keys across tool arguments, mapped to the mockup's field
// labels (assets/GUI-SETS/GUI-SET-3.png) so e.g. an email-send confirmation
// shows "Prima" / "Predmet" instead of a raw JSON dump. Falls back to JSON
// for payloads that don't match any of these (e.g. computer_click's x/y).
const PAYLOAD_FIELD_LABELS: Record<string, string> = {
  to: "Prima",
  recipient: "Prima",
  email: "Prima",
  subject: "Predmet",
  title: "Predmet",
  text: "Sadržaj",
  body: "Sadržaj",
  appName: "Aplikacija",
};

type ConfirmationDialogProps = {
  confirmation: Confirmation | null;
  busy: boolean;
  onApprove: (confirmationId: string) => void;
  onReject: (confirmationId: string) => void;
  onCancel: (confirmationId: string) => void;
};

const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Nizak rizik",
  medium: "Srednji rizik",
  high: "Visok rizik — potrebna potvrda",
  critical: "Kritičan rizik — potrebna potvrda",
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
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (confirmation && confirmation.status === "pending") {
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [confirmation]);

  if (!visible || !confirmation) return null;
  const isPending = confirmation.status === "pending";

  const payload = confirmation.payload || {};
  const recognizedEntries = Object.entries(payload).filter(([key]) => key in PAYLOAD_FIELD_LABELS);
  const unrecognizedPayload = Object.fromEntries(
    Object.entries(payload).filter(([key]) => !(key in PAYLOAD_FIELD_LABELS)),
  );
  const hasUnrecognized = Object.keys(unrecognizedPayload).length > 0;

  // Dynamic confirm label matching the mockup's "Pošalji email" pattern —
  // falls back to a generic verb for actions this heuristic doesn't cover.
  const confirmLabel = /email|mail/i.test(confirmation.action_name)
    ? "Pošalji email"
    : "Pokreni";

  return (
    <div className="confirmation-overlay" role="dialog" aria-modal="true" aria-label="Ricky predlaže akciju">
      <div className="confirmation-dialog">
        <header className="confirmation-header">
          <span className="confirmation-icon">
            <IconWarning className="confirmation-icon-svg" />
          </span>
          <div className="confirmation-title-block">
            <strong>Ricky želi izvršiti ovu akciju</strong>
            <small>Pažljivo provjeri detalje prije potvrde.</small>
          </div>
          <button
            className="confirmation-close"
            onClick={() => confirmation && onCancel(confirmation.id)}
            disabled={!isPending || busy}
            aria-label="Odbaci potvrdu"
            title="Odbaci"
          >
            <IconCancel className="confirmation-icon-svg" />
          </button>
        </header>

        <section className="confirmation-body">
          <div className="confirmation-row">
            <span className="confirmation-label">Akcija</span>
            <span className="confirmation-value">{confirmation.action_name}</span>
          </div>
          {confirmation.summary ? (
            <div className="confirmation-row">
              <span className="confirmation-label">Sažetak</span>
              <span className="confirmation-value">{confirmation.summary}</span>
            </div>
          ) : null}
          {recognizedEntries.map(([key, value]) => (
            <div className="confirmation-row" key={key}>
              <span className="confirmation-label">{PAYLOAD_FIELD_LABELS[key]}</span>
              <span className="confirmation-value">{String(value)}</span>
            </div>
          ))}
          <div className="confirmation-row">
            <span className="confirmation-label">Rizik</span>
            <span className={riskClassName(confirmation.risk_level)}>
              {RISK_LABEL[confirmation.risk_level]}
            </span>
          </div>
          {confirmation.plan_id ? (
            <div className="confirmation-row">
              <span className="confirmation-label">Plan</span>
              <span className="confirmation-value confirmation-mono">{confirmation.plan_id}</span>
            </div>
          ) : null}
          {hasUnrecognized ? (
            <div className="confirmation-row confirmation-row-payload">
              <span className="confirmation-label">Detalji</span>
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
            <span>Otkaži</span>
          </button>
          <button
            className="confirmation-button confirmation-approve"
            onClick={() => confirmation && onApprove(confirmation.id)}
            disabled={!isPending || busy}
          >
            <IconConfirm className="confirmation-icon-svg" />
            <span>{confirmLabel}</span>
          </button>
        </footer>
      </div>
    </div>
  );
}