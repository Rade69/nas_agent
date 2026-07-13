/** Negative-security unit tests for diagnostics ring buffer (R0 corrections).
 *  Verifies that push() MANDATORILY sanitizes all fields, all categories,
 *  and that no sensitive literal survives into snapshot().
 *  Context: docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md §0.1 */
import { describe, it, expect } from "vitest";
import {
  createDiagnosticsRing,
  MAX_EVENTS,
  type RealtimeDiagnosticEvent,
  type DiagnosticCategory,
} from "../realtimeDiagnostics";

function rawEvent(
  overrides?: Partial<RealtimeDiagnosticEvent>,
): RealtimeDiagnosticEvent {
  return {
    at: 100,
    generation: 1,
    category: "connection",
    name: "test_event",
    ...overrides,
  };
}

// ---------- basic ring buffer behavior ----------

describe("createDiagnosticsRing — basic behavior", () => {
  it("starts empty", () => {
    const ring = createDiagnosticsRing();
    expect(ring.length()).toBe(0);
    expect(ring.totalPushed()).toBe(0);
    expect(ring.snapshot()).toEqual([]);
  });

  it("pushes and retrieves safe events in order", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ at: 100, name: "dc_open" }));
    ring.push(rawEvent({ at: 200, name: "ice_connected" }));
    ring.push(rawEvent({ at: 300, name: "peer_negotiated" }));

    expect(ring.length()).toBe(3);
    expect(ring.totalPushed()).toBe(3);

    const snap = ring.snapshot();
    expect(snap).toHaveLength(3);
    expect(snap[0].name).toBe("dc_open");
    expect(snap[1].name).toBe("ice_connected");
    expect(snap[2].name).toBe("peer_negotiated");
  });

  it("evicts oldest when exceeding MAX_EVENTS", () => {
    const ring = createDiagnosticsRing();
    for (let i = 0; i < MAX_EVENTS + 1; i++) {
      ring.push(rawEvent({ at: i, name: `e${i}` }));
    }
    expect(ring.length()).toBe(MAX_EVENTS);
    expect(ring.totalPushed()).toBe(MAX_EVENTS + 1);
    const snap = ring.snapshot();
    expect(snap[0].name).toBe("e1"); // e0 evicted
    expect(snap[snap.length - 1].name).toBe(`e${MAX_EVENTS}`);
  });

  it("snapshot(count) returns last N events", () => {
    const ring = createDiagnosticsRing();
    for (let i = 0; i < 10; i++) ring.push(rawEvent({ at: i, name: `e${i}` }));
    const last3 = ring.snapshot(3);
    expect(last3).toHaveLength(3);
    expect(last3[0].name).toBe("e7");
    expect(last3[2].name).toBe("e9");
  });

  it("snapshot result is frozen (shallow array)", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ name: "a" }));
    const snap = ring.snapshot();
    expect(Object.isFrozen(snap)).toBe(true);
  });

  it("snapshot objects are deep-frozen (immutable)", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ name: "ok_event" }));
    const snap = ring.snapshot();
    expect(Object.isFrozen(snap[0])).toBe(true);
  });
});

// ---------- mandatory sanitization: all categories, all fields ----------

const ALL_CATEGORIES: DiagnosticCategory[] = [
  "connection", "ice", "data_channel", "audio_input", "audio_output", "event", "tool",
];

/** Sensitive payloads that must NOT survive in any form. */
const SENSITIVE_PAYLOADS: { label: string; value: string }[] = [
  { label: "plain transcript", value: "Zdravo Ricky, kako si danas?" },
  { label: "JSON tool args", value: '{"file": "C:\\secret.txt", "mode": "overwrite"}' },
  { label: "JSON tool result", value: '{"ok":true,"path":"C:\\Users\\user\\Documents\\report.pdf"}' },
  { label: "Windows absolute path", value: "C:\\Users\\38765\\Desktop\\passwords.txt" },
  { label: "UNC path", value: "\\\\server\\share\\finance\\budget.xlsx" },
  { label: "file:// URL", value: "file:///C:/Users/38765/Documents/secret.docx" },
  { label: "URL with token query", value: "https://api.example.com/data?token=sk-abc123def456" },
  { label: "Bearer authorization header", value: "Bearer sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx" },
  { label: "API key-like string", value: "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456" },
  { label: "long free-text (>64 chars)", value: "a".repeat(100) },
  { label: "spaces in name", value: "user said something secret" },
];

describe("push() mandatory sanitization — sensitive content via name", () => {
  for (const cat of ALL_CATEGORIES) {
    for (const payload of SENSITIVE_PAYLOADS) {
      it(`redacts [${payload.label}] in category "${cat}" via name field`, () => {
        const ring = createDiagnosticsRing();
        ring.push(rawEvent({ category: cat, name: payload.value }));
        const snap = ring.snapshot();
        expect(snap).toHaveLength(1);

        const stored = snap[0];
        // The stored name must NOT contain any of the original value.
        expect(stored.name).not.toContain(payload.value);
        // It must also not partially leak recognizable fragments.
        if (payload.value.length > 4) {
          // Check that the first 4 chars of the payload aren't in the stored name
          // (catches partial leaks like "Zdra" from "Zdravo Ricky...")
          const fragment = payload.value.slice(0, Math.min(8, payload.value.length));
          if (fragment.length >= 4) {
            expect(stored.name).not.toContain(fragment.slice(0, 4));
          }
        }
        // The stored name should be "redacted" or "redacted" (empty only for empty inputs that were empty)
        // Since all our payloads have non-empty, non-matching names, they should all become "redacted"
        if (payload.value.length > 0) {
          // Either "redacted" (unsafe) or a different safe name (safe, but none match)
          // Since none of our payloads match SAFE_FIELD_RE, they should all be "redacted"
          expect(stored.name).toBe("redacted");
        }
      });
    }
  }
});

describe("push() mandatory sanitization — sensitive content via code", () => {
  for (const cat of ALL_CATEGORIES) {
    for (const payload of SENSITIVE_PAYLOADS) {
      it(`redacts [${payload.label}] in category "${cat}" via code field`, () => {
        const ring = createDiagnosticsRing();
        ring.push(rawEvent({ category: cat, name: "safe_name", code: payload.value }));
        const snap = ring.snapshot();
        expect(snap).toHaveLength(1);

        const stored = snap[0];
        // Name is safe — should be unchanged
        expect(stored.name).toBe("safe_name");
        // Code must be redacted
        expect(stored.code).toBe("redacted");
      });
    }
  }
});

describe("push() mandatory sanitization — safe values pass through", () => {
  it("preserves valid technical name", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ category: "connection", name: "peer_connected", code: "OK" }));
    const snap = ring.snapshot();
    expect(snap[0].name).toBe("peer_connected");
    expect(snap[0].code).toBe("OK");
  });

  it("preserves event-type names with dots and colons", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({
      category: "event",
      name: "response.done",
      code: "R200",
    }));
    const snap = ring.snapshot();
    expect(snap[0].name).toBe("response.done");
    expect(snap[0].code).toBe("R200");
  });

  it("handles empty/undefined code gracefully", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ category: "tool", name: "tool_started", code: undefined }));
    const snap = ring.snapshot();
    expect(snap[0].code).toBeUndefined();
  });

  it("handles empty code string", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ category: "tool", name: "tool_started", code: "" }));
    const snap = ring.snapshot();
    expect(snap[0].code).toBe("");
  });
});

describe("push() mandatory sanitization — invalid categories", () => {
  it("maps unknown category to 'event'", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({
      category: "transcript" as DiagnosticCategory,
      name: "safe_name",
    }));
    const snap = ring.snapshot();
    expect(snap[0].category).toBe("event");
  });
});

describe("push() mandatory sanitization — non-finite numbers", () => {
  it("sanitizes NaN at to 0", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ at: NaN, name: "dc_open" }));
    const snap = ring.snapshot();
    expect(snap[0].at).toBe(0);
  });

  it("sanitizes Infinity durationMs to 0", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ name: "dc_open", durationMs: Infinity }));
    const snap = ring.snapshot();
    expect(snap[0].durationMs).toBe(0);
  });

  it("sanitizes -Infinity generation to 0", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ generation: -Infinity, name: "dc_open" }));
    const snap = ring.snapshot();
    expect(snap[0].generation).toBe(0);
  });
});

// ---------- post-push mutation protection ----------

describe("push() — post-push mutation does not affect stored data", () => {
  it("mutating original event after push() does not change snapshot", () => {
    const ring = createDiagnosticsRing();
    const event = rawEvent({ name: "original_name" });
    ring.push(event);

    // Mutate the original
    event.name = "mutated_name";
    event.at = 999;
    event.code = "mutated_code";

    const snap = ring.snapshot();
    expect(snap[0].name).toBe("original_name");
    expect(snap[0].at).toBe(100);
    expect(snap[0].code).toBeUndefined();
  });

  it("mutating snapshot element does not affect next snapshot", () => {
    const ring = createDiagnosticsRing();
    ring.push(rawEvent({ name: "stored_name" }));

    const snap1 = ring.snapshot();
    // Attempt to assign to frozen object — throws in strict mode
    expect(() => {
      (snap1[0] as Record<string, unknown>).name = "hacked";
    }).toThrow();

    const snap2 = ring.snapshot();
    expect(snap2[0].name).toBe("stored_name");
  });

  it("original event reference is NOT stored (defense in depth)", () => {
    const ring = createDiagnosticsRing();
    const event = rawEvent({ name: "ref_check" });
    ring.push(event);

    const snap = ring.snapshot();
    // Stored object must be a DIFFERENT reference from the original
    expect(snap[0]).not.toBe(event);
  });
});

// ---------- edge cases ----------

describe("createDiagnosticsRing — edge cases", () => {
  it("length never exceeds MAX_EVENTS", () => {
    const ring = createDiagnosticsRing();
    for (let i = 0; i < MAX_EVENTS * 2; i++) {
      ring.push(rawEvent({ at: i, name: `e${i % 1000}` }));
      expect(ring.length()).toBeLessThanOrEqual(MAX_EVENTS);
    }
  });

  it("totalPushed counts all events including evicted", () => {
    const ring = createDiagnosticsRing();
    for (let i = 0; i < MAX_EVENTS + 50; i++) {
      ring.push(rawEvent({ at: i, name: "ev" }));
    }
    expect(ring.length()).toBe(MAX_EVENTS);
    expect(ring.totalPushed()).toBe(MAX_EVENTS + 50);
  });

  it("name longer than 64 chars is redacted even if all safe chars", () => {
    const ring = createDiagnosticsRing();
    const longSafeName = "a".repeat(65); // all 'a' — safe chars, but too long
    ring.push(rawEvent({ name: longSafeName }));

    const snap = ring.snapshot();
    expect(snap[0].name).toBe("redacted");
    // Verify the original long value is NOT in the stored name
    expect(snap[0].name).not.toBe(longSafeName);
  });

  it("name of exactly 64 safe chars is preserved", () => {
    const ring = createDiagnosticsRing();
    const maxSafeName = "a".repeat(64);
    ring.push(rawEvent({ name: maxSafeName }));

    const snap = ring.snapshot();
    expect(snap[0].name).toBe(maxSafeName);
  });
});