/** Pixel dictation editor screen — verbatim move from App.tsx (R3), later
 *  extended with the "Doradi" rewrite menu and "..." overflow menu.
 *  Context: agent_reports/2026-07-11_dictation-rewrite-menu.md */
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
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const hasText = text.trim().length > 0;

  return (
    <section className="pixel-dictation">
      <header className="pixel-dictation-head">
        <div>
          <span className="pixel-dictation-badge">DIKTIRANJE</span>
          <span className="pixel-autosave">
            <span />
            {busy ? "obrađujem..." : "auto-čuvanje uključeno"}
          </span>
        </div>
        <button onClick={onCancel}>
          Otkaži diktiranje
        </button>
      </header>
      <div className="pixel-editor-wrap">
        <textarea
          value={text}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Diktirani tekst će se pojaviti ovdje..."
        />
        <span className="pixel-word-count">{wordCount} riječi</span>
      </div>
      <footer className="pixel-dictation-actions">
        <button className="pixel-secondary" onClick={onContinue} title="Ponovo poveži glas ako je prekinut i nastavi diktiranje">
          <IconMic /> Nastavi diktiranje
        </button>
        <div className="pixel-dropdown">
          <button className="pixel-secondary" disabled={busy || !hasText}>
            Doradi <IconChevronDown />
          </button>
          <div className="pixel-dropdown-menu">
            <button onClick={() => onRewrite("formalize")}>Formalizuj</button>
            <button onClick={() => onRewrite("shorten")}>Skrati</button>
            <button onClick={() => onRewrite("proofread")}>Provjeri pravopis</button>
            <button onClick={() => onRewrite("translate_en")}>Prevedi na engleski</button>
          </div>
        </div>
        <div className="pixel-dropdown">
          <button className="pixel-secondary" title="Više opcija">
            <IconMore /> Više
          </button>
          <div className="pixel-dropdown-menu">
            <button onClick={onCopy} disabled={!hasText}>Kopiraj tekst</button>
            <button onClick={onClear} disabled={!hasText}>Obriši sve</button>
            <button onClick={onUndo} disabled={!canUndo}>Undo</button>
            <button onClick={onDownload} disabled={!hasText}>Preuzmi kao .txt</button>
          </div>
        </div>
        <span className="pixel-action-spacer" />
        <button className="pixel-primary" onClick={onSend}>
          <IconSend /> Pošalji agentu
        </button>
      </footer>
    </section>
  );
}
