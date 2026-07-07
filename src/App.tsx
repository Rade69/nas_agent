import { useEffect, useRef, useState } from "react";
import { MonitorCog } from "lucide-react";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { ArtifactPanel } from "./components/ArtifactPanel";
import { ConfirmationDialog } from "./components/ConfirmationDialog";
import { PlansPanel } from "./components/PlansPanel";
import { RickyOrb } from "./components/RickyOrb";
import { Sidebar } from "./components/Sidebar";
import { voiceStateLabel } from "./lib/voiceState";
import { categoryForActivity } from "./lib/activityIcons";
import IconMic from "../assets/brending/icons/voice/icon-microphone.svg?react";
import IconMicOff from "../assets/brending/icons/voice/icon-microphone-muted.svg?react";
import IconStop from "../assets/brending/icons/voice/icon-stop.svg?react";
import IconSend from "../assets/brending/icons/voice/icon-send.svg?react";
import IconClose from "../assets/brending/icons/window/icon-close.svg?react";
import IconCompanion from "../assets/brending/icons/system/icon-realtime.svg?react";
import IconCalendar from "../assets/brending/icons/actions/icon-calendar.svg?react";
import IconSettings from "../assets/brending/icons/navigation/icon-settings.svg?react";
import IconChevron from "../assets/brending/icons/ui/icon-chevron-right.svg?react";
import IconLogoR from "../assets/brending/logo/ricky-logo-r.svg?react";
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
import type { BackendEvent } from "./vite-env";

type RickyMode = "display" | "computer";

export default function App() {
  const [connectionState, setConnectionState] = useState<RickyConnectionState>("idle");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [mood, setMood] = useState<RickyMood>("idle");
  const [mode, setMode] = useState<RickyMode>("display");
  const [artifact, setArtifact] = useState<RickyArtifact | null>(null);
  const [artifactVisible, setArtifactVisible] = useState(false);
  const [artifactFullscreen, setArtifactFullscreen] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const [mouthShape, setMouthShape] = useState<MouthShape>({ open: 0, width: 0.18, round: 0, teeth: 0 });
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([
    newEntry("system", "Ricky is ready. Connect voice, then talk naturally."),
  ]);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([
    createActivityEvent("status", "Renderer ready", "Voice-first shell loaded."),
  ]);
  const [status, setStatus] = useState("Idle");
  const [textPrompt, setTextPrompt] = useState("");
  const [pendingConfirmation, setPendingConfirmation] = useState<Confirmation | null>(null);
  const [confirmationBusy, setConfirmationBusy] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [busyStepId, setBusyStepId] = useState<string | null>(null);

  // UI redesign: state-machine screen (mockup principle "Jedan sadržaj po
  // ekranu") separate from an overlay drawer (mockup principle "Paneli
  // dostupni po potrebi (drawers)" — Activity/Plans/etc. float over the
  // current screen instead of replacing it; see GUI-SET-4/5.png).
  const [screen, setScreen] = useState<"home" | "dictation">("home");
  const [activeDrawer, setActiveDrawer] = useState<
    "activity" | "plans" | "memory" | "screens" | "settings" | null
  >(null);
  const [dictationText, setDictationText] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const clientRef = useRef<RickyRealtimeClient | null>(null);

  const isConnected = connectionState === "connected";

  // isActive: any state where the user might need to Stop
  const isActive = voiceState === "listening" || voiceState === "transcribing" ||
    voiceState === "thinking" || voiceState === "speaking" ||
    voiceState === "waiting_confirmation";

  // FAZA 9: drive VoiceState into waiting_confirmation while a pending
  // confirmation is visible.
  useEffect(() => {
    if (pendingConfirmation && pendingConfirmation.status === "pending") {
      setVoiceState("waiting_confirmation");
    }
  }, [pendingConfirmation]);

  // Consolidated poller: confirmations + events + backend health
  useEffect(() => {
    let cancelled = false;
    let cursor: string | null = null;
    // The very first /events call has no `since` cursor, so the backend
    // returns the most recent persisted events (app/api/events.py
    // service.recent()) — this can include an artifact.created/backend.ready
    // event from hours-old test sessions, not this run. Replay them silently
    // (just advance the cursor) instead of re-opening old artifacts / adding
    // duplicate "Backend ready" entries on every fresh launch.
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
      } catch { /* silent */ }
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
            if (replayingHistory) continue; // stale artifact from a past session — don't reopen it
            const artifactId = event.details?.artifact_id;
            if (typeof artifactId === "string") {
              try {
                const result = await window.ricky.executeTool({ name: "artifact_get", arguments: { id: artifactId } });
                if ((result as Record<string, unknown>).artifact) {
                  setArtifact((result as Record<string, unknown>).artifact as RickyArtifact);
                  setArtifactVisible(true);
                }
              } catch { /* ignore */ }
            }
          } else if (event.type === "tool.completed" || event.type === "tool.failed") {
            if (replayingHistory) continue;
            addActivityEvent(createActivityEvent("tool", event.title || event.type, event.type));
          } else if (event.type === "backend.ready") {
            setBackendConnected(true);
            if (replayingHistory) continue; // one of these per past restart today — not a new event
            addActivityEvent(createActivityEvent("status", "Backend ready", "Python backend connected"));
          }
        }
      } catch { /* silent */ }
    }

    async function pollHealth() {
      try {
        await window.ricky.listEvents();
        setBackendConnected(true);
      } catch { setBackendConnected(false); }
    }

    async function pollAll() {
      await Promise.allSettled([refreshPending(), pollEvents(), pollHealth()]);
    }

    pollAll();
    const interval = window.setInterval(pollAll, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // --- Voice state callbacks setup ---
  useEffect(() => {
    const client = new RickyRealtimeClient({
      onConnectionState: setConnectionState,
      onVoiceState: setVoiceState,
      onMood: setMood,
      onStatus: setStatus,
      onMouthShape: setMouthShape,
      onTranscript: (entry) => setTranscript((list) => [entry, ...list].slice(0, 200)),
      onArtifact: (next) => { setArtifact(next); setArtifactVisible(true); },
      onActivity: (event) => addActivityEvent(event),
      onMode: (next) => setMode(next as RickyMode),
      onThumbnailReady: () => {},
    });
    clientRef.current = client;
    return () => { client.disconnect(); };
  }, []);

  // --- Helpers ---
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

  function sendTextPrompt() {
    if (!textPrompt.trim()) return;
    clientRef.current?.sendText(textPrompt.trim());
    setTextPrompt("");
  }

  async function switchMode(nextMode: RickyMode) {
    const result = await window.ricky.executeTool({ name: "set_mode", arguments: { mode: nextMode } });
    if ((result as Record<string, unknown>).artifact) {
      setArtifact((result as Record<string, unknown>).artifact as RickyArtifact);
      setArtifactVisible(true);
    }
  }

  async function refreshPlans() {
    try {
      const response = await window.ricky.listPlans();
      setPlans(response?.plans ?? []);
    } catch { /* silent */ }
  }

  // Bug fix: refreshPlans() existed but was never called anywhere, so the
  // Planovi drawer always showed an empty list regardless of backend state.
  useEffect(() => {
    if (activeDrawer === "plans") void refreshPlans();
  }, [activeDrawer]);

  async function handleCreatePlan() {
    try {
      const created = await window.ricky.createPlan({ title: "Novi plan" });
      if (created) setPlans((list) => [created, ...list]);
    } catch { /* silent */ }
  }

  // --- Confirmation handlers (FAZA 9 + confirmation bridge) ---
  async function handleApproveConfirmation(confirmationId: string) {
    setConfirmationBusy(true);
    try {
      const result = await window.ricky.approveConfirmation(confirmationId);
      const approved = result?.confirmation ?? null;
      setPendingConfirmation(approved);
      addActivityEvent(createActivityEvent("status", "Confirmation approved", `Approved ${confirmationId}`));
      if (approved && approved.tool_name) {
        try {
          const retryResult = await window.ricky.executeTool({
            name: approved.tool_name,
            arguments: approved.payload || {},
            context: { confirmation_id: confirmationId, computer_mode: true },
          } as { name: string; arguments: Record<string, unknown>; context: Record<string, unknown> });
          const retryResultObj = retryResult as Record<string, unknown>;
          if (retryResultObj.ok === false) {
            // Report the real outcome — e.g. the active window changed to a
            // blocked app while the user was still looking at the dialog.
            // Silently logging "Retried" here would tell the user an action
            // happened when it actually didn't.
            addActivityEvent(
              createActivityEvent(
                "error",
                `Retry of ${approved.tool_name} was blocked`,
                typeof retryResultObj.error === "string" ? retryResultObj.error : "Tool execution failed after approval.",
              ),
            );
          } else {
            if (retryResultObj.artifact) {
              setArtifact(retryResultObj.artifact as Parameters<typeof setArtifact>[0]);
              setArtifactVisible(true);
            }
            addActivityEvent(createActivityEvent("tool", `Retried ${approved.tool_name}`, `Approved re-execution of ${confirmationId}`));
          }
        } catch (retryErr) {
          addActivityEvent(createActivityEvent("error", "Retry failed", retryErr instanceof Error ? retryErr.message : String(retryErr)));
        }
      }
    } catch (error) {
      addActivityEvent(createActivityEvent("error", "Approval failed", error instanceof Error ? error.message : String(error)));
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
      addActivityEvent(createActivityEvent("status", "Confirmation rejected", `Rejected ${confirmationId}`));
    } catch (error) {
      addActivityEvent(createActivityEvent("error", "Rejection failed", error instanceof Error ? error.message : String(error)));
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
      if (result) {
        setPlans((list) => list.map((p) => (p.id === planId ? result : p)));
      }
    } catch { /* silent */ }
    setBusyPlanId(null);
  }

  async function handleUpdateStepStatus(planId: string, stepId: string, status: string) {
    setBusyStepId(stepId);
    try {
      const result = await window.ricky.updatePlanStep(planId, stepId, { status: status as PlanStepStatus });
      if (result) {
        setPlans((list) => list.map((p) => (p.id === planId ? result : p)));
      }
    } catch { /* silent */ }
    setBusyStepId(null);
  }

  // --- Stop handler ---
  function handleStop() {
    clientRef.current?.disconnect();
    setVoiceState("interrupted");
    addActivityEvent(createActivityEvent("status", "Stopped", "User pressed Stop"));
  }

  // --- Recent activity items (last 4, excluding raw system events) ---
  // Bug fix: this used to check `a.detail` for "Backend ready"/"Renderer ready",
  // but createActivityEvent("status", "Backend ready", "Python backend connected")
  // puts that text in `.title`, not `.detail` — so the filter never matched and
  // every historical "Backend ready" event (one per backend restart, replayed on
  // every fresh app launch — see pollEvents()) showed up as noise.
  const SYSTEM_NOISE_TITLES = ["Backend ready", "Renderer ready", "Voice-first shell"];
  const recentActivity = activityEvents
    .filter((a) => a.kind !== "status" || !SYSTEM_NOISE_TITLES.some((noise) => a.title.includes(noise)))
    .slice(0, 4);

  // --- Render: Idle / Ready screen ---
  function renderIdleScreen() {
    return (
      <div className="idle-screen">
        <div className="idle-center">
          <RickyOrb voiceState={voiceState} />
          <div className="idle-headline">Ricky je spreman</div>
          <div className="idle-subtitle">Klikni mikrofon ili reci "Ricky"</div>
          {isActive ? (
            <button className="idle-cta stop" onClick={handleStop} title="Stop">
              <IconStop className="idle-cta-icon" />
            </button>
          ) : (
            <button
              className="idle-cta"
              onClick={isConnected ? disconnect : () => void connect()}
              title={isConnected ? "Prekini vezu" : "Pokreni glas"}
            >
              {isConnected ? <IconMicOff className="idle-cta-icon" /> : <IconMic className="idle-cta-icon" />}
            </button>
          )}
        </div>
        <div className="idle-right">
          <div className="idle-card">
            <div className="idle-card-head">
              <h4>Zadnja aktivnost</h4>
              {recentActivity.length ? (
                <button className="idle-card-link" onClick={() => setActiveDrawer("activity")}>
                  Prikaži sve
                </button>
              ) : null}
            </div>
            <ul className="idle-activity-list">
              {recentActivity.length ? recentActivity.map((a, i) => {
                const { Icon, className } = categoryForActivity(a);
                return (
                  <li key={i} className="idle-activity-item">
                    <span className={`activity-icon activity-icon-sm ${className}`}>
                      <Icon className="activity-icon-svg" />
                    </span>
                    <div className="idle-activity-body">
                      <span className="idle-activity-text">{a.title || a.detail}</span>
                      {a.title && a.detail ? (
                        <span className="idle-activity-sub">{a.detail}</span>
                      ) : null}
                    </div>
                    <time className="idle-activity-time">{a.at}</time>
                  </li>
                );
              }) : <li className="idle-empty">Još nema aktivnosti.</li>}
            </ul>
          </div>
          <div className="idle-card">
            <div className="idle-card-head">
              <h4>Brze komande</h4>
            </div>
            <ul>
              <li className="cmd" onClick={() => sendText("Napiši email šefu")}>
                <IconChevron className="cmd-icon" /> Napiši email šefu
              </li>
              <li className="cmd" onClick={() => sendText("Napravi screenshot")}>
                <IconChevron className="cmd-icon" /> Napravi screenshot
              </li>
              <li className="cmd" onClick={() => sendText("Otvori Notepad")}>
                <IconChevron className="cmd-icon" /> Otvori Notepad
              </li>
              <li className="cmd" onClick={() => sendText("Planiraj sastanak sutra u 10h")}>
                <IconChevron className="cmd-icon" /> Planiraj sastanak sutra u 10h
              </li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // --- Render: Dictation screen ---
  function renderDictationScreen() {
    return (
      <div className="dictation-screen">
        <div className="dictation-header">
          <h3>Diktiranje</h3>
          <span className="dictation-badge">DICTATION MODE</span>
        </div>
        <textarea
          className="dictation-editor"
          value={dictationText}
          onChange={(e) => setDictationText(e.target.value)}
          placeholder="Tekst diktata će se pojaviti ovdje..."
        />
        <div className="dictation-actions">
          <button className="btn-secondary" onClick={() => setScreen("home")}>
            Zatvori
          </button>
          <div className="spacer" />
          <button className="btn-secondary" onClick={() => setDictationText("")}>Obriši</button>
          <button className="btn-primary" onClick={() => {
            if (dictationText.trim()) sendText(dictationText.trim());
            setScreen("home");
          }}>Pošalji agentu</button>
        </div>
      </div>
    );
  }

  function sendText(text: string) {
    clientRef.current?.sendText(text);
  }

  // --- Render: persistent state-machine screen (Idle or Dictation) ---
  function renderScreen() {
    return screen === "dictation" ? renderDictationScreen() : renderIdleScreen();
  }

  // --- Drawer: overlay panel floating over the current screen; see
  // GUI-SET-4.png (Activity Drawer) / GUI-SET-5.png (Plans Drawer) ---
  const DRAWER_TITLE: Record<string, string> = {
    activity: "Aktivnost",
    plans: "Planovi",
    memory: "Memorija",
    screens: "Snimci ekrana",
    settings: "Postavke",
  };

  function renderDrawerContent() {
    switch (activeDrawer) {
      case "activity":
        return <ActivityTimeline transcript={transcript} activityEvents={activityEvents} />;
      case "plans":
        return (
          <PlansPanel
            visible={true}
            plans={plans}
            busyPlanId={busyPlanId}
            busyStepId={busyStepId}
            onUpdatePlanStatus={handleUpdatePlanStatus}
            onUpdateStepStatus={handleUpdateStepStatus}
            onCreatePlan={handleCreatePlan}
          />
        );
      case "memory":
        return <p className="drawer-placeholder-text">Notes and records will appear here.</p>;
      case "screens":
        return <p className="drawer-placeholder-text">Screenshots will appear here.</p>;
      case "settings":
        return <p className="drawer-placeholder-text">Settings panel — coming soon.</p>;
      default:
        return null;
    }
  }

  // --- Main render ---
  return (
    <main className="app-shell-redesign">
      <div className="window-drag-strip" aria-hidden="true" />

      {/* ---- TOP BAR ---- */}
      <header className="top-bar">
        <IconLogoR className="top-bar-logo" />
        <span className="top-bar-brand">Ricky</span>
        <div className={`voice-state-pill voice-state-${voiceState}`}>
          <span className="dot" />
          <span>{voiceStateLabel(voiceState)}</span>
        </div>
        <div className="top-bar-spacer" />
        <button
          className={`computer-mode-pill ${mode === "computer" ? "on" : "off"}`}
          onClick={() => switchMode(mode === "computer" ? "display" : "computer")}
        >
          <MonitorCog size={14} />
          <span>{mode === "computer" ? "Computer mode: UKLJUČEN" : "Computer mode: ISKLJUČEN"}</span>
        </button>
        <div className="top-bar-controls">
          <button className="top-bar-btn" onClick={() => void window.ricky.companionToggle?.()} title="Companion orb">
            <IconCompanion className="top-bar-btn-icon" />
          </button>
          <button className="top-bar-btn" onClick={() => setActiveDrawer("plans")} title="Planovi">
            <IconCalendar className="top-bar-btn-icon" />
          </button>
          <button className="top-bar-btn" onClick={() => setActiveDrawer("settings")} title="Postavke">
            <IconSettings className="top-bar-btn-icon" />
          </button>
          <button className="top-bar-btn close" onClick={() => void window.ricky.quitApp()} title="Close">
            <IconClose className="top-bar-btn-icon" />
          </button>
        </div>
      </header>

      {/* ---- SIDEBAR ---- */}
      <Sidebar activeTab={activeDrawer ?? screen} onTabChange={(id) => {
        if (id === "home") { setScreen("home"); setActiveDrawer(null); }
        else setActiveDrawer(id as typeof activeDrawer);
      }} backendConnected={backendConnected} />

      {/* ---- MAIN CONTENT ---- */}
      <div className="main-content">
        {renderScreen()}

        {/* Bottom voice bar — only on the Idle screen; Dictation Mode has its own actions bar */}
        {screen === "home" && (
          <footer className="bottom-voice-bar">
            <span className="bottom-voice-status-text">
              <span className={`voice-state-dot voice-state-dot-${voiceState}`} style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", marginRight: 5 }} />
              {voiceStateLabel(voiceState)}
            </span>
            <div className="bottom-voice-input">
              <input
                value={textPrompt}
                onChange={(e) => setTextPrompt(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") sendTextPrompt(); }}
                placeholder="Upiši umjesto govora..."
              />
              <button className="btn-primary" style={{ padding: "7px 14px", fontSize: 13 }} onClick={sendTextPrompt} title="Pošalji">
                <IconSend style={{ width: 14, height: 14 }} />
              </button>
            </div>
            {isActive && (
              <button className="btn-danger" onClick={handleStop}>
                <IconStop style={{ width: 14, height: 14 }} /> Stop
              </button>
            )}
          </footer>
        )}

        {/* ---- DRAWER OVERLAY (Activity/Plans/Memory/Snimci/Postavke) ---- */}
        {activeDrawer && (
          <div className="drawer-backdrop" onClick={() => setActiveDrawer(null)}>
            <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
              <header className="drawer-header">
                <strong>{DRAWER_TITLE[activeDrawer]}</strong>
                <button className="drawer-close" onClick={() => setActiveDrawer(null)} aria-label="Zatvori">
                  <IconClose className="drawer-close-icon" />
                </button>
              </header>
              <div className="drawer-body">{renderDrawerContent()}</div>
            </div>
          </div>
        )}
      </div>

      {/* ---- ARTIFACT PANEL ---- */}
      {artifactVisible && artifact && (
        <ArtifactPanel
          artifact={artifact}
          visible={artifactVisible}
          fullscreen={artifactFullscreen}
          onToggleVisible={() => setArtifactVisible((v) => !v)}
          onToggleFullscreen={() => setArtifactFullscreen((v) => !v)}
        />
      )}

      {/* ---- CONFIRMATION DIALOG ---- */}
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