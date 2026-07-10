import { useEffect, useState } from "react";
import type { VoiceState } from "../lib/voiceState";
import { voiceStateLabel } from "../lib/voiceState";
import { RickyOrb } from "./RickyOrb";

type CompanionOrbProps = {
  initialState?: VoiceState;
};

export function CompanionOrb({ initialState = "idle" }: CompanionOrbProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>(initialState);

  // FAZA 12: VoiceState arrives via IPC from the main process.
  useEffect(() => {
    const unsubscribe = window.ricky.onCompanionVoiceState?.((state: VoiceState) => {
      setVoiceState(state);
    });
    return () => {
      unsubscribe?.();
    };
  }, []);

  return (
    <div className="companion-root" aria-label={`Ricky companion — ${voiceStateLabel(voiceState)}`}>
      {/* The orb is the drag handle (-webkit-app-region: drag in CSS). A drag
          region can't receive left-clicks, so actions live on the Stop button
          (no-drag) and the right-click native menu (Menu.popup, not clipped by
          the small window like the old HTML menu was). */}
      <div
        className="companion-orb-button"
        onContextMenu={(event) => {
          event.preventDefault();
          window.ricky.companionMenu?.();
        }}
        title={`${voiceStateLabel(voiceState)} — povuci za pomjeranje, desni klik za meni`}
      >
        <RickyOrb voiceState={voiceState} size="floating" />
        <span className="companion-state-pill">{voiceStateLabel(voiceState)}</span>
      </div>

      {/* Always-visible Stop — the orb carries the "stop everything" control. */}
      <button
        type="button"
        className="companion-stop-button"
        onClick={() => window.ricky.companionStop?.()}
        title="Zaustavi sve — glas i sve radnje (isto kao Ctrl+Alt+K)"
        aria-label="Zaustavi sve"
      >
        <span className="companion-stop-glyph" aria-hidden="true">
          ■
        </span>
        Stop
      </button>
    </div>
  );
}
