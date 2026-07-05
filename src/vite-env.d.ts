/// <reference types="vite/client" />

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
};

export type RickyToolCall = {
  name: string;
  arguments: Record<string, unknown>;
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
export type ConfirmationStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "cancelled";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type Confirmation = {
  id: string;
  status: ConfirmationStatus;
  action_name: string;
  payload: Record<string, unknown>;
  risk_level: RiskLevel;
  plan_id?: string | null;
  summary?: string | null;
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
      createRealtimeToken: () => Promise<{ value: string; expiresAt: number | null }>;
      executeTool: (toolCall: RickyToolCall) => Promise<RickyToolResult>;
      getToolSpecs: () => Promise<RickyToolSpec[]>;
      quitApp: () => Promise<void>;
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
      onCompanionVoiceState: (handler: (state: VoiceState) => void) => () => void;
      onCompanionToggleVoice: (handler: () => void) => () => void;
    };
  }
}
