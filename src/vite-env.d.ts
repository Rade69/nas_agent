/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

import type { VoiceState } from "./lib/voiceState";

export type RickyArtifact = {
  title: string;
  kind:
    | "text"
    | "markdown"
    | "code"
    | "table"
    | "notes"
    | "mermaid"
    | "image"
    | "imageLoading"
    | "thumbnailBoard"
    | "progress";
  content: string;
  language?: string;
  fullscreen?: boolean;
};

export type RickyToolSpec = {
  type: "function";
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  risk?: "low" | "medium" | "high" | "critical";
  reads_external_content?: boolean;
};

export type RickyToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  context?: {
    confirmation_id?: string;
    external_content_seen?: boolean;
    computer_mode?: boolean;
  };
};

export type RickyToolResult = {
  ok: boolean;
  artifact?: RickyArtifact;
  mode?: "display" | "computer";
  message?: string;
  error?: string;
  [key: string]: unknown;
};

// --- FAZA 9: confirmations + plans types ---
// "consumed" added for S-04 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md)
// — the confirmation authorized exactly one tool execution attempt and the
// backend has already spent it; it can never be used again.
export type ConfirmationStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "cancelled"
  | "consumed";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type Confirmation = {
  id: string;
  status: ConfirmationStatus;
  action_name: string;
  payload: Record<string, unknown>;
  risk_level: RiskLevel;
  plan_id?: string | null;
  summary?: string | null;
  tool_name?: string | null;
  created_at: string;
  resolved_at?: string | null;
};

export type ConfirmationListResponse = { confirmations: Confirmation[] };
export type ConfirmationDecisionResponse = { ok: boolean; confirmation: Confirmation };

export type PlanStatus =
  | "draft"
  | "proposed"
  | "approved"
  | "running"
  | "completed"
  | "rejected"
  | "cancelled";

export type PlanStepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "skipped"
  | "failed";

export type PlanStep = {
  id: string;
  plan_id: string;
  step_index: number;
  title: string;
  status: PlanStepStatus;
  details: Record<string, unknown>;
};

// User-facing preferences (Settings panel). Mirrors app/schemas/settings.py
// UserSettings — new fields are added on both sides together as the Settings
// panel grows. Context: agent_reports/2026-07-11_settings-panel-foundation.md
export type UserSettings = {
  user_name: string;
  interface_language: string;
  // Empty = use the built-in localized defaults (idle.cmd* i18n keys).
  // Context: agent_reports/2026-07-12_custom-quick-commands.md
  quick_commands: string[];
};

// Dictation Mode "Doradi" menu — mirrors python_backend/app/schemas/text.py
// TextRewriteOperation. Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
export type TextRewriteOperation = "formalize" | "shorten" | "proofread" | "translate_en";

// Screenshot gallery/retention — mirrors python_backend/app/schemas/screenshot.py.
// Context: agent_reports/2026-07-12_screenshot-privacy.md
export type Screenshot = {
  id: string;
  filePath: string;
  createdAt: string;
  sentToModel: boolean;
};

export type Plan = {
  id: string;
  title: string;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
  summary?: string | null;
  steps: PlanStep[];
};

export type PlanListResponse = { plans: Plan[] };

// --- FAZA 11: backend event bridge ---
export type BackendEvent = {
  id: string;
  type: string;
  timestamp: string;
  title: string | null;
  details: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

declare global {
  interface Window {
    ricky: {
      createRealtimeToken: () => Promise<{ value: string; expiresAt: number | null; sttLanguageHint: string }>;
      executeTool: (toolCall: RickyToolCall) => Promise<RickyToolResult>;
      getToolSpecs: () => Promise<RickyToolSpec[]>;
      cancelAllExecutions: () => Promise<{ ok: boolean; cancelled: string[]; count: number }>;
      getSettings: () => Promise<UserSettings>;
      updateSettings: (payload: Partial<UserSettings>) => Promise<UserSettings>;
      rewriteText: (payload: { text: string; operation: TextRewriteOperation }) => Promise<{ text: string }>;
      listScreenshots: () => Promise<{ screenshots: Screenshot[] }>;
      deleteAllScreenshots: () => Promise<{ ok: boolean; deletedCount: number }>;
      quitApp: () => Promise<void>;
      minimizeApp: () => Promise<void>;
      toggleMaximizeApp: () => Promise<void>;
      // FAZA 9: confirmations + plans
      listConfirmations: (filter?: {
        status?: ConfirmationStatus;
        limit?: number;
      }) => Promise<ConfirmationListResponse>;
      listPendingConfirmations: () => Promise<ConfirmationListResponse>;
      createConfirmation: (payload: {
        action_name: string;
        payload?: Record<string, unknown>;
        risk_level?: RiskLevel;
        plan_id?: string | null;
        summary?: string | null;
        tool_name?: string | null;
      }) => Promise<Confirmation>;
      approveConfirmation: (confirmationId: string) => Promise<ConfirmationDecisionResponse>;
      rejectConfirmation: (confirmationId: string) => Promise<ConfirmationDecisionResponse>;
      cancelConfirmation: (confirmationId: string) => Promise<ConfirmationDecisionResponse>;
      listPlans: () => Promise<PlanListResponse>;
      createPlan: (payload: {
        title: string;
        summary?: string | null;
        steps?: { title: string; details?: Record<string, unknown> }[];
      }) => Promise<Plan>;
      getPlan: (planId: string) => Promise<Plan>;
      updatePlan: (
        planId: string,
        payload: { title?: string; summary?: string | null; status?: PlanStatus },
      ) => Promise<Plan>;
      updatePlanStep: (
        planId: string,
        stepId: string,
        payload: { status?: PlanStepStatus; title?: string; details?: Record<string, unknown> },
      ) => Promise<Plan>;
      // FAZA 11: event bridge
      listEvents: (since?: string) => Promise<{
        events: BackendEvent[];
        next_cursor: string | null;
      }>;
      // FAZA 12: companion orb
      companionShow: () => Promise<{ ok: boolean }>;
      companionHide: () => Promise<{ ok: boolean }>;
      companionToggle: () => Promise<{ ok: boolean }>;
      companionUpdateVoiceState: (state: VoiceState) => Promise<{ ok: boolean }>;
      companionClick: () => Promise<{ ok: boolean }>;
      companionOpenMain: () => Promise<{ ok: boolean }>;
      companionToggleVoice: () => Promise<{ ok: boolean }>;
      companionToggleLock: (locked: boolean) => Promise<{ ok: boolean }>;
      companionStop: () => Promise<void>;
      companionMenu: () => Promise<void>;
      onCompanionVoiceState: (handler: (state: VoiceState) => void) => () => void;
      onCompanionToggleVoice: (handler: () => void) => () => void;
      // FAZA S-4: global kill-switch event (main → renderer). Returns unsubscribe.
      onKillSwitch: (handler: () => void) => () => void;
    };
  }
}
