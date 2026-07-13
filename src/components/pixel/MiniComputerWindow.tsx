/** Computer-mode mini window — verbatim move from App.tsx (R3). JSX unchanged.
 *  Localized via i18next (GUI Localization PR-3).
 *  User-reported gap (2026-07-13): this window used to have no way to see or
 *  act on a pending confirmation at all — App.tsx's <ConfirmationDialog> only
 *  rendered in the main-window branch, so a computer_click/computer_type_text
 *  confirmation while in Computer Mode was invisible here. The only way to
 *  reach it was clicking "Vrati", which calls onRestore -> switchMode("display")
 *  and turns Computer Mode OFF as a side effect — by the time the user could
 *  see and approve the confirmation, the mode requirement it needed had
 *  already been disabled. Now this window renders a compact confirm/reject
 *  card itself when a confirmation is pending, so approving never requires
 *  leaving Computer Mode. */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import rikiAvatar from "../../../assets/Riki-avatar.png";
import type { VoiceState } from "../../lib/realtime";
import type { Confirmation } from "../../vite-env";

export function MiniComputerWindow({
  voiceState,
  onRestore,
  pendingConfirmation,
  confirmationBusy,
  onApproveConfirmation,
  onRejectConfirmation,
}: {
  voiceState: VoiceState;
  onRestore: () => void;
  pendingConfirmation: Confirmation | null;
  confirmationBusy: boolean;
  onApproveConfirmation: (confirmationId: string) => void;
  onRejectConfirmation: (confirmationId: string) => void;
}) {
  const { t } = useTranslation();
  // FAZA S-4/S30 (same rate-limit principle as ConfirmationDialog.tsx): the
  // approve button stays disabled for a short window after the card appears
  // so a stray click can't sail through the instant it renders.
  const [armed, setArmed] = useState(false);
  const isPendingConfirm = pendingConfirmation?.status === "pending";

  useEffect(() => {
    if (!isPendingConfirm) {
      setArmed(false);
      return;
    }
    setArmed(false);
    const timer = setTimeout(() => setArmed(true), 250);
    return () => clearTimeout(timer);
  }, [isPendingConfirm, pendingConfirmation?.id]);

  const stateLabel = t("mini.on");
  const isTalking = voiceState === "speaking" || voiceState === "listening" || voiceState === "thinking" || voiceState === "transcribing";

  if (pendingConfirmation && isPendingConfirm) {
    return (
      <main className="mini-computer-window mini-computer-window-confirm">
        <div className="mini-confirm-card">
          <span className="mini-confirm-label">{t("mini.confirmNeeded")}</span>
          <p className="mini-confirm-action">{pendingConfirmation.action_name}</p>
          <div className="mini-confirm-actions">
            <button
              className="mini-confirm-reject"
              onClick={() => onRejectConfirmation(pendingConfirmation.id)}
              disabled={confirmationBusy}
            >
              {t("mini.reject")}
            </button>
            <button
              className="mini-confirm-approve"
              onClick={() => onApproveConfirmation(pendingConfirmation.id)}
              disabled={confirmationBusy || !armed}
            >
              {t("mini.approve")}
            </button>
          </div>
        </div>
      </main>
    );
  }

  // Stop lives on the floating companion orb (auto-shown in Computer Mode), not
  // here — see docs/ORB_PRESENCE_SPEC.md. This window only offers "Vrati".
  return (
    <main className={`mini-computer-window ${isTalking ? "is-talking" : "is-idle"}`}>
      <button className="mini-avatar-restore" onClick={onRestore} title={t("mini.restoreTitle")}>
        {t("mini.restore")}
      </button>
      <div className="mini-avatar-stage" aria-label={t("mini.stageAria", { state: stateLabel })}>
        <img src={rikiAvatar} alt="Ricky avatar" draggable={false} />
      </div>
      <div className="mini-avatar-status">
        <span>{t("mini.computerMode")}</span>
        <strong>{stateLabel}</strong>
      </div>
    </main>
  );
}
