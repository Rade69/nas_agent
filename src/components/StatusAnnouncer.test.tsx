/** Unit tests for StatusAnnouncer logic (A1 — ARIA live region).
 *
 *  Tests deriveAnnouncement() — the pure function that maps raw voiceState
 *  enum + status + connectionState to announcement messages. Urgency is
 *  derived from the enum, not substring-matching on localized labels.
 *
 *  Context: docs/ACCESSIBILITY_UNIVERSAL_LAYER_BRIEF_FOR_PI.md (A1)
 *  Review fix (2026-07-16): tests now use the raw enum + a stub t() so they
 *  don't depend on a specific locale's localized label text.
 */
import { describe, expect, test } from "vitest";
import { deriveAnnouncement } from "./StatusAnnouncer";
import type { VoiceState } from "../lib/voiceState";

// Stub t() — returns the key so tests are locale-independent. Real i18n is
// verified by typecheck + the locale JSON files.
const t = (key: string) => key;

describe("deriveAnnouncement — idle/silent cases", () => {
  test("returns null for idle + idle connection", () => {
    expect(deriveAnnouncement("idle", "Idle", "idle", t)).toBeNull();
  });

  test("returns null for connected idle state", () => {
    expect(deriveAnnouncement("idle", "Spreman", "connected", t)).toBeNull();
  });
});

describe("deriveAnnouncement — polite cases", () => {
  test("returns voice label for listening", () => {
    // voiceStateLabel("listening") calls the global i18n instance → "Slušam"
    const result = deriveAnnouncement("listening", "Idle", "connected", t);
    expect(result).toBe("Slušam");
  });

  test("returns status when status is meaningful", () => {
    const result = deriveAnnouncement("idle", "Alat traje…", "connected", t);
    expect(result).toBe("Alat traje…");
  });

  test("status takes priority over voice label", () => {
    const result = deriveAnnouncement("listening", "Ricky je uživo.", "connected", t);
    expect(result).toBe("Ricky je uživo.");
  });

  test("returns connecting message (i18n key) for connecting state", () => {
    const result = deriveAnnouncement("idle", "Idle", "connecting", t);
    expect(result).toBe("a11y.announcer.connecting");
  });

  test("returns connecting message for reconnecting", () => {
    const result = deriveAnnouncement("idle", "Idle", "reconnecting", t);
    expect(result).toBe("a11y.announcer.connecting");
  });
});

describe("deriveAnnouncement — assertive (urgent) cases", () => {
  test("reconnect-failed returns i18n error string", () => {
    const result = deriveAnnouncement("idle", "Idle", "reconnect-failed", t);
    expect(result).toBe("a11y.announcer.reconnectFailed");
  });

  test("error voice state returns i18n error string", () => {
    const result = deriveAnnouncement("error", "Idle", "connected", t);
    expect(result).toBe("a11y.announcer.error");
  });

  test("reconnect-failed takes priority over error voice state", () => {
    const result = deriveAnnouncement("error", "Idle", "reconnect-failed", t);
    expect(result).toBe("a11y.announcer.reconnectFailed");
  });

  test("waiting_confirmation returns the localized voice label", () => {
    const result = deriveAnnouncement("waiting_confirmation", "Idle", "connected", t);
    expect(result).toBe("Čekam potvrdu");
  });
});

describe("deriveAnnouncement — dedup contract", () => {
  test("same inputs produce the same output (caller dedups via state)", () => {
    const r1 = deriveAnnouncement("listening", "Idle", "connected", t);
    const r2 = deriveAnnouncement("listening", "Idle", "connected", t);
    expect(r1).toBe(r2);
  });

  test("priority is stable: error > waiting_confirmation > status > voice > connecting", () => {
    // error beats status
    expect(deriveAnnouncement("error", "status text", "connected", t)).toBe("a11y.announcer.error");
    // waiting_confirmation beats status
    expect(deriveAnnouncement("waiting_confirmation", "status text", "connected", t)).toBe("Čekam potvrdu");
    // status beats voice
    expect(deriveAnnouncement("listening", "status text", "connected", t)).toBe("status text");
    // voice beats connecting
    expect(deriveAnnouncement("listening", "Idle", "connecting", t)).toBe("Slušam");
  });
});

describe("deriveAnnouncement — locale independence (review fix #5)", () => {
  // The whole point of enum-based branching: urgency does NOT depend on the
  // localized label text. These tests verify the function never inspects the
  // localized string — it only looks at the enum.
  test("error urgency does not require a localized 'error' keyword", () => {
    // Even with a t() that returns non-Serbian, non-English strings, the enum
    // "error" must still route to the error message.
    const tFrench = (k: string) => (k === "a11y.announcer.error" ? "Erreur" : k);
    const result = deriveAnnouncement("error", "Idle", "connected", tFrench);
    expect(result).toBe("Erreur");
  });
});
