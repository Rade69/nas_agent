/** Companion orb overlay renderer — mounts when the Electron companion
 *  BrowserWindow loads ?view=companion. Displays RickyOrb with VoiceState
 *  reactivity and Stop control. Localized via i18next (GUI Localization PR-3);
 *  the native right-click/tray context menus are a separate main-process
 *  concern, localized independently in electron/core/companionWindow.cjs.
 *  Context: agent_reports/2026-07-05_faza12-companion-orb.md */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { VoiceState } from "../lib/voiceState";
import { voiceStateLabel } from "../lib/voiceState";
import { RickyOrb } from "./RickyOrb";

type CompanionOrbProps = {
  initialState?: VoiceState;
};

export function CompanionOrb({ initialState = "idle" }: CompanionOrbProps) {
  const { t } = useTranslation();
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
    <div className="companion-root" aria-label={t("companion.ariaLabel", { state: voiceStateLabel(voiceState) })}>
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
        title={t("companion.orbTitle", { state: voiceStateLabel(voiceState) })}
      >
        <RickyOrb voiceState={voiceState} size="floating" />
        <span className="companion-state-pill">{voiceStateLabel(voiceState)}</span>
      </div>

      {/* Always-visible Stop — the orb carries the "stop everything" control. */}
      <button
        type="button"
        className="companion-stop-button"
        onClick={() => window.ricky.companionStop?.()}
        title={t("companion.stopTitle")}
        aria-label={t("companion.stopAria")}
      >
        <span className="companion-stop-glyph" aria-hidden="true">
          ■
        </span>
        {t("companion.stop")}
      </button>
    </div>
  );
}
