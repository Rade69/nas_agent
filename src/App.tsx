import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { ConfirmationDialog } from "./components/ConfirmationDialog";
import { PlansPanel } from "./components/PlansPanel";
import { RickyOrb } from "./components/RickyOrb";
import { Sidebar } from "./components/Sidebar";
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

type RickyMode = "display" | "computer";
type ScreenState = "home" | "dictation";
type DrawerState = "activity" | "plans" | "memory" | "screens" | "settings" | null;

const SYSTEM_NOISE_TITLES = ["Backend ready", "Renderer ready", "Voice-first shell", "Backend spreman", "Renderer spreman"];

function getInitialMode(): RickyMode {
  const params = new URLSearchParams(window.location.search);
  return params.get("mode") === "computer" ? "computer" : "display";
}

function isMiniWindow() {
  return new URLSearchParams(window.location.search).get("window") === "mini";
}

function debugRenderer(label: string, payload: Record<string, unknown> = {}) {
  const snapshot = {
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    visibility: document.visibilityState,
    focused: document.hasFocus(),
    activeElement: document.activeElement?.tagName || null,
  };
  void window.ricky.debugLog(label, { ...snapshot, ...payload });
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
  const switchModeStartedAtRef = useRef<number | null>(null);

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
    debugRenderer("app:mode-state", { mode, artifactVisible, artifactKind: artifact?.kind || null });
  }, [artifact?.kind, artifactVisible, mode]);

  useEffect(() => {
    const logWindowEvent = (eventName: string) => {
      debugRenderer(`window:${eventName}`, {
        mode,
        artifactVisible,
        scrollX: window.scrollX,
        scrollY: window.scrollY,
      });
    };
    const onFocus = () => logWindowEvent("focus");
    const onBlur = () => logWindowEvent("blur");
    const onResize = () => logWindowEvent("resize");
    const onVisibilityChange = () => logWindowEvent(`visibility:${document.visibilityState}`);
    const onPageShow = () => logWindowEvent("pageshow");

    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);
    window.addEventListener("resize", onResize);
    window.addEventListener("pageshow", onPageShow);
    document.addEventListener("visibilitychange", onVisibilityChange);
    debugRenderer("app:debug-attached", { mode, artifactVisible });
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pageshow", onPageShow);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [artifactVisible, mode]);

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
    switchModeStartedAtRef.current = performance.now();
    const traceId = `mode-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    debugRenderer("switchMode:start", {
      traceId,
      currentMode: mode,
      nextMode,
      artifactVisible,
      artifactKind: artifact?.kind || null,
    });
    try {
      const result = await window.ricky.executeTool({ name: "set_mode", arguments: { mode: nextMode, __modeTraceId: traceId } });
      const resultObj = result as Record<string, unknown>;
      debugRenderer("switchMode:result", {
        traceId,
        currentMode: mode,
        nextMode,
        resultMode: resultObj.mode || null,
        hasArtifact: Boolean(resultObj.artifact),
        ok: resultObj.ok,
        elapsedMs: switchModeStartedAtRef.current ? Math.round(performance.now() - switchModeStartedAtRef.current) : null,
      });
      setMode(nextMode);
      if (resultObj.mode === "display") setArtifactVisible(false);
      debugRenderer("switchMode:set-state", { traceId, nextMode, closeArtifact: resultObj.mode === "display" });
    } catch (error) {
      debugRenderer("switchMode:error", {
        traceId,
        currentMode: mode,
        nextMode,
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
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
          debugRenderer("mini-restore-button:click", { currentMode: mode, nextMode: "display" });
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
          debugRenderer("mode-button:click", { currentMode: mode, nextMode, artifactVisible, note: "traceId is created in switchMode:start" });
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

function MiniComputerWindow({
  voiceState,
  onRestore,
}: {
  voiceState: VoiceState;
  onRestore: () => void;
}) {
  const stateLabel = "UKLJUČEN";
  const isTalking = voiceState === "speaking" || voiceState === "listening" || voiceState === "thinking" || voiceState === "transcribing";
  return (
    <main className={`mini-computer-window ${isTalking ? "is-talking" : "is-idle"}`}>
      <button className="mini-avatar-restore" onClick={onRestore} title="Vrati glavni prozor">
        Vrati
      </button>
      <div className="mini-avatar-stage" aria-label={`Računarski režim ${stateLabel}`}>
        <img src={rikiAvatar} alt="Ricky avatar" draggable={false} />
      </div>
      <div className="mini-avatar-status">
        <span>Računarski režim</span>
        <strong>{stateLabel}</strong>
      </div>
    </main>
  );
}

function PixelMockupBoard({
  mode,
  screen,
  voiceState,
  isActive,
  isConnected,
  textPrompt,
  dictationText,
  recentActivity,
  activityEvents,
  transcript,
  plans,
  activeDrawer,
  backendConnected,
  busyPlanId,
  busyStepId,
  onToggleMode,
  onOpenPlans,
  onSidebarChange,
  onTextPromptChange,
  onSendTextPrompt,
  onVoiceToggle,
  onStop,
  onOpenActivity,
  onQuickCommand,
  onDictationChange,
  onDictationCancel,
  onDictationSend,
  onStopAll,
  onCloseDrawer,
  onUpdatePlanStatus,
  onUpdateStepStatus,
  onCreatePlan,
}: {
  mode: RickyMode;
  screen: ScreenState;
  voiceState: VoiceState;
  isActive: boolean;
  isConnected: boolean;
  textPrompt: string;
  dictationText: string;
  recentActivity: ActivityEvent[];
  activityEvents: ActivityEvent[];
  transcript: TranscriptEntry[];
  plans: Plan[];
  activeDrawer: DrawerState;
  backendConnected: boolean;
  busyPlanId: string | null;
  busyStepId: string | null;
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onSidebarChange: (id: string) => void;
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
  onDictationChange: (value: string) => void;
  onDictationCancel: () => void;
  onDictationSend: () => void;
  onStopAll: () => void;
  onCloseDrawer: () => void;
  onUpdatePlanStatus: (planId: string, status: string) => Promise<void>;
  onUpdateStepStatus: (planId: string, stepId: string, status: string) => Promise<void>;
  onCreatePlan: () => Promise<void>;
}) {
  return (
    <div className="pixel-mockup-board">
      <MockupSection
        className="pixel-section-idle"
        number="1"
        title="SPREMAN"
        description="Mirno stanje. Fokus na mikrofon i zadnju aktivnost. Sve ostalo dostupno po potrebi."
      >
        <section className="pixel-window pixel-window-idle" aria-label="Spreman">
          <TopBar
            mode={mode}
            screen={screen}
            voiceState={voiceState}
            onToggleMode={onToggleMode}
            onOpenPlans={onOpenPlans}
            onStopAll={onStopAll}
          />
          <Sidebar activeTab={activeDrawer ?? screen} onTabChange={onSidebarChange} backendConnected={backendConnected} />
          <section className="pixel-main">
            <IdleScreen
              voiceState={voiceState}
              isActive={isActive}
              isConnected={isConnected}
              textPrompt={textPrompt}
              recentActivity={recentActivity}
              onTextPromptChange={onTextPromptChange}
              onSendTextPrompt={onSendTextPrompt}
              onVoiceToggle={onVoiceToggle}
              onStop={onStop}
              onOpenActivity={onOpenActivity}
              onQuickCommand={onQuickCommand}
            />
            {activeDrawer ? (
              <Drawer drawer={activeDrawer} onClose={onCloseDrawer}>
                {activeDrawer === "activity" ? (
                  <ActivityTimeline transcript={transcript} activityEvents={activityEvents} />
                ) : null}
                {activeDrawer === "plans" ? (
                  <PlansPanel
                    visible={true}
                    plans={plans}
                    busyPlanId={busyPlanId}
                    busyStepId={busyStepId}
                    onUpdatePlanStatus={onUpdatePlanStatus}
                    onUpdateStepStatus={onUpdateStepStatus}
                    onCreatePlan={onCreatePlan}
                  />
                ) : null}
                {activeDrawer === "memory" ? <p className="drawer-placeholder-text">Nema sačuvane memorije.</p> : null}
                {activeDrawer === "screens" ? <p className="drawer-placeholder-text">Nema snimaka ekrana.</p> : null}
                {activeDrawer === "settings" ? <p className="drawer-placeholder-text">Postavke nisu dostupne u ovom prikazu.</p> : null}
              </Drawer>
            ) : null}
          </section>
        </section>
      </MockupSection>

      <MockupSection
        className="pixel-section-dictation"
        number="2"
        title="DIKTIRANJE"
        description="Editor je u fokusu. Samo najvažnije akcije. Ostali paneli skriveni."
      >
        <section className="pixel-window pixel-window-dictation" aria-label="Diktiranje">
          <TopBar mode={mode} screen="dictation" voiceState={voiceState} onToggleMode={onToggleMode} onOpenPlans={onOpenPlans} />
          <section className="pixel-main pixel-main-full">
            <DictationScreen
              text={dictationText}
              onChange={onDictationChange}
              onCancel={onDictationCancel}
              onSend={onDictationSend}
            />
          </section>
        </section>
      </MockupSection>

      <MockupSection
        className="pixel-section-confirmation"
        number="3"
        title="POTVRDA"
        description="Dominantna potvrda. Ne može se previdjeti. Detalji jasni, rizik istaknut."
      >
        <ConfirmationPreview />
      </MockupSection>

      <MockupSection
        className="pixel-section-activity"
        number="4"
        title="AKTIVNOST"
        description="Detaljna historija svih događaja i akcija."
      >
        <ActivityDrawerPreview activityEvents={recentActivity} />
      </MockupSection>

      <MockupSection
        className="pixel-section-plans"
        number="5"
        title="PLANOVI"
        description="Tvoji planovi, zadaci i podsjetnici."
      >
        <PlansDrawerPreview plans={plans} />
      </MockupSection>

    </div>
  );
}

function MockupSection({
  number,
  title,
  description,
  className,
  children,
}: {
  number?: string;
  title?: string;
  description?: string;
  className: string;
  children: ReactNode;
}) {
  return (
    <section className={`pixel-mockup-section ${className}`}>
      {title ? (
        <header className="pixel-section-label">
          <h2>{number ? `${number}. ${title}` : title}</h2>
          {description ? <p>{description}</p> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}

function ConfirmationPreview() {
  return (
    <div className="pixel-confirmation-preview">
      <div className="pixel-blurred-shell" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <article className="pixel-confirm-card">
        <div className="pixel-warning-icon">
          <IconWarning />
        </div>
        <div className="pixel-confirm-content">
          <h3>Ricky želi izvršiti ovu akciju</h3>
          <p>Pažljivo provjeri detalje prije potvrde.</p>
          <dl className="pixel-confirm-table">
            <div>
              <dt>Akcija</dt>
              <dd>Pošalji email</dd>
            </div>
            <div>
              <dt>Prima</dt>
              <dd>sef@firma.com</dd>
            </div>
            <div>
              <dt>Predmet</dt>
              <dd>Izvještaj o prodaji za prošli mjesec</dd>
            </div>
            <div>
              <dt>Rizik</dt>
              <dd>
                <span className="pixel-risk-badge">SREDNJI</span>
                <span className="pixel-risk-time">ističe za 02:00</span>
              </dd>
            </div>
          </dl>
          <button className="pixel-confirm-link">
            Prikaži cijeli sadržaj emaila <IconChevronDown />
          </button>
          <footer>
            <button>Izmijeni</button>
            <button>Otkaži</button>
            <button className="pixel-confirm-primary">
              <IconSend /> Pošalji email
            </button>
          </footer>
        </div>
      </article>
    </div>
  );
}

function ActivityDrawerPreview({ activityEvents }: { activityEvents: ActivityEvent[] }) {
  return (
    <aside className="pixel-preview-drawer">
      <header>
        <strong>Aktivnost</strong>
      </header>
      <div className="pixel-preview-list">
        {activityEvents.length > 0 ? (
          activityEvents.slice(0, 5).map((event) => {
            const { Icon, className } = categoryForActivity(event);
            return (
              <article className="pixel-preview-row" key={event.id}>
                <span className={`pixel-preview-icon ${className}`}>
                  <Icon />
                </span>
                <span>
                  <strong>{event.title}</strong>
                  {event.detail ? <small>{event.detail}</small> : null}
                </span>
                <time>{event.at}</time>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title="Još nema aktivnosti" detail="Događaji će se pojaviti ovdje kada Ricky nešto uradi." />
        )}
      </div>
      <button className="pixel-full-history">Prikaži cijelu historiju</button>
    </aside>
  );
}

function PlansDrawerPreview({ plans }: { plans: Plan[] }) {
  return (
    <aside className="pixel-preview-drawer pixel-preview-plans">
      <header>
        <strong>Planovi</strong>
      </header>
      <div className="pixel-plan-tabs">
        <button className="active">Aktivni</button>
        <button>Predloženi</button>
        <button>Završeni</button>
      </div>
      <div className="pixel-preview-list">
        {plans.length > 0 ? (
          plans.slice(0, 4).map((plan) => {
            const status = planStatusLabel(plan.status);
            return (
              <article className="pixel-plan-row" key={plan.id}>
                <span className={`pixel-preview-icon ${plan.status === "completed" ? "success" : "voice"}`}>
                  {plan.status === "completed" ? <IconSuccess /> : <IconBackend />}
                </span>
                <span>
                  <strong>{plan.title}</strong>
                  <small>{plan.summary || `${plan.steps.length} koraka`}</small>
                </span>
                <em className={status.tone}>{status.label}</em>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title="Nema aktivnih planova" detail="Napravi novi plan kada želiš da Ricky prati zadatke." />
        )}
      </div>
      <button className="pixel-full-history">Novi plan</button>
    </aside>
  );
}

function EmptyPreviewState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="pixel-empty-preview">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

function planStatusLabel(status: Plan["status"]): { label: string; tone: "active" | "pending" } {
  switch (status) {
    case "approved":
    case "running":
      return { label: "AKTIVAN", tone: "active" };
    case "completed":
      return { label: "ZAVRŠEN", tone: "active" };
    case "rejected":
    case "cancelled":
      return { label: "OTKAZAN", tone: "pending" };
    case "draft":
      return { label: "NACRT", tone: "pending" };
    case "proposed":
    default:
      return { label: "NA ČEKANJU", tone: "pending" };
  }
}

function TopBar({
  mode,
  screen,
  voiceState,
  onToggleMode,
  onOpenPlans,
  onStopAll,
}: {
  mode: RickyMode;
  screen: ScreenState;
  voiceState: VoiceState;
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onStopAll?: () => void;
}) {
  return (
    <header className="pixel-top-bar">
      <div className="pixel-brand">
        <span className="pixel-brand-orb">
          <IconLogoR className="pixel-brand-logo" />
        </span>
        <strong>Ricky</strong>
        <span className={`pixel-state pixel-state-${voiceState}`}>
          {screen === "dictation" ? (
            <>
              <IconWave className="pixel-state-icon" />
              Diktiranje
            </>
          ) : (
            <>
              <span className="pixel-state-dot" />
              {voiceStateLabel(voiceState)}
            </>
          )}
        </span>
      </div>
      {onStopAll ? (
        <div className="pixel-top-actions">
          <button className="pixel-top-stop-all" onClick={onStopAll} title="Zaustavi sve aktivnosti">
            <IconStop />
            Stop sve
          </button>
          <button className={`pixel-mode-pill ${mode === "computer" ? "on" : ""}`} onClick={onToggleMode}>
            Računarski režim: {mode === "computer" ? "UKLJUČEN" : "ISKLJUČEN"}
          </button>
          <button className="pixel-icon-button" title="Glas">
            <IconWave />
          </button>
          <button className="pixel-icon-button" onClick={onOpenPlans} title="Planovi">
            <IconCalendar />
          </button>
        </div>
      ) : null}
    </header>
  );
}

function IdleScreen({
  voiceState,
  isActive,
  isConnected,
  textPrompt,
  recentActivity,
  onTextPromptChange,
  onSendTextPrompt,
  onVoiceToggle,
  onStop,
  onOpenActivity,
  onQuickCommand,
}: {
  voiceState: VoiceState;
  isActive: boolean;
  isConnected: boolean;
  textPrompt: string;
  recentActivity: ActivityEvent[];
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
}) {
  return (
    <div className="pixel-idle">
      <section className="pixel-hero">
        <RickyOrb voiceState={voiceState} />
        <h1>Ricky je spreman</h1>
        <p>Klikni mikrofon ili reci "Ricky"</p>
        <button
          className={`pixel-mic-button ${isActive ? "stop" : ""}`}
          onClick={isActive ? onStop : onVoiceToggle}
          title={isActive ? "Stop" : isConnected ? "Prekini vezu" : "Pokreni glas"}
        >
          {isActive ? <IconStop /> : isConnected ? <IconMicOff /> : <IconMic />}
        </button>
        <div className="pixel-prompt">
          <input
            value={textPrompt}
            onChange={(event) => onTextPromptChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSendTextPrompt();
            }}
            placeholder="Upiši umjesto govora..."
          />
          <button onClick={onSendTextPrompt} aria-label="Pošalji tekst">
            <IconSend />
          </button>
        </div>
      </section>
      <aside className="pixel-idle-side">
        <section className="pixel-card pixel-activity-card">
          <header>
            <h2>Zadnja aktivnost</h2>
            <button onClick={onOpenActivity}>Prikaži sve</button>
          </header>
          <div className="pixel-list">
            {recentActivity.length > 0 ? (
              recentActivity.slice(0, 4).map((event) => {
                const { Icon, className } = categoryForActivity(event);
                return (
                  <article className="pixel-list-row" key={event.id}>
                    <span className={`pixel-row-icon ${className}`}>
                      <Icon />
                    </span>
                    <span>
                      <strong>{event.title}</strong>
                      {event.detail ? <small>{event.detail}</small> : null}
                    </span>
                    <time>{event.at}</time>
                  </article>
                );
              })
            ) : (
              <EmptyPreviewState title="Nema aktivnosti" detail="Historija će se popuniti kada pokreneš glas ili alat." />
            )}
          </div>
        </section>
        <section className="pixel-card pixel-command-card">
          <header>
            <h2>Brze komande</h2>
          </header>
          <button onClick={() => onQuickCommand("Napiši email šefu")}>
            <IconChevronRight /> Napiši email šefu
          </button>
          <button onClick={() => onQuickCommand("Napravi screenshot")}>
            <IconScreenshot /> Napravi screenshot
          </button>
          <button onClick={() => onQuickCommand("Otvori Notepad")}>
            <IconOpenApp /> Otvori Notepad
          </button>
          <button onClick={() => onQuickCommand("Planiraj sastanak sutra u 10h")}>
            <IconCalendar /> Planiraj sastanak sutra u 10h
          </button>
        </section>
      </aside>
    </div>
  );
}

function DictationScreen({
  text,
  onChange,
  onCancel,
  onSend,
}: {
  text: string;
  onChange: (value: string) => void;
  onCancel: () => void;
  onSend: () => void;
}) {
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <section className="pixel-dictation">
      <header className="pixel-dictation-head">
        <div>
          <span className="pixel-dictation-badge">DIKTIRANJE</span>
          <span className="pixel-autosave">
            <span />
            auto-čuvanje uključeno
          </span>
        </div>
        <button onClick={onCancel}>
          Otkaži diktiranje
        </button>
      </header>
      <div className="pixel-editor-wrap">
        <textarea
          value={text}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Diktirani tekst će se pojaviti ovdje..."
        />
        <span className="pixel-word-count">{wordCount} riječi</span>
      </div>
      <footer className="pixel-dictation-actions">
        <button className="pixel-secondary">
          <IconMic /> Nastavi diktiranje
        </button>
        <div className="pixel-dropdown">
          <button className="pixel-secondary">
            Doradi <IconChevronDown />
          </button>
          <div className="pixel-dropdown-menu">
            <button>Formalizuj</button>
            <button>Skrati</button>
            <button>Provjeri pravopis</button>
            <button>Prevedi na engleski</button>
          </div>
        </div>
        <button className="pixel-secondary">...</button>
        <span className="pixel-action-spacer" />
        <button className="pixel-primary" onClick={onSend}>
          <IconSend /> Pošalji agentu
        </button>
      </footer>
    </section>
  );
}

function Drawer({
  drawer,
  onClose,
  children,
}: {
  drawer: Exclude<DrawerState, null>;
  onClose: () => void;
  children: ReactNode;
}) {
  const titles: Record<Exclude<DrawerState, null>, string> = {
    activity: "Aktivnost",
    plans: "Planovi",
    memory: "Memorija",
    screens: "Snimci ekrana",
    settings: "Postavke",
  };

  return (
    <div className="pixel-drawer-backdrop" onClick={onClose}>
      <aside className={`pixel-drawer pixel-drawer-${drawer}`} onClick={(event) => event.stopPropagation()}>
        <header>
          <strong>{titles[drawer]}</strong>
          <button onClick={onClose} aria-label="Zatvori">
            <IconClose />
          </button>
        </header>
        <div className="pixel-drawer-body">{children}</div>
      </aside>
    </div>
  );
}
