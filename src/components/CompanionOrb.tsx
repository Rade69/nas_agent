import { useEffect, useRef, useState } from "react";
import type { VoiceState } from "../lib/voiceState";
import { voiceStateLabel } from "../lib/voiceState";

type RickyMood = "idle" | "happy" | "thinking" | "talking" | "error" | "sleeping";

type MouthShape = {
  open: number;
  width: number;
  round: number;
  teeth: number;
};

type CompanionOrbProps = {
  initialState?: VoiceState;
};

const VOICE_STATE_TO_MOOD: Record<VoiceState, RickyMood> = {
  idle: "idle",
  listening: "talking",
  transcribing: "thinking",
  thinking: "thinking",
  speaking: "talking",
  waiting_confirmation: "thinking",
  interrupted: "error",
  muted: "sleeping",
  error: "error",
};

const DEFAULT_MOUTH: MouthShape = { open: 0.05, width: 0.18, round: 0, teeth: 0 };

export function CompanionOrb({ initialState = "idle" }: CompanionOrbProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>(initialState);
  const [mood, setMood] = useState<RickyMood>("idle");
  const [mouthShape, setMouthShape] = useState<MouthShape>(DEFAULT_MOUTH);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // FAZA 12: VoiceState arrives via IPC from the main process, which forwards
  // voice.state_changed events from the main window's Realtime client. The orb
  // itself does NOT run a Realtime client — there is exactly one audio pipeline
  // (src/lib/realtime.ts in the main window) per ARCHITECTURE_VOICE_FIRST_REVISED.
  useEffect(() => {
    const unsubscribe = window.ricky.onCompanionVoiceState?.((state: VoiceState) => {
      setVoiceState(state);
      setMood(VOICE_STATE_TO_MOOD[state] ?? "idle");
    });
    return () => {
      unsubscribe?.();
    };
  }, []);

  // Driven by mouth animation when speaking/listening: a gentle idle pulse is
  // enough for the orb (full mouth animation stays in the main window's RickyFace).
  useEffect(() => {
    let raf = 0;
    let cancelled = false;
    const animate = () => {
      if (cancelled) return;
      const t = Date.now() / 1000;
      if (voiceState === "speaking") {
        setMouthShape({
          open: 0.3 + Math.sin(t * 14) * 0.25,
          width: 0.22,
          round: 0.2,
          teeth: 0.3,
        });
      } else if (voiceState === "listening") {
        setMouthShape({
          open: 0.12 + Math.sin(t * 4) * 0.08,
          width: 0.2,
          round: 0.1,
          teeth: 0,
        });
      } else {
        setMouthShape(DEFAULT_MOUTH);
      }
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [voiceState]);

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

  const stateClass = `companion-state-${voiceState}`;

  return (
    <div className={`companion-root ${stateClass}`} aria-label={`Ricky companion — ${voiceStateLabel(voiceState)}`}>
      <button
        className="companion-orb-button"
        onClick={() => {
          // Single click: bring main window to front / start listening.
          window.ricky.companionClick?.();
        }}
        onContextMenu={(event) => {
          event.preventDefault();
          setMenuOpen((value) => !value);
        }}
        onDoubleClick={() => {
          // Double click: open main window.
          window.ricky.companionOpenMain?.();
        }}
        title={`${voiceStateLabel(voiceState)} — click to act, double-click for main window, right-click for menu`}
      >
        <CompanionFace mood={mood} mouthShape={mouthShape} voiceState={voiceState} />
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

function CompanionFace({
  mood,
  mouthShape,
  voiceState,
}: {
  mood: RickyMood;
  mouthShape: MouthShape;
  voiceState: VoiceState;
}) {
  const styleVars = {
    "--mouth-open": mouthShape.open.toFixed(3),
    "--mouth-width": mouthShape.width.toFixed(3),
    "--mouth-round": mouthShape.round.toFixed(3),
    "--mouth-teeth": mouthShape.teeth.toFixed(3),
  } as React.CSSProperties;

  return (
    <div className={`companion-face companion-face-${mood} companion-state-ring-${voiceState}`} style={styleVars}>
      <div className="companion-glow" />
      <div className="companion-eye-row">
        <div className="companion-eye">
          <span />
        </div>
        <div className="companion-eye">
          <span />
        </div>
      </div>
      <div className="companion-mouth-wrap">
        <div className="companion-mouth">
          <div className="companion-mouth-teeth" />
          <div className="companion-mouth-line" />
        </div>
      </div>
    </div>
  );
}
