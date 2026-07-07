import { useEffect, useRef, useState } from "react";
import type { VoiceState } from "../lib/voiceState";
import { voiceStateLabel } from "../lib/voiceState";
import orbMini from "../../assets/brending/orb/ricky-orb-mini.png";

type CompanionOrbProps = {
  initialState?: VoiceState;
};

export function CompanionOrb({ initialState = "idle" }: CompanionOrbProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>(initialState);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // FAZA 12: VoiceState arrives via IPC from the main process.
  useEffect(() => {
    const unsubscribe = window.ricky.onCompanionVoiceState?.((state: VoiceState) => {
      setVoiceState(state);
    });
    return () => {
      unsubscribe?.();
    };
  }, []);

  // Close context menu on outside click.
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  return (
    <div className="companion-root" aria-label={`Ricky companion — ${voiceStateLabel(voiceState)}`}>
      <button
        className="companion-orb-button"
        onClick={() => {
          window.ricky.companionClick?.();
        }}
        onContextMenu={(event) => {
          event.preventDefault();
          setMenuOpen((value) => !value);
        }}
        onDoubleClick={() => {
          window.ricky.companionOpenMain?.();
        }}
        title={`${voiceStateLabel(voiceState)} — klik za akciju, dupli klik za glavni prozor, desni klik za meni`}
      >
        <img
          src={orbMini}
          alt="Ricky companion"
          className="companion-orb-img"
          draggable={false}
        />
        <span className="companion-state-pill">{voiceStateLabel(voiceState)}</span>
      </button>

      {menuOpen ? (
        <div className="companion-menu" ref={menuRef} role="menu">
          <button className="companion-menu-item" onClick={() => { setMenuOpen(false); window.ricky.companionOpenMain?.(); }}>
            Open Ricky
          </button>
          <button className="companion-menu-item" onClick={() => { setMenuOpen(false); window.ricky.companionToggleVoice?.(); }}>
            Toggle voice
          </button>
          <button className="companion-menu-item" onClick={() => { setMenuOpen(false); window.ricky.companionToggleLock?.(true); }}>
            Lock position
          </button>
          <hr className="companion-menu-separator" />
          <button className="companion-menu-item companion-menu-danger" onClick={() => { setMenuOpen(false); window.ricky.quitApp?.(); }}>
            Quit
          </button>
        </div>
      ) : null}
    </div>
  );
}