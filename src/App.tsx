import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { ConfirmationDialog } from "./components/ConfirmationDialog";
import { PlansPanel } from "./components/PlansPanel";
import { RickyOrb } from "./components/RickyOrb";
import { Sidebar } from "./components/Sidebar";
import {
  ActivityDrawerPreview,
  ConfirmationPreview,
  EmptyPreviewState,
  PlansDrawerPreview,
  planStatusLabel,
} from "./components/pixel/Previews";
import { DictationScreen } from "./components/pixel/DictationScreen";
import { TopBar } from "./components/pixel/TopBar";
import { Drawer } from "./components/pixel/Drawer";
import { MiniComputerWindow } from "./components/pixel/MiniComputerWindow";
import { IdleScreen } from "./components/pixel/IdleScreen";
import { PixelMockupBoard } from "./components/pixel/PixelMockupBoard";
import { categoryForActivity } from "./lib/activityIcons";
import { voiceStateLabel } from "./lib/voiceState";
import IconCalendar from "../assets/brending/icons/actions/icon-calendar.svg?react";
import IconOpenApp from "../assets/brending/icons/actions/icon-open-app.svg?react";
import IconScreenshot from "../assets/brending/icons/actions/icon-screenshot.svg?react";
import IconWarning from "../assets/brending/icons/safety/icon-warning.svg?react";
import IconSuccess from "../assets/brending/icons/status/icon-status-success.svg?react";
import IconBackend from "../assets/brending/icons/system/icon-backend.svg?react";
import IconChevronDown from "../assets/brending/icons/ui/icon-chevron-down.svg?react";
import IconChevronRight from "../assets/brending/icons/ui/icon-chevron-right.svg?react";
import IconClose from "../assets/brending/icons/window/icon-close.svg?react";
import IconMaximize from "../assets/brending/icons/window/icon-maximize.svg?react";
import IconMinimize from "../assets/brending/icons/window/icon-minimize.svg?react";
import IconMic from "../assets/brending/icons/voice/icon-microphone.svg?react";
import IconMicOff from "../assets/brending/icons/voice/icon-microphone-muted.svg?react";
import IconSend from "../assets/brending/icons/voice/icon-send.svg?react";
import IconStop from "../assets/brending/icons/voice/icon-stop.svg?react";
import IconWave from "../assets/brending/icons/voice/icon-audio-wave.svg?react";
import IconLogoR from "../assets/brending/logo/ricky-logo-r.svg?react";
import rikiAvatar from "../assets/Riki-avatar.png";
import {
  createActivityEvent,
  newEntry,
  RickyRealtimeClient,
  type ActivityEvent,
  type MouthShape,
  type RickyConnectionState,
  type RickyMood,
  type TranscriptEntry,
  type VoiceState,
} from "./lib/realtime";
import type { BackendEvent, Confirmation, Plan, PlanStepStatus, RickyArtifact } from "./vite-env";

import type { RickyMode, ScreenState, DrawerState } from "./components/pixel/types";

const SYSTEM_NOISE_TITLES = ["Backend ready", "Renderer ready", "Voice-first shell", "Backend spreman", "Renderer spreman"];

function getInitialMode(): RickyMode {
  const params = new URLSearchParams(window.location.search);
  return params.get("mode") === "computer" ? "computer" : "display";
}

function isMiniWindow() {
  return new URLSearchParams(window.location.search).get("window") === "mini";
}

export default function App() {
  const [connectionState, setConnectionState] = useState<RickyConnectionState>("idle");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [, setMood] = useState<RickyMood>("idle");
  const [mode, setMode] = useState<RickyMode>(() => getInitialMode());
  const [artifact, setArtifact] = useState<RickyArtifact | null>(null);
  const [artifactVisible, setArtifactVisible] = useState(false);
  const [artifactFullscreen, setArtifactFullscreen] = useState(false);
  const [, setMouthShape] = useState<MouthShape>({ open: 0, width: 0.18, round: 0, teeth: 0 });
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([
    newEntry("system", "Ricky je spreman. Pokreni glas i govori prirodno."),
  ]);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([
    createActivityEvent("status", "Renderer spreman", "GUI je učitan."),
  ]);
  const [, setStatus] = useState("Idle");
  const [textPrompt, setTextPrompt] = useState("");
  const [pendingConfirmation, setPendingConfirmation] = useState<Confirmation | null>(null);
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [busyStepId, setBusyStepId] = useState<string | null>(null);
  const [screen, setScreen] = useState<ScreenState>("home");
  const [activeDrawer, setActiveDrawer] = useState<DrawerState>(null);
  const [killFlash, setKillFlash] = useState(false);
  const [dictationText, setDictationText] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const clientRef = useRef<RickyRealtimeClient | null>(null);

  const isConnected = connectionState === "connected";
  const isActive =
    voiceState === "listening" ||
    voiceState === "transcribing" ||
    voiceState === "thinking" ||
    voiceState === "speaking" ||
    voiceState === "waiting_confirmation";
  const isMini = isMiniWindow();

  const recentActivity = useMemo(
    () =>
      activityEvents
        .filter((event) => event.kind !== "status" || !SYSTEM_NOISE_TITLES.some((noise) => event.title.includes(noise)))
        .slice(0, 4),
    [activityEvents],
  );

  useEffect(() => {
    if (pendingConfirmation && pendingConfirmation.status === "pending") {
      setVoiceState("waiting_confirmation");
    }
  }, [pendingConfirmation]);

  useEffect(() => {
    let cancelled = false;
    let cursor: string | null = null;
    let isFirstPoll = true;

    async function refreshPending() {
      try {
        const response = await window.ricky.listPendingConfirmations();
        if (cancelled) return;
        const next = response?.confirmations?.[0] ?? null;
        setPendingConfirmation((current) => {
          if (next && (!current || current.id !== next.id)) return next;
          if (!next && current && current.status !== "pending") return null;
          return current;
        });
      } catch {
        /* polling stays silent */
      }
    }

    async function pollEvents() {
      try {
        const response = await window.ricky.listEvents(cursor ?? undefined);
        if (cancelled) return;
        const events: BackendEvent[] = response?.events ?? [];
        if (response?.next_cursor) cursor = response.next_cursor;
        const replayingHistory = isFirstPoll;
        isFirstPoll = false;

        for (const event of events) {
          if (event.type === "artifact.created") {
            if (replayingHistory) continue;
            const artifactId = event.details?.artifact_id;
            if (typeof artifactId === "string") {
              try {
                const result = await window.ricky.executeTool({ name: "artifact_get", arguments: { id: artifactId } });
                if ((result as Record<string, unknown>).artifact) {
                  setArtifact((result as Record<string, unknown>).artifact as RickyArtifact);
                  setArtifactVisible(true);
                }
              } catch {
                /* ignore artifact fetch errors */
              }
            }
          } else if (event.type === "tool.completed" || event.type === "tool.failed") {
            if (replayingHistory) continue;
            addActivityEvent(createActivityEvent("tool", event.title || event.type, event.type));
          } else if (event.type === "backend.ready") {
            setBackendConnected(true);
            if (replayingHistory) continue;
            addActivityEvent(createActivityEvent("status", "Backend spreman", "Python backend povezan"));
          }
        }
      } catch {
        /* polling stays silent */
      }
    }

    async function pollHealth() {
      try {
        await window.ricky.listEvents();
        setBackendConnected(true);
      } catch {
        setBackendConnected(false);
      }
    }

    async function pollAll() {
      await Promise.allSettled([refreshPending(), pollEvents(), pollHealth()]);
    }

    void pollAll();
    const interval = window.setInterval(pollAll, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const client = new RickyRealtimeClient({
      onConnectionState: setConnectionState,
      onVoiceState: setVoiceState,
      onMood: setMood,
      onStatus: setStatus,
      onMouthShape: setMouthShape,
      onTranscript: (entry) => setTranscript((list) => [entry, ...list].slice(0, 200)),
      onArtifact: (next) => {
        setArtifact(next);
        setArtifactVisible(true);
      },
      onActivity: addActivityEvent,
      onMode: (next) => setMode(next as RickyMode),
      onThumbnailReady: () => {},
    });
    clientRef.current = client;
    return () => {
      client.disconnect();
    };
  }, []);

  useEffect(() => {
    if (activeDrawer === "plans") void refreshPlans();
  }, [activeDrawer]);

  // FAZA S-4: kill-switch — stop everything (voice/mic + Computer Mode) with a
  // brief on-screen confirmation. Two triggers:
  //  1. Escape while Ricky is focused (fast, local; does NOT hijack Esc in other
  //     apps). Skipped while typing in an input/textarea so text editing works.
  //  2. Ctrl+Alt+K global hotkey (main process) — works even when unfocused.
  function runKillSwitch() {
    clientRef.current?.disconnect();
    setVoiceState("idle");
    setMode("display");
    // Backend half: also cancel any in-flight tool. Covers every kill-switch
    // trigger (Escape, Ctrl+Alt+K, and the companion orb Stop button, which all
    // funnel through here) — previously only the main Stop button did this.
    // Context: agent_reports/2026-07-09_stop-cancellation-wiring.md
    void window.ricky.cancelAllExecutions().catch(() => {
      /* best-effort; voice/mic is already torn down above */
    });
    addActivityEvent(createActivityEvent("status", "Kill-switch", "Sve zaustavljeno"));
    setKillFlash(true);
    window.setTimeout(() => setKillFlash(false), 2200);
  }

  useEffect(() => {
    const unsubscribe = window.ricky.onKillSwitch?.(() => runKillSwitch());
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      const tag = (document.activeElement as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      runKillSwitch();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => {
      unsubscribe?.();
      window.removeEventListener("keydown", onKeyDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function addActivityEvent(event: ActivityEvent) {
    setActivityEvents((items) => [event, ...items].slice(0, 80));
  }

  async function connect() {
    setBackendConnected(false);
    await clientRef.current?.connect();
  }

  // Companion orb "Uključi/isključi glas" menu item forwards companion:toggle-voice
  // from the main process; this was previously never subscribed to in the
  // renderer, so the menu item was a silent no-op. Mirrors the main mic button's
  // isConnected ? disconnect : connect toggle.
  useEffect(() => {
    const unsubscribe = window.ricky.onCompanionToggleVoice?.(() => {
      if (isConnected) {
        disconnect();
      } else {
        void connect();
      }
    });
    return () => unsubscribe?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  function disconnect() {
    clientRef.current?.disconnect();
  }

  function sendText(text: string) {
    clientRef.current?.sendText(text);
  }

  function sendTextPrompt() {
    const trimmed = textPrompt.trim();
    if (!trimmed) return;
    sendText(trimmed);
    setTextPrompt("");
  }

  async function switchMode(nextMode: RickyMode) {
    const result = await window.ricky.executeTool({ name: "set_mode", arguments: { mode: nextMode } });
    setMode(nextMode);
    if ((result as Record<string, unknown>).mode === "display") setArtifactVisible(false);
  }

  async function refreshPlans() {
    try {
      const response = await window.ricky.listPlans();
      setPlans(response?.plans ?? []);
    } catch {
      /* silent */
    }
  }

  async function handleCreatePlan() {
    try {
      const created = await window.ricky.createPlan({ title: "Novi plan" });
      if (created) setPlans((list) => [created, ...list]);
    } catch {
      /* silent */
    }
  }

  async function handleApproveConfirmation(confirmationId: string) {
    setConfirmationBusy(true);
    try {
      const result = await window.ricky.approveConfirmation(confirmationId);
      const approved = result?.confirmation ?? null;
      setPendingConfirmation(approved);
      addActivityEvent(createActivityEvent("status", "Potvrda odobrena", `Odobreno ${confirmationId}`));
      if (approved?.tool_name) {
        try {
          const retryResult = await window.ricky.executeTool({
            name: approved.tool_name,
            arguments: approved.payload || {},
            context: { confirmation_id: confirmationId, computer_mode: true },
          } as { name: string; arguments: Record<string, unknown>; context: Record<string, unknown> });
          const retryResultObj = retryResult as Record<string, unknown>;
          if (retryResultObj.ok === false) {
            addActivityEvent(
              createActivityEvent(
                "error",
                `Ponovno izvršenje alata ${approved.tool_name} je blokirano`,
                typeof retryResultObj.error === "string" ? retryResultObj.error : "Alat nije izvršen poslije potvrde.",
              ),
            );
          } else {
            if (retryResultObj.artifact) {
              setArtifact(retryResultObj.artifact as RickyArtifact);
              setArtifactVisible(true);
            }
            addActivityEvent(createActivityEvent("tool", `Ponovo izvršen alat ${approved.tool_name}`, `Potvrda ${confirmationId}`));
          }
        } catch (retryErr) {
          addActivityEvent(createActivityEvent("error", "Ponovno izvršenje nije uspjelo", retryErr instanceof Error ? retryErr.message : String(retryErr)));
        }
      }
    } catch (error) {
      addActivityEvent(createActivityEvent("error", "Odobrenje nije uspjelo", error instanceof Error ? error.message : String(error)));
    } finally {
      setConfirmationBusy(false);
      setVoiceState("idle");
    }
  }

  async function handleRejectConfirmation(confirmationId: string) {
    setConfirmationBusy(true);
    try {
      const result = await window.ricky.rejectConfirmation(confirmationId);
      setPendingConfirmation(result?.confirmation ?? null);
      addActivityEvent(createActivityEvent("status", "Potvrda odbijena", `Odbijeno ${confirmationId}`));
    } catch (error) {
      addActivityEvent(createActivityEvent("error", "Odbijanje nije uspjelo", error instanceof Error ? error.message : String(error)));
    } finally {
      setConfirmationBusy(false);
      setVoiceState("idle");
    }
  }

  async function handleCancelConfirmation(confirmationId: string) {
    setConfirmationBusy(true);
    try {
      const result = await window.ricky.cancelConfirmation(confirmationId);
      setPendingConfirmation(result?.confirmation ?? null);
    } catch {
      setPendingConfirmation(null);
    } finally {
      setConfirmationBusy(false);
      setVoiceState("idle");
    }
  }

  async function handleUpdatePlanStatus(planId: string, status: string) {
    setBusyPlanId(planId);
    try {
      const result = await window.ricky.updatePlan(planId, { status: status as Plan["status"] });
      if (result) setPlans((list) => list.map((plan) => (plan.id === planId ? result : plan)));
    } catch {
      /* silent */
    }
    setBusyPlanId(null);
  }

  async function handleUpdateStepStatus(planId: string, stepId: string, status: string) {
    setBusyStepId(stepId);
    try {
      const result = await window.ricky.updatePlanStep(planId, stepId, { status: status as PlanStepStatus });
      if (result) setPlans((list) => list.map((plan) => (plan.id === planId ? result : plan)));
    } catch {
      /* silent */
    }
    setBusyStepId(null);
  }

  function handleStop() {
    clientRef.current?.disconnect();
    setVoiceState("interrupted");
    // Backend half of "stop": the disconnect above only tears down the voice/mic
    // session, so also flag every in-flight tool for cancellation (FAZA 10
    // cancellation registry). Best-effort — the voice session is already stopped.
    // Context: agent_reports/2026-07-09_stop-cancellation-wiring.md
    void window.ricky.cancelAllExecutions().catch(() => {
      /* best-effort; nothing more to do if the backend cancel call fails */
    });
    addActivityEvent(createActivityEvent("status", "Zaustavljeno", "Korisnik je pritisnuo Stop"));
  }

  function openDrawer(drawer: Exclude<DrawerState, null>) {
    setActiveDrawer(drawer);
  }

  function handleSidebarChange(id: string) {
    if (id === "home") {
      setScreen("home");
      setActiveDrawer(null);
      return;
    }
    openDrawer(id as Exclude<DrawerState, null>);
  }

  if (isMini) {
    return (
      <MiniComputerWindow
        voiceState={voiceState}
        onRestore={() => {
          void switchMode("display");
        }}
      />
    );
  }

  return (
    <main className="pixel-app-shell pixel-board-shell">
      {killFlash ? (
        <div className="kill-switch-flash" role="status">⛔ Zaustavljeno — glas i mikrofon isključeni</div>
      ) : null}
      <div className="pixel-global-window-controls" aria-label="Kontrole prozora">
        <button className="pixel-icon-button" onClick={() => void window.ricky.minimizeApp()} title="Minimizuj">
          <IconMinimize />
        </button>
        <button className="pixel-icon-button" onClick={() => void window.ricky.toggleMaximizeApp()} title="Maksimizuj">
          <IconMaximize />
        </button>
        <button className="pixel-icon-button pixel-close" onClick={() => void window.ricky.quitApp()} title="Zatvori">
          <IconClose />
        </button>
      </div>
      <PixelMockupBoard
        mode={mode}
        screen={screen}
        voiceState={voiceState}
        isActive={isActive}
        isConnected={isConnected}
        textPrompt={textPrompt}
        dictationText={dictationText}
        recentActivity={recentActivity}
        activityEvents={activityEvents}
        transcript={transcript}
        plans={plans}
        activeDrawer={activeDrawer}
        backendConnected={backendConnected}
        busyPlanId={busyPlanId}
        busyStepId={busyStepId}
        onToggleMode={() => {
          const nextMode = mode === "computer" ? "display" : "computer";
          void switchMode(nextMode);
        }}
        onOpenPlans={() => openDrawer("plans")}
        onSidebarChange={handleSidebarChange}
        onTextPromptChange={setTextPrompt}
        onSendTextPrompt={sendTextPrompt}
        onVoiceToggle={isConnected ? disconnect : () => void connect()}
        onStop={handleStop}
        onOpenActivity={() => openDrawer("activity")}
        onQuickCommand={(text) => {
          if (text.toLowerCase().includes("dikt")) setScreen("dictation");
          sendText(text);
        }}
        onDictationChange={setDictationText}
        onDictationCancel={() => setScreen("home")}
        onDictationSend={() => {
          if (dictationText.trim()) sendText(dictationText.trim());
          setScreen("home");
        }}
        onStopAll={runKillSwitch}
        onCloseDrawer={() => setActiveDrawer(null)}
        onUpdatePlanStatus={handleUpdatePlanStatus}
        onUpdateStepStatus={handleUpdateStepStatus}
        onCreatePlan={handleCreatePlan}
      />

      {artifactVisible && artifact ? (
        <ArtifactPanel
          artifact={artifact}
          visible={artifactVisible}
          fullscreen={artifactFullscreen}
          onToggleVisible={() => setArtifactVisible((value) => !value)}
          onToggleFullscreen={() => setArtifactFullscreen((value) => !value)}
        />
      ) : null}

      <ConfirmationDialog
        confirmation={pendingConfirmation}
        busy={confirmationBusy}
        onApprove={handleApproveConfirmation}
        onReject={handleRejectConfirmation}
        onCancel={handleCancelConfirmation}
      />
    </main>
  );
}

