/** Pixel dictation editor screen — verbatim move from App.tsx (R3). JSX unchanged. */
import IconMic from "../../../assets/brending/icons/voice/icon-microphone.svg?react";
import IconChevronDown from "../../../assets/brending/icons/ui/icon-chevron-down.svg?react";
import IconSend from "../../../assets/brending/icons/voice/icon-send.svg?react";

export function DictationScreen({
  text,
  onChange,
  onCancel,
  onSend,
  onContinue,
}: {
  text: string;
  onChange: (value: string) => void;
  onCancel: () => void;
  onSend: () => void;
  onContinue: () => void;
}) {
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <section className="pixel-dictation">
      <header className="pixel-dictation-head">
        <div>
          <span className="pixel-dictation-badge">DIKTIRANJE</span>
          <span className="pixel-autosave">
            <span />
            auto-čuvanje uključeno
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
          <button className="pixel-secondary">
            Doradi <IconChevronDown />
          </button>
          <div className="pixel-dropdown-menu">
            <button>Formalizuj</button>
            <button>Skrati</button>
            <button>Provjeri pravopis</button>
            <button>Prevedi na engleski</button>
          </div>
        </div>
        <button className="pixel-secondary">...</button>
        <span className="pixel-action-spacer" />
        <button className="pixel-primary" onClick={onSend}>
          <IconSend /> Pošalji agentu
        </button>
      </footer>
    </section>
  );
}
