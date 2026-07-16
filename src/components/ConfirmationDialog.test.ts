/** Unit tests for ConfirmationDialog A2 logic (focus trap + Escape).
 *
 *  Tests resolveDialogKeyDown() — the pure decision function for the
 *  dialog's keydown handler. Verifies:
 *  - Escape → reject/cancel (NEVER approve)
 *  - Tab wraps within the dialog (focus trap)
 *  - Shift+Tab wraps backward
 *  - Non-Tab/Escape keys are default (no action)
 *
 *  DOM-level testing (document.activeElement) requires jsdom, which would
 *  be a new dependency (against the brief's rules). The decision logic is
 *  extracted and tested here; the DOM wiring is verified via typecheck +
 *  manual NVDA smoke test.
 *
 *  Context: docs/ACCESSIBILITY_UNIVERSAL_LAYER_BRIEF_FOR_PI.md (A2)
 */
import { describe, expect, test } from "vitest";
import { resolveDialogKeyDown } from "./ConfirmationDialog";

describe("resolveDialogKeyDown — Escape (security-critical)", () => {
  test("Escape on pending confirmation → escape action (reject)", () => {
    const result = resolveDialogKeyDown("Escape", false, true, false, 3, 1);
    expect(result).toEqual({ type: "escape" });
  });

  test("Escape when busy → default (no action)", () => {
    const result = resolveDialogKeyDown("Escape", false, true, true, 3, 1);
    expect(result).toEqual({ type: "default" });
  });

  test("Escape when not pending → default", () => {
    const result = resolveDialogKeyDown("Escape", false, false, false, 3, 1);
    expect(result).toEqual({ type: "default" });
  });

  test("Escape NEVER returns an approve action — only escape/default exist", () => {
    // Security property: there is no "approve" action type at all
    for (const busy of [true, false]) {
      for (const pending of [true, false]) {
        const result = resolveDialogKeyDown("Escape", false, pending, busy, 3, 1);
        expect(result.type).not.toBe("approve");
      }
    }
  });
});

describe("resolveDialogKeyDown — focus trap (Tab)", () => {
  test("Tab on last focusable → wrap to first", () => {
    const result = resolveDialogKeyDown("Tab", false, true, false, 3, 2);
    expect(result).toEqual({ type: "wrap-focus", target: "first" });
  });

  test("Tab on middle focusable → default (no wrap, normal Tab)", () => {
    const result = resolveDialogKeyDown("Tab", false, true, false, 3, 1);
    expect(result).toEqual({ type: "default" });
  });

  test("Tab on first focusable → default (normal forward Tab)", () => {
    const result = resolveDialogKeyDown("Tab", false, true, false, 3, 0);
    expect(result).toEqual({ type: "default" });
  });

  test("Shift+Tab on first focusable → wrap to last", () => {
    const result = resolveDialogKeyDown("Tab", true, true, false, 3, 0);
    expect(result).toEqual({ type: "wrap-focus", target: "last" });
  });

  test("Shift+Tab on container (-1) → wrap to last", () => {
    const result = resolveDialogKeyDown("Tab", true, true, false, 3, -1);
    expect(result).toEqual({ type: "wrap-focus", target: "last" });
  });

  test("Shift+Tab on middle → default (normal backward Tab)", () => {
    const result = resolveDialogKeyDown("Tab", true, true, false, 3, 1);
    expect(result).toEqual({ type: "default" });
  });
});

describe("resolveDialogKeyDown — edge cases", () => {
  test("Tab with zero focusable elements → default", () => {
    const result = resolveDialogKeyDown("Tab", false, true, false, 0, -1);
    expect(result).toEqual({ type: "default" });
  });

  test("Any other key → default", () => {
    for (const key of ["Enter", " ", "ArrowDown", "a", "1"]) {
      const result = resolveDialogKeyDown(key, false, true, false, 3, 1);
      expect(result).toEqual({ type: "default" });
    }
  });

  test("Enter on container (-1) → default (NEVER approves)", () => {
    // Security property: Enter must not approve. It returns "default" = no action.
    const result = resolveDialogKeyDown("Enter", false, true, false, 3, -1);
    expect(result).toEqual({ type: "default" });
  });
});