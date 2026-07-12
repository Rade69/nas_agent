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
import { cyrillicToLatin } from "./lib/cyrillicToLatin";
import i18n from "./i18n";
import type { BackendEvent, Confirmation, Plan, PlanStepStatus, RickyArtifact, TextRewriteOperation } from "./vite-env";

import type { RickyMode, ScreenState, DrawerState } from "./components/pixel/types";

const SYSTEM_NOISE_TITLES = ["Backend ready", "Renderer ready", "Voice-first shell", "Backend spreman", "Renderer spreman"];

// Voice exit phrases for Dictation Mode (agent_reports/2026-07-11_dictation-guardrails-and-exit.md).
// Deliberately multi-word and distinctive — a single common word (e.g. "gotovo")
// would false-positive on ordinary dictated sentences that happen to contain it.
// Checked on the (already Cyrillic->Latin normalized) transcript, mirroring the
// entry-trigger check but in reverse.
// Now keyed by interface_language (agent_reports/2026-07-11_interface-language-stt-hint.md)
// so the voice exit works in every supported language. en/de/es/fr phrases are
// best-effort — NOT native-speaker verified (agent_reports/2026-07-11_dictation-language-cascade.md).
const DICTATION_EXIT_PHRASES: Record<string, string[]> = {
  "sr-Latn": [
    "vrati se u normalan",
    "vrati u normalan",
    "izađi iz diktat",
    "izadji iz diktat",
    "prekini diktat",
    "završi diktiranje",
    "zavrsi diktiranje",
  ],
  en: [
    "go back to normal",
    "exit dictation",
    "stop dictating",
    "end dictation",
  ],
  de: [
    "zurück zum normalen modus",
    "diktat beenden",
    "diktat verlassen",
  ],
  es: [
    "volver al modo normal",
    "salir del dictado",
    "terminar el dictado",
  ],
  fr: [
    "retour au mode normal",
    "quitter la dictée",
    "arrêter la dictée",
  ],
};
const DEFAULT_DICTATION_EXIT_PHRASES = DICTATION_EXIT_PHRASES["sr-Latn"];

// Voice trigger words for entering Dictation Mode (agent_reports/2026-07-10_dictation-and-dashboard-fixes.md).
// Keyed by interface_language — a substring match on the user's spoken utterance
// (after Cyrillic->Latin normalization). en/de/es/fr triggers are best-effort —
// NOT native-speaker verified (agent_reports/2026-07-11_dictation-language-cascade.md).
const DICTATION_TRIGGER_WORDS: Record<string, string> = {
  "sr-Latn": "dikt",
  en: "dictat",
  de: "diktier",
  es: "dict",
  fr: "dict",
};
const DEFAULT_DICTATION_TRIGGER_WORD = "dikt";

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
  // Mirrors `screen` for the onTranscript callback below, which is captured
  // once in a mount-only useEffect (empty deps) and would otherwise read a
  // stale "home" value forever instead of the current screen.
  const screenRef = useRef<ScreenState>(screen);
  useEffect(() => {
    screenRef.current = screen;
  }, [screen]);
  // interface_language for dictation trigger/exit phrases (Deo A,
  // agent_reports/2026-07-11_dictation-language-cascade.md). Same mirroring
  // pattern as screenRef — the mount-only useEffect below that captures
  // onTranscript would otherwise read a stale "sr-Latn" forever.
  const [interfaceLanguage, setInterfaceLanguage] = useState("sr-Latn");
  const interfaceLanguageRef = useRef(interfaceLanguage);
  useEffect(() => {
    interfaceLanguageRef.current = interfaceLanguage;
  }, [interfaceLanguage]);
  // Fetch interface_language once at mount so dictation trigger/exit phrases
  // match the user's chosen language. Fail-open: if the fetch fails, stays
  // on default "sr-Latn" — same principle as user_name in realtime.cjs. Also
  // applies the same value to i18next so the GUI text (Sidebar/TopBar/voice
  // state labels) matches on load, not just the dictation cascade.
  // Context: agent_reports/2026-07-11_i18n-foundation.md
  useEffect(() => {
    window.ricky
      .getSettings()
      .then((s) => {
        setInterfaceLanguage(s.interface_language);
        void i18n.changeLanguage(s.interface_language);
      })
      .catch(() => {});
  }, []);
  const [activeDrawer, setActiveDrawer] = useState<DrawerState>(null);
  const [killFlash, setKillFlash] = useState(false);
  const [dictationText, setDictationText] = useState("");
  const [dictationBusy, setDictationBusy] = useState(false);
  const [canUndoDictation, setCanUndoDictation] = useState(false);
  // Single-level undo: holds the text as it was immediately before the last
  // destructive Dictation action (a "Doradi" rewrite or "Obriši sve").
  // Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
  const dictationUndoRef = useRef<string | null>(null);
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
        // This call already doubles as the backend health check (the
        // previous separate pollHealth() made an identical, redundant
        // listEvents() request every 3s just to check connectivity — three
        // HTTP requests per poll cycle instead of two).
        setBackendConnected(true);
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
            if (replayingHistory) continue;
            addActivityEvent(createActivityEvent("status", "Backend spreman", "Python backend povezan"));
          }
        }
      } catch {
        if (!cancelled) setBackendConnected(false);
      }
    }

    async function pollAll() {
      await Promise.allSettled([refreshPending(), pollEvents()]);
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
      onTranscript: (entry) => {
        // Debug logging (agent_reports/2026-07-10_dictation-debug-logging.md)
        // proved the Realtime API's transcription sometimes returns Serbian
        // speech in Cyrillic mid-session (this project standardizes on
        // sr-Latn) — that silently broke the "dikt" substring check below
        // (Cyrillic "диктат" never matches Latin "dikt") and caused mixed-
        // script dictated text. Normalize once here for both uses. Only
        // applied to user speech (STT output) — Ricky's own generated text
        // doesn't go through transcription and isn't affected by this.
        // Context: agent_reports/2026-07-11_dictation-cyrillic-fix.md
        const text = entry.role === "user" ? cyrillicToLatin(entry.text) : entry.text;
        setTranscript((list) => [text === entry.text ? entry : { ...entry, text }, ...list].slice(0, 200));
        if (entry.role !== "user") return;
        if (screenRef.current !== "dictation") {
          // Live voice-triggered entry (agent_reports/2026-07-10_dictation-and-dashboard-fixes.md):
          // previously only the onQuickCommand click path could trigger this —
          // saying "uđi u diktat mod" did nothing here, so the model, lacking
          // any dictation concept, guessed the closest tool it had (set_mode)
          // instead. This intercepts the phrase locally and deterministically,
          // without depending on the model calling any tool at all. Not
          // appended as content below — a not-yet-in-dictation utterance is
          // read as a command, never dictated text.
          if (text.toLowerCase().includes(DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD)) {
            setScreen("dictation");
            clientRef.current?.setDictationMode(true);
          }
          return;
        }
        // Voice exit (agent_reports/2026-07-11_dictation-guardrails-and-exit.md):
        // previously there was no way to leave dictation by voice at all — a
        // phrase like "vrati se u normalan mod" just got written down as
        // dictated content instead of acting on it. Checked before appending,
        // same reasoning as the entry trigger: a command, not content.
        const lowerText = text.toLowerCase();
        if ((DICTATION_EXIT_PHRASES[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_EXIT_PHRASES).some((phrase) => lowerText.includes(phrase))) {
          clientRef.current?.setDictationMode(false);
          setScreen("home");
          return;
        }
        // Dictation Mode Phase 1 (agent_reports/2026-07-10_dictation-phase1-cloud-stt.md):
        // route the live session's own speech transcription into the dictation
        // textarea while that screen is active, instead of a separate STT call.
        // Once actually in dictation mode, every user utterance is content —
        // including one that happens to contain "dikt" as a substring.
        setDictationText((prev) => (prev ? `${prev} ${text}` : text));
      },
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

  // Dictation Mode "Doradi" + "..." menus. All four rewrite operations replace
  // dictationText wholesale, so a single-level undo (dictationUndoRef) covers
  // both rewrite and "Obriši sve" — the only two destructive actions here.
  // Context: agent_reports/2026-07-11_dictation-rewrite-menu.md
  const DICTATION_REWRITE_LABELS: Record<TextRewriteOperation, string> = {
    formalize: "Formalizovano",
    shorten: "Skraćeno",
    proofread: "Pravopis provjeren",
    translate_en: "Prevedeno na engleski",
  };

  function handleDictationRewrite(operation: TextRewriteOperation) {
    const trimmed = dictationText.trim();
    if (!trimmed || dictationBusy) return;
    dictationUndoRef.current = dictationText;
    setCanUndoDictation(true);
    setDictationBusy(true);
    window.ricky
      .rewriteText({ text: dictationText, operation })
      .then((result) => {
        setDictationText(result.text);
        addActivityEvent(createActivityEvent("status", DICTATION_REWRITE_LABELS[operation]));
      })
      .catch(() => {
        addActivityEvent(createActivityEvent("error", "Greška pri obradi teksta", "Tekst nije promijenjen."));
      })
      .finally(() => setDictationBusy(false));
  }

  function handleDictationCopy() {
    if (!dictationText.trim()) return;
    void navigator.clipboard.writeText(dictationText);
    addActivityEvent(createActivityEvent("status", "Tekst kopiran"));
  }

  function handleDictationClear() {
    if (!dictationText.trim()) return;
    if (!window.confirm("Obrisati cijeli diktirani tekst?")) return;
    dictationUndoRef.current = dictationText;
    setCanUndoDictation(true);
    setDictationText("");
  }

  function handleDictationUndo() {
    if (dictationUndoRef.current === null) return;
    setDictationText(dictationUndoRef.current);
    dictationUndoRef.current = null;
    setCanUndoDictation(false);
  }

  function handleDictationDownload() {
    if (!dictationText.trim()) return;
    const blob = new Blob([dictationText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `diktat-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.txt`;
    link.click();
    URL.revokeObjectURL(url);
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
        pendingConfirmation={pendingConfirmation}
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
          if (text.toLowerCase().includes(DICTATION_TRIGGER_WORDS[interfaceLanguageRef.current] ?? DEFAULT_DICTATION_TRIGGER_WORD)) {
            setScreen("dictation");
            clientRef.current?.setDictationMode(true);
          }
          sendText(text);
        }}
        onEnterDictation={() => {
          setScreen("dictation");
          clientRef.current?.setDictationMode(true);
        }}
        onDictationChange={setDictationText}
        onDictationCancel={() => {
          clientRef.current?.setDictationMode(false);
          setScreen("home");
        }}
        onDictationSend={() => {
          clientRef.current?.setDictationMode(false);
          if (dictationText.trim()) sendText(dictationText.trim());
          setScreen("home");
        }}
        onDictationRewrite={handleDictationRewrite}
        onDictationCopy={handleDictationCopy}
        onDictationClear={handleDictationClear}
        onDictationUndo={handleDictationUndo}
        onDictationDownload={handleDictationDownload}
        dictationBusy={dictationBusy}
        canUndoDictation={canUndoDictation}
        onDictationContinue={() => {
          // "Nastavi diktiranje" had no onClick at all before — clicking did
          // literally nothing. Capture is already continuous while on this
          // screen (Phase 1), so the one real gap is: if voice dropped (mic
          // idle timeout, manual Stop) there's no active session left to
          // capture anything. Reconnect if needed, re-affirm dictation mode
          // either way, and always log an activity entry so the click has
          // visible feedback even when already connected (nothing to "resume").
          // Context: agent_reports/2026-07-11_dictation-continue-button-fix.md
          if (isConnected) {
            clientRef.current?.setDictationMode(true);
            addActivityEvent(createActivityEvent("status", "Diktiranje nastavljeno", "Slušam dalje."));
          } else {
            addActivityEvent(createActivityEvent("status", "Ponovo povezujem glas", "Diktiranje nastavlja čim se poveže."));
            void connect().then(() => {
              clientRef.current?.setDictationMode(true);
            });
          }
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

      {/* Rendered LAST deliberately — Electron's -webkit-app-region drag/
          no-drag resolution for overlapping regions appears to follow DOM
          order (later wins), not z-index/stacking context. This element's
          no-drag must win over .pixel-section-label's drag (12-pixel-board.css)
          where "main" spans the full top row and reaches this corner.
          Context: agent_reports/2026-07-11_i18n-foundation.md */}
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
    </main>
  );
}

