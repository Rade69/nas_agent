/** Redacted diagnostics ring buffer for voice reliability observability (R0).
 *  Stores up to MAX_EVENTS technical events (connection, ICE, data channel,
 *  audio I/O, event routing, tool lifecycle). Sanitization is MANDATORY
 *  inside push() — callers cannot bypass it. Never stores raw payload,
 *  transcript, delta content, tool arguments/results, API keys, file paths,
 *  URLs with tokens, or any other free-form dynamic text.
 *  NOT yet integrated into RickyRealtimeClient (planned for R1/R2).
 *  Context: docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md R0 */
export type DiagnosticCategory =
  | "connection"
  | "ice"
  | "data_channel"
  | "audio_input"
  | "audio_output"
  | "event"
  | "tool";

export type RealtimeDiagnosticEvent = {
  /** Monotonic timestamp (performance.now() or fake clock). */
  at: number;
  /** Session generation the event belongs to (0 = pre-connect). */
  generation: number;
  /** Technical category. */
  category: DiagnosticCategory;
  /** Short technical name — only [a-zA-Z0-9_\-.:], max 64 chars. */
  name: string;
  /** Optional duration in milliseconds. */
  durationMs?: number;
  /** Optional stable error/status code — only [a-zA-Z0-9_\-.:], max 64 chars. */
  code?: string;
};

/** Maximum number of events before oldest are evicted. */
export const MAX_EVENTS = 300;

// ---------- sanitization (mandatory, fail-closed) ----------

/** Allowed character set for name and code fields. */
const SAFE_FIELD_RE = /^[a-zA-Z0-9_\-.:]{1,64}$/;

/** Patterns that look like API keys, bearer tokens, or URLs with auth
 *  credentials — must never pass sanitization even if SAFE_FIELD_RE matches. */
const UNSAFE_PATTERNS: ReadonlyArray<{ re: RegExp; label: string }> = [
  { re: /^sk-/i, label: "OpenAI/Anthropic API key prefix" },
  { re: /^sk_/i, label: "API key prefix variant" },
  { re: /^api[-_]key/i, label: "api-key literal" },
  { re: /^bearer\s/i, label: "Bearer token header" },
  { re: /^basic\s/i, label: "Basic auth header" },
  { re: /[?&](?:token|key|auth|api_key|secret|access_token)=/i, label: "URL with auth query param" },
];

/** Replaces unsafe name/code with the fixed sentinel. Never preserves
 *  the original unsafe value. */
function sanitizeField(raw: string | undefined): string {
  if (raw === undefined) return "";
  // Empty string is allowed (explicit no-value).
  if (raw === "") return "";
  if (!SAFE_FIELD_RE.test(raw)) return "redacted";
  // Check against known unsafe patterns (API keys, bearer tokens, auth URLs)
  for (const pattern of UNSAFE_PATTERNS) {
    if (pattern.re.test(raw)) return "redacted";
  }
  return raw;
}

/** Returns a deep-sanitized copy of the event. The caller MUST use this
 *  copy; the original event reference must never be stored. */
function sanitizeEvent(raw: RealtimeDiagnosticEvent): RealtimeDiagnosticEvent {
  return {
    at: sanitizeNumber(raw.at),
    generation: sanitizeNumber(raw.generation),
    category: sanitizeCategory(raw.category),
    name: sanitizeField(raw.name),
    durationMs: raw.durationMs === undefined ? undefined : sanitizeNumber(raw.durationMs),
    code: raw.code === undefined ? undefined : sanitizeField(raw.code),
  };
}

function sanitizeNumber(n: number): number {
  if (typeof n !== "number" || !Number.isFinite(n)) return 0;
  return n;
}

function sanitizeCategory(c: string): DiagnosticCategory {
  const allowed: readonly DiagnosticCategory[] = [
    "connection", "ice", "data_channel", "audio_input", "audio_output", "event", "tool",
  ];
  return allowed.includes(c as DiagnosticCategory) ? (c as DiagnosticCategory) : "event";
}

// ---------- ring buffer ----------

/** Deep-freezes an event object so snapshot consumers cannot mutate stored data. */
function deepFreezeEvent(e: RealtimeDiagnosticEvent): RealtimeDiagnosticEvent {
  Object.freeze(e);
  return e;
}

/** Creates a new diagnostics ring buffer. All events pushed through it are
 *  MANDATORILY sanitized — callers cannot bypass redaction. */
export function createDiagnosticsRing(): {
  /** Push a raw event. It is sanitized before storage; the original reference
   *  is never retained. */
  push: (event: RealtimeDiagnosticEvent) => void;
  /** Returns a deep-frozen snapshot (oldest → newest), limited to `count`. */
  snapshot: (count?: number) => readonly RealtimeDiagnosticEvent[];
  /** Total events ever pushed (including evicted). */
  totalPushed: () => number;
  /** Current buffer length (≤ MAX_EVENTS). */
  length: () => number;
} {
  const buffer: RealtimeDiagnosticEvent[] = [];
  let pushed = 0;

  return {
    push(event: RealtimeDiagnosticEvent): void {
      // Sanitization is mandatory — caller cannot skip it.
      const safe = sanitizeEvent(event);
      // Freeze immediately so no one can mutate the stored object later.
      deepFreezeEvent(safe);
      if (buffer.length >= MAX_EVENTS) buffer.shift();
      buffer.push(safe);
      pushed++;
      // Verify the original reference was NOT stored (defense in depth).
      if (buffer[buffer.length - 1] === event) {
        throw new Error("Diagnostics invariant violated: raw event reference stored");
      }
    },
    snapshot(count?: number): readonly RealtimeDiagnosticEvent[] {
      const limit = count ?? buffer.length;
      // Return a frozen copy so consumers cannot mutate stored events.
      return Object.freeze(buffer.slice(-limit)) as readonly RealtimeDiagnosticEvent[];
    },
    totalPushed(): number {
      return pushed;
    },
    length(): number {
      return buffer.length;
    },
  };
}