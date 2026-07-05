import { useEffect, useRef, useState } from "react";
import { Expand, ListChecks, X } from "lucide-react";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { BottomVoiceBar } from "./components/BottomVoiceBar";
import { ConfirmationDialog } from "./components/ConfirmationDialog";
import { PlansPanel } from "./components/PlansPanel";
import { RickyFace } from "./components/RickyFace";
import { VoiceTopBar } from "./components/VoiceTopBar";
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
import type { Confirmation, Plan, PlanStepStatus, RickyArtifact } from "./vite-env";

type RickyMode = "display" | "computer";

export default function App() {
  const [connectionState, setConnectionState] = useState<RickyConnectionState>("idle");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [mood, setMood] = useState<RickyMood>("idle");
  const [mode, setMode] = useState<RickyMode>("display");
  const [artifact, setArtifact] = useState<RickyArtifact | null>(null);
  const [artifactVisible, setArtifactVisible] = useState(true);
  const [artifactFullscreen, setArtifactFullscreen] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const [showTypeInput, setShowTypeInput] = useState(false);
  const [mouthShape, setMouthShape] = useState<MouthShape>({ open: 0, width: 0.18, round: 0, teeth: 0 });
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([
    newEntry("system", "Ricky is ready. Connect voice, then talk naturally."),
  ]);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([
    createActivityEvent("status", "Renderer ready", "Voice-first shell loaded."),
  ]);
  const [status, setStatus] = useState("Idle");
  const [textPrompt, setTextPrompt] = useState("");
  // FAZA 9: confirmations + plans UI state.
  const [pendingConfirmation, setPendingConfirmation] = useState<Confirmation | null>(null);
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [showPlans, setShowPlans] = useState(false);
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [busyStepId, setBusyStepId] = useState<string | null>(null);
  const clientRef = useRef<RickyRealtimeClient | null>(null);

  const isConnected = connectionState === "connected";

  // FAZA 9: drive VoiceState into waiting_confirmation while a pending
  // confirmation is visible, so the top bar reflects the safety state. The
  // underlying audio pipeline (src/lib/realtime.ts) is NOT modified — this is
  // an additive UI-side effect layered over the existing VoiceState model.
  useEffect(() => {
    if (pendingConfirmation && pendingConfirmation.status === "pending") {
      setVoiceState("waiting_confirmation");
    }
  }, [pendingConfirmation]);

  // FAZA 9: refresh pending confirmations periodically (lightweight poll —
  // backend push via activity_events arrives in a later phase).
  useEffect(() => {
    let cancelled = false;
    async function refreshPending() {
      try {
        const response = await window.ricky.listPendingConfirmations();
        if (cancelled) return;
        const next = response?.confirmations?.[0] ?? null;
        setPendingConfirmation((current) => {
          // Only auto-show new pending confirmations; keep resolved ones visible
          // briefly via the dialog dismiss flow (handled by setVisible inside
          // the component).
          if (next && (!current || current.id !== next.id)) {
            return next;
          }
          if (!next && current && current.status !== "pending") {
            return null;
          }
          return current;
        });
      } catch {
        // Backend may briefly be unavailable during startup; silent retry.
      }
    }
    refreshPending();
    const interval = window.setInterval(refreshPending, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  async function refreshPlans() {
    try {
      const response = await window.ricky.listPlans();
      setPlans(response?.plans ?? []);
    } catch {
      // Non-fatal: plans panel just stays empty.
    }
  }

  useEffect(() => {
    refreshPlans();
  }, []);

  async function connect() {
    const client = new RickyRealtimeClient({
      onConnectionState: setConnectionState,
      onMood: setMood,
      onMouthShape: setMouthShape,
      onVoiceState: setVoiceState,
      onActivity: addActivityEvent,
      onTranscript: (entry) => setTranscript((items) => [entry, ...items].slice(0, 80)),
      onArtifact: (nextArtifact) => {
        setArtifact(nextArtifact);
        setArtifactVisible(true);
        if (nextArtifact.fullscreen) setArtifactFullscreen(true);
      },
      onMode: (nextMode) => {
        setMode(nextMode);
        if (nextMode === "computer") {
          setArtifactVisible(false);
          setArtifactFullscreen(false);
          setShowLog(false);
          setShowTypeInput(false);
        } else {
          setArtifactVisible(true);
        }
      },
      onStatus: (message) => {
        setStatus(message);
        setTranscript((items) => [newEntry("system", message), ...items].slice(0, 80));
        addActivityEvent(createActivityEvent("status", "Status", message));
      },
      onThumbnailReady: playThumbnailReadySound,
    });
    clientRef.current = client;
    await client.connect();
  }

  function disconnect() {
    clientRef.current?.disconnect();
    clientRef.current = null;
    setStatus("Disconnected");
    addActivityEvent(createActivityEvent("status", "Disconnected"));
  }

  async function switchMode(nextMode: RickyMode) {
    setMode(nextMode);
    const result = await window.ricky.executeTool({ name: "set_mode", arguments: { mode: nextMode } });
    if (result.artifact) setArtifact(result.artifact);
    if (nextMode === "computer") {
      setArtifactVisible(false);
      setArtifactFullscreen(false);
      setShowLog(false);
      setShowTypeInput(false);
    } else {
      setArtifactVisible(true);
    }
    const message = `Mode switched to ${nextMode}.`;
    setTranscript((items) => [newEntry("system", message), ...items].slice(0, 80));
    addActivityEvent(createActivityEvent("status", "Mode changed", message));
  }

  function sendTextPrompt() {
    const trimmed = textPrompt.trim();
    if (!trimmed) return;
    clientRef.current?.sendText(trimmed);
    setTextPrompt("");
    setShowTypeInput(false);
  }

  function addActivityEvent(event: ActivityEvent) {
    setActivityEvents((items) => [event, ...items].slice(0, 80));
  }

  // --- FAZA 9: confirmation + plans handlers ---
  async function handleApproveConfirmation(confirmationId: string) {
    setConfirmationBusy(true);
    try {
      const result = await window.ricky.approveConfirmation(confirmationId);
      setPendingConfirmation(result?.confirmation ?? null);
      addActivityEvent(
        createActivityEvent("status", "Confirmation approved", `Approved ${confirmationId}`),
      );
    } catch (error) {
      addActivityEvent(
        createActivityEvent("error", "Approval failed", error instanceof Error ? error.message : String(error)),
      );
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
      addActivityEvent(
        createActivityEvent("status", "Confirmation rejected", `Rejected ${confirmationId}`),
      );
    } catch (error) {
      addActivityEvent(
        createActivityEvent("error", "Rejection failed", error instanceof Error ? error.message : String(error)),
      );
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
    } catch (error) {
      addActivityEvent(
        createActivityEvent("error", "Cancel failed", error instanceof Error ? error.message : String(error)),
      );
    } finally {
      setConfirmationBusy(false);
      setVoiceState("idle");
    }
  }

  async function handleUpdatePlanStatus(planId: string, status: Plan["status"]) {
    setBusyPlanId(planId);
    try {
      const updated = await window.ricky.updatePlan(planId, { status });
      setPlans((items) => items.map((plan) => (plan.id === planId ? updated : plan)));
      addActivityEvent(createActivityEvent("status", "Plan updated", `${planId} -> ${status}`));
    } catch (error) {
      addActivityEvent(
        createActivityEvent("error", "Plan update failed", error instanceof Error ? error.message : String(error)),
      );
    } finally {
      setBusyPlanId(null);
    }
  }

  async function handleUpdateStepStatus(
    planId: string,
    stepId: string,
    status: PlanStepStatus,
  ) {
    setBusyPlanId(planId);
    setBusyStepId(stepId);
    try {
      const updated = await window.ricky.updatePlanStep(planId, stepId, { status });
      setPlans((items) => items.map((plan) => (plan.id === planId ? updated : plan)));
    } catch (error) {
      addActivityEvent(
        createActivityEvent("error", "Step update failed", error instanceof Error ? error.message : String(error)),
      );
    } finally {
      setBusyPlanId(null);
      setBusyStepId(null);
    }
  }

  if (mode === "computer") {
    return (
      <main className="app-shell app-shell-mini">
        <section className="mini-companion" aria-label="Ricky computer use mini mode">
          <RickyFace mood={mood} mouthShape={mouthShape} />
          <button
            className="mini-restore-button"
            onClick={() => void switchMode("display")}
            aria-label="Return to full Ricky window"
            title="Return to full Ricky window"
          >
            <Expand size={14} />
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <div className="window-drag-strip" aria-hidden="true" />
      <div className="window-drag-left-zone" aria-hidden="true" />
      <button
        className="window-close-button"
        onClick={() => void window.ricky.quitApp()}
        aria-label="Close Ricky"
        title="Close Ricky"
      >
        <X size={15} />
      </button>
      <section className="companion-window">
        <VoiceTopBar
          voiceState={voiceState}
          connectionState={connectionState}
          status={status}
          activityCount={activityEvents.length + transcript.length}
        />

        <section className="face-stage">
          <RickyFace mood={mood} mouthShape={mouthShape} />
        </section>

        <BottomVoiceBar
          voiceState={voiceState}
          connectionState={connectionState}
          isConnected={isConnected}
          isConnecting={connectionState === "connecting"}
          showTypeInput={showTypeInput}
          showLog={showLog}
          artifactVisible={artifactVisible}
          textPrompt={textPrompt}
          onConnectToggle={isConnected ? disconnect : () => void connect()}
          onToggleTextInput={() => setShowTypeInput((value) => !value)}
          onTextPromptChange={setTextPrompt}
          onSendTextPrompt={sendTextPrompt}
          onSwitchDisplayMode={() => void switchMode("display")}
          onSwitchComputerMode={() => void switchMode("computer")}
          onToggleArtifacts={() => setArtifactVisible((value) => !value)}
          onToggleActivity={() => setShowLog((value) => !value)}
        />

        <button
          className={`plans-toggle-button${showPlans ? " active" : ""}`}
          onClick={() => {
            setShowPlans((value) => !value);
            if (!showPlans) void refreshPlans();
          }}
          aria-label="Toggle plans panel"
          title="Ricky plans and proposals"
        >
          <ListChecks size={14} />
          <span>{plans.length}</span>
        </button>

        {showLog ? <ActivityTimeline transcript={transcript} activityEvents={activityEvents} /> : null}
      </section>

      <PlansPanel
        visible={showPlans}
        plans={plans}
        busyPlanId={busyPlanId}
        busyStepId={busyStepId}
        onClose={() => setShowPlans(false)}
        onUpdatePlanStatus={handleUpdatePlanStatus}
        onUpdateStepStatus={handleUpdateStepStatus}
      />

      <ArtifactPanel
        artifact={artifact}
        visible={artifactVisible}
        fullscreen={artifactFullscreen}
        onToggleVisible={() => setArtifactVisible((value) => !value)}
        onToggleFullscreen={() => setArtifactFullscreen((value) => !value)}
      />

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

function playThumbnailReadySound() {
  try {
    const AudioContextClass = window.AudioContext;
    const audio = new AudioContextClass();
    const gain = audio.createGain();
    const osc = audio.createOscillator();

    osc.type = "sine";
    osc.frequency.setValueAtTime(880, audio.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, audio.currentTime + 0.08);
    gain.gain.setValueAtTime(0.0001, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.035, audio.currentTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + 0.13);

    osc.connect(gain);
    gain.connect(audio.destination);
    osc.start();
    osc.stop(audio.currentTime + 0.14);
    window.setTimeout(() => void audio.close(), 220);
  } catch {
    // Audio cues are optional; ignore browsers that block short sounds.
  }
}
