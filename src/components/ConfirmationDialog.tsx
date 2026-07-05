import { useEffect, useState } from "react";
import { Check, ShieldAlert, X } from "lucide-react";
import type { Confirmation, RiskLevel } from "../vite-env";
import { voiceStateLabel } from "../lib/voiceState";

type ConfirmationDialogProps = {
  confirmation: Confirmation | null;
  busy: boolean;
  onApprove: (confirmationId: string) => void;
  onReject: (confirmationId: string) => void;
  onCancel: (confirmationId: string) => void;
};

const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk — requires confirmation",
  critical: "Critical risk — requires confirmation",
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

  const payloadPreview = Object.keys(confirmation.payload || {}).length
    ? JSON.stringify(confirmation.payload, null, 2)
    : "—";

  return (
    <div className="confirmation-overlay" role="dialog" aria-modal="true" aria-label="Ricky proposes an action">
      <div className="confirmation-dialog">
        <header className="confirmation-header">
          <span className="confirmation-icon">
            <ShieldAlert size={18} />
          </span>
          <div className="confirmation-title-block">
            <strong>Ricky predlaže akciju</strong>
            <small>Waiting confirmation</small>
          </div>
          <button
            className="confirmation-close"
            onClick={() => confirmation && onCancel(confirmation.id)}
            disabled={!isPending || busy}
            aria-label="Dismiss confirmation"
            title="Dismiss"
          >
            <X size={14} />
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
          <div className="confirmation-row confirmation-row-payload">
            <span className="confirmation-label">Payload</span>
            <pre className="confirmation-payload">{payloadPreview}</pre>
          </div>
        </section>

        <footer className="confirmation-actions">
          <button
            className="confirmation-button confirmation-reject"
            onClick={() => confirmation && onReject(confirmation.id)}
            disabled={!isPending || busy}
          >
            <X size={14} />
            <span>Otkaži</span>
          </button>
          <button
            className="confirmation-button confirmation-approve"
            onClick={() => confirmation && onApprove(confirmation.id)}
            disabled={!isPending || busy}
          >
            <Check size={14} />
            <span>Pokreni</span>
          </button>
        </footer>

        <p className="confirmation-hint">
          Voice command "da"/"pokreni" or "ne"/"otkaži" must bind to this same confirmation_id —
          see voiceState: {voiceStateLabel("waiting_confirmation")}.
        </p>
      </div>
    </div>
  );
}
