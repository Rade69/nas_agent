/** StatusAnnouncer — ARIA live region for screen-reader accessibility (A1).
 *
 *  Always-on, never opt-in. Publishes voice/connection/status changes to
 *  assistive technology via role="status" (polite) and role="alert" (assertive).
 *  Visually hidden (sr-only) — no visual change for sighted users.
 *
 *  Mechanism: the live-region nodes are persistent (always in the DOM).
 *  We update their text content via React state. Screen readers announce
 *  text changes in an existing live region — NOT the initial content of a
 *  freshly-inserted node (that's why we avoid the key-remount trick).
 *
 *  Urgency is derived from the raw VoiceState enum + connectionState string,
 *  NOT from substring-matching on localized labels (which would break under
 *  non-Serbian locales).
 *
 *  Context: docs/ACCESSIBILITY_UNIVERSAL_LAYER_BRIEF_FOR_PI.md (A1)
 *  Review fix (2026-07-16): key-remount → state-based; localized-label
 *  substring-match → enum branching; ref-in-render → useEffect; hardcoded
 *  strings → i18n; .sr-only moved 12-pixel-board.css → 00-base.css.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { VoiceState } from "../lib/voiceState";
import { voiceStateLabel } from "../lib/voiceState";

export type AnnouncerState = {
  /** Raw voice state enum (NOT the localized label) — branching source. */
  voiceState: VoiceState;
  /** Status string from realtime.ts (already localized by the source). */
  status: string;
  /** Connection state: idle | connecting | connected | reconnecting | reconnect-failed. */
  connectionState: string;
};

/**
 * Determine urgency from the raw enum, not from localized text.
 * Assertive: errors, reconnect-failed, waiting for user decision.
 */
function isUrgent(voiceState: VoiceState, connectionState: string): boolean {
  return (
    voiceState === "error" ||
    voiceState === "waiting_confirmation" ||
    connectionState === "reconnect-failed"
  );
}

/**
 * Derive the announcement message from state + i18n.
 * Returns null when there is nothing meaningful to announce (idle/connected).
 * Priority: error > waiting_confirmation > status > voice label > connecting.
 */
export function deriveAnnouncement(
  voiceState: VoiceState,
  status: string,
  connectionState: string,
  t: (key: string) => string,
): string | null {
  // Assertive: reconnect failure (own i18n string)
  if (connectionState === "reconnect-failed") {
    return t("a11y.announcer.reconnectFailed");
  }
  // Assertive: voice error (own i18n string, plus the localized label)
  if (voiceState === "error") {
    return t("a11y.announcer.error");
  }
  // Assertive but not an error: waiting for confirmation (localized label)
  if (voiceState === "waiting_confirmation") {
    return voiceStateLabel(voiceState);
  }

  // Polite: status string (from realtime.ts — already localized by the source)
  if (status && status !== "Idle" && status !== "Spreman") {
    return status;
  }
  // Polite: non-idle voice state (localized via voiceStateLabel)
  if (voiceState !== "idle") {
    return voiceStateLabel(voiceState);
  }
  // Polite: connecting / reconnecting (own i18n string)
  if (connectionState === "connecting" || connectionState === "reconnecting") {
    return t("a11y.announcer.connecting");
  }

  return null;
}

/** Always-present, sr-only ARIA live region. Mount once in App.tsx. */
export function StatusAnnouncer({ voiceState, status, connectionState }: AnnouncerState) {
  const { t } = useTranslation();
  // Persistent message state — screen reader announces when this CHANGES,
  // not when the node is (re)created. Same value = no re-announce (dedup).
  const [politeMessage, setPoliteMessage] = useState("");
  const [assertiveMessage, setAssertiveMessage] = useState("");

  useEffect(() => {
    const message = deriveAnnouncement(voiceState, status, connectionState, t);
    if (message === null) return;
    if (isUrgent(voiceState, connectionState)) {
      // Only update on real change — React bails out on same value, so the
      // DOM text doesn't change and the screen reader stays silent (dedup).
      setAssertiveMessage((prev) => (prev === message ? prev : message));
    } else {
      setPoliteMessage((prev) => (prev === message ? prev : message));
    }
  }, [voiceState, status, connectionState, t]);

  return (
    <div className="sr-only" aria-live="off">
      {/* Polite: normal state transitions (listening, thinking, connected…) */}
      <div role="status" aria-live="polite" aria-atomic="true">
        {politeMessage}
      </div>
      {/* Assertive: errors, waiting for confirmation */}
      <div role="alert" aria-live="assertive" aria-atomic="true">
        {assertiveMessage}
      </div>
    </div>
  );
}
