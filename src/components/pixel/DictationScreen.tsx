/** Pixel dictation editor screen — verbatim move from App.tsx (R3), later
 *  extended with the "Doradi" rewrite menu and "..." overflow menu.
 *  Now fully localized via i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useTranslation } from "react-i18next";
import IconMic from "../../../assets/brending/icons/voice/icon-microphone.svg?react";
import IconChevronDown from "../../../assets/brending/icons/ui/icon-chevron-down.svg?react";
import IconSend from "../../../assets/brending/icons/voice/icon-send.svg?react";
import IconMore from "../../../assets/brending/icons/ui/icon-more.svg?react";
import type { TextRewriteOperation } from "../../vite-env";

export function DictationScreen({
  text,
  onChange,
  onCancel,
  onSend,
  onContinue,
  onRewrite,
  onCopy,
  onClear,
  onUndo,
  onDownload,
  busy,
  canUndo,
}: {
  text: string;
  onChange: (value: string) => void;
  onCancel: () => void;
  onSend: () => void;
  onContinue: () => void;
  onRewrite: (operation: TextRewriteOperation) => void;
  onCopy: () => void;
  onClear: () => void;
  onUndo: () => void;
  onDownload: () => void;
  busy: boolean;
  canUndo: boolean;
}) {
  const { t } = useTranslation();
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const hasText = text.trim().length > 0;

  return (
    <section className="pixel-dictation">
      <header className="pixel-dictation-head">
        <div>
          <span className="pixel-dictation-badge">{t("dictation.badge")}</span>
          <span className="pixel-autosave">
            <span />
            {busy ? t("dictation.processing") : t("dictation.autoSave")}
          </span>
        </div>
        <button onClick={onCancel}>
          {t("dictation.cancel")}
        </button>
      </header>
      <div className="pixel-editor-wrap">
        <textarea
          value={text}
          onChange={(event) => onChange(event.target.value)}
          placeholder={t("dictation.placeholder")}
        />
        <span className="pixel-word-count">{t("dictation.wordCount", { count: wordCount })}</span>
      </div>
      <footer className="pixel-dictation-actions">
        <button className="pixel-secondary" onClick={onContinue} title={t("dictation.continueTitle")}>
          <IconMic /> {t("dictation.continueDictating")}
        </button>
        <div className="pixel-dropdown">
          <button className="pixel-secondary" disabled={busy || !hasText}>
            {t("dictation.refine")} <IconChevronDown />
          </button>
          <div className="pixel-dropdown-menu">
            <button onClick={() => onRewrite("formalize")}>{t("dictation.formalize")}</button>
            <button onClick={() => onRewrite("shorten")}>{t("dictation.shorten")}</button>
            <button onClick={() => onRewrite("proofread")}>{t("dictation.proofread")}</button>
            <button onClick={() => onRewrite("translate_en")}>{t("dictation.translateEn")}</button>
          </div>
        </div>
        <div className="pixel-dropdown">
          <button className="pixel-secondary" title={t("dictation.moreTitle")}>
            <IconMore /> {t("dictation.more")}
          </button>
          <div className="pixel-dropdown-menu">
            <button onClick={onCopy} disabled={!hasText}>{t("dictation.copy")}</button>
            <button onClick={onClear} disabled={!hasText}>{t("dictation.clear")}</button>
            <button onClick={onUndo} disabled={!canUndo}>{t("dictation.undo")}</button>
            <button onClick={onDownload} disabled={!hasText}>{t("dictation.download")}</button>
          </div>
        </div>
        <span className="pixel-action-spacer" />
        <button className="pixel-primary" onClick={onSend}>
          <IconSend /> {t("dictation.send")}
        </button>
      </footer>
    </section>
  );
}
