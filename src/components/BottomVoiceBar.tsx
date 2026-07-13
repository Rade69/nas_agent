/** Deprecated voice control bar from the pre-pixel-redesign UI.
 *  Replaced by the pixel TopBar / Sidebar / RickyOrb components.
 *  Kept for reference; not mounted in the current App.tsx shell. */
import { BrainCircuit, History, Keyboard, Mic, MicOff, MonitorCog, PanelRight, Send } from "lucide-react";
import { voiceStateLabel, type VoiceState } from "../lib/voiceState";
import type { RickyConnectionState } from "../lib/realtime";

type BottomVoiceBarProps = {
  voiceState: VoiceState;
  connectionState: RickyConnectionState;
  isConnected: boolean;
  isConnecting: boolean;
  showTypeInput: boolean;
  showLog: boolean;
  artifactVisible: boolean;
  textPrompt: string;
  onConnectToggle: () => void;
  onToggleTextInput: () => void;
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onSwitchDisplayMode: () => void;
  onSwitchComputerMode: () => void;
  onToggleArtifacts: () => void;
  onToggleActivity: () => void;
};

export function BottomVoiceBar({
  voiceState,
  connectionState,
  isConnected,
  isConnecting,
  showTypeInput,
  showLog,
  artifactVisible,
  textPrompt,
  onConnectToggle,
  onToggleTextInput,
  onTextPromptChange,
  onSendTextPrompt,
  onSwitchDisplayMode,
  onSwitchComputerMode,
  onToggleArtifacts,
  onToggleActivity,
}: BottomVoiceBarProps) {
  return (
    <footer className="bottom-console voice-console">
      <div className="bottom-voice-status">
        <span className={`voice-state-dot voice-state-dot-${voiceState}`} />
        <span>{voiceStateLabel(voiceState)}</span>
        <small>{connectionState}</small>
      </div>

      {showTypeInput ? (
        <section className="prompt-box">
          <input
            value={textPrompt}
            onChange={(event) => onTextPromptChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSendTextPrompt();
            }}
            autoFocus
            placeholder="Type to Ricky..."
          />
          <button onClick={onSendTextPrompt} aria-label="Send typed prompt" title="Send typed prompt">
            <Send size={15} />
          </button>
        </section>
      ) : null}

      <section className="control-strip voice-control-strip">
        <button
          className={isConnected ? "simple-button active" : "simple-button"}
          onClick={onConnectToggle}
          disabled={isConnecting}
          aria-label={isConnected ? "Disconnect voice" : "Connect voice"}
          title={isConnected ? "Disconnect voice" : "Connect voice"}
        >
          {isConnected ? <MicOff size={16} /> : <Mic size={16} />}
        </button>
        <button
          className={showTypeInput ? "simple-button active" : "simple-button"}
          onClick={onToggleTextInput}
          aria-label="Type to Ricky"
          title="Type to Ricky"
        >
          <Keyboard size={16} />
        </button>
        <button className="simple-button active" onClick={onSwitchDisplayMode} aria-label="Display mode" title="Display mode">
          <PanelRight size={16} />
        </button>
        <button className="simple-button danger" onClick={onSwitchComputerMode} aria-label="Computer use mode" title="Computer use mode">
          <MonitorCog size={16} />
        </button>
        <button
          className={artifactVisible ? "simple-button active" : "simple-button"}
          onClick={onToggleArtifacts}
          aria-label="Toggle artifacts"
          title="Toggle artifacts"
        >
          <BrainCircuit size={16} />
        </button>
        <button
          className={showLog ? "simple-button active" : "simple-button"}
          onClick={onToggleActivity}
          aria-label="Toggle activity"
          title="Toggle activity"
        >
          <History size={16} />
        </button>
      </section>
    </footer>
  );
}