/** Computer-mode mini window — verbatim move from App.tsx (R3). JSX unchanged.
 *  Localized via i18next (GUI Localization PR-3). */
import { useTranslation } from "react-i18next";
import rikiAvatar from "../../../assets/Riki-avatar.png";
import type { VoiceState } from "../../lib/realtime";

export function MiniComputerWindow({
  voiceState,
  onRestore,
}: {
  voiceState: VoiceState;
  onRestore: () => void;
}) {
  const { t } = useTranslation();
  const stateLabel = t("mini.on");
  const isTalking = voiceState === "speaking" || voiceState === "listening" || voiceState === "thinking" || voiceState === "transcribing";
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
