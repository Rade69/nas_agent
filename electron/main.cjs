/** Electron main process entry point.
 *  Orchestrates: Python backend startup, window creation, IPC handler
 *  registration, companion orb, kill-switch hotkey, security self-test,
 *  and app lifecycle (ready/before-quit/window-all-closed/activate).
 *
 *  Architecture rule (AGENTS.md): No new business/agent/computer-use/
 *  storage/AI logic here — this file is shell/IPC wiring only.
 *  Context: agent_reports/2026-07-05_split-main-cjs-faza3.md */

const { app, BrowserWindow, dialog, globalShortcut } = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");
const crypto = require("node:crypto");

require("./core/env.cjs");

const { createWindow, setWindowMode, getMainWindow } = require("./core/window.cjs");
const { registerIpcHandlers } = require("./core/ipc.cjs");
const { runSecuritySelfTest } = require("./core/securitySelfTest.cjs");
// FAZA 17: legacy PowerShell tool feature flag.
const {
  isLegacyEnabled,
  hasPythonEquivalent,
  hasNoPythonYet,
  blockLegacyResponse,
  LEGACY_FLAG,
} = require("./core/legacyTools.cjs");
// FAZA 12: Companion orb window.
const {
  createCompanionWindow,
  showCompanion,
  hideCompanion,
  toggleCompanion,
  forwardVoiceStateToCompanion,
  setLockedPosition,
  showOrbContextMenu,
  ensureTray,
  setMainWindowFocusCallback,
  setQuitAppCallback,
  setToggleVoiceCallback,
} = require("./core/companionWindow.cjs");
const { startPythonBackend, stopPythonBackend } = require("./services/pythonProcess.cjs");
const { createRealtimeSession } = require("./services/pythonClient.cjs");
const {
  approveConfirmation,
  cancelConfirmation,
  createConfirmation,
  createPlan,
  executeTool,
  getPlan,
  listConfirmations,
  listEvents,
  listPlans,
  listPendingConfirmations,
  rejectConfirmation,
  requestJson,
  updatePlan,
  updatePlanStep,
} = require("./services/pythonClient.cjs");
const { computerOpenApp } = require("./tools_legacy/powershell/computerOpenApp.cjs");
const { computerTypeText } = require("./tools_legacy/powershell/computerTypeText.cjs");
const { computerPressKey } = require("./tools_legacy/powershell/computerPressKey.cjs");
const { computerClick } = require("./tools_legacy/powershell/computerClick.cjs");
const { computerScroll } = require("./tools_legacy/powershell/computerScroll.cjs");
const { screenSnapshot } = require("./tools_legacy/powershell/screenSnapshot.cjs");
const { uiInspect } = require("./tools_legacy/powershell/uiInspect.cjs");

const dataDir = path.join(process.cwd(), "data");
const dbPath = path.join(dataDir, "ricky-db.json");
let currentMode = "display";


const { toolSpecs } = require("./core/realtimeToolSpecs.cjs");
const {
  ensureData,
  readDb,
  writeDb,
  updateDb,
  asObject,
  defaultDb,
  normalizeDb,
} = require("./core/legacyDb.cjs");
const {
  webSearch,
  formatSearchMarkdown,
  cleanMarkdownText,
  hostname,
  buildMenuMarkdown,
  generateImage,
  imageErrorArtifact,
  thumbnailLoadingPrepare,
  thumbnailGenerate,
  thumbnailEdit,
  thumbnailSelect,
  createThumbnailImage,
  editImageWithInputs,
  saveImageResponse,
  thumbnailRecord,
  thumbnailPrompt,
  editThumbnailPrompt,
  thumbnailByNumberOrSelected,
  replaceLoadingThumbnails,
  removeLoadingThumbnailRun,
  thumbnailNumber,
  assignThumbnailNumber,
  pageForArgs,
  sortedThumbnailImages,
  paginatedThumbnailImages,
  thumbnailPageMeta,
  thumbnailBoardSummary,
  buildThumbnailBoardInstructions,
  thumbnailBoardArtifact,
  imageDataUrl,
  mimeForPath,
} = require("./tools_legacy/legacyMedia.cjs");
const { handleEventsList } = require("./ipc_handlers/events.cjs");
const { handleSettingsGet, handleSettingsUpdate } = require("./ipc_handlers/settings.cjs");
const { handleTextRewrite } = require("./ipc_handlers/text.cjs");
const { handleScreenshotsList, handleScreenshotsDeleteAll } = require("./ipc_handlers/screenshots.cjs");
const { handleThumbnailAddReference, handleThumbnailSaveAs } = require("./ipc_handlers/thumbnails.cjs");
const {
  handlePlansList,
  handlePlanCreate,
  handlePlanGet,
  handlePlanUpdate,
  handlePlanStepUpdate,
} = require("./ipc_handlers/plans.cjs");
const {
  handleConfirmationsList,
  handleConfirmationsPending,
  handleConfirmationCreate,
  handleConfirmationApprove,
  handleConfirmationReject,
  handleConfirmationCancel,
} = require("./ipc_handlers/confirmations.cjs");
const { handleRealtimeCreateToken } = require("./ipc_handlers/realtime.cjs");
const {
  handleToolsList,
  handleCancelAllExecutions,
  handleAppQuit,
  handleAppMinimize,
  handleAppToggleMaximize,
} = require("./ipc_handlers/app.cjs");
const {
  handleCompanionShow,
  handleCompanionHide,
  handleCompanionToggle,
  handleCompanionVoiceStateUpdate,
  handleCompanionClick,
  handleCompanionOpenMain,
  handleCompanionToggleVoice,
  handleCompanionToggleLock,
} = require("./ipc_handlers/companion.cjs");

async function clearStartupLoadingThumbnails() {
  const db = await readDb();
  const before = db.thumbnailBoard.images.length;
  db.thumbnailBoard.images = db.thumbnailBoard.images.filter((image) => image.status !== "loading");
  if (db.thumbnailBoard.images.length !== before) {
    db.thumbnailBoard.selectedId = null;
    db.thumbnailBoard.view = "grid";
    await writeDb(db);
  }
}

function requireComputerMode() {
  if (currentMode !== "computer") {
    // Security PR A (S-01): the model can no longer call set_mode itself, so
    // this message must tell it to ask the human — not to "switch" on its own,
    // which was the exact framing that made S-01 easy to trigger by voice.
    return {
      ok: false,
      needsMode: "computer",
      message: "Computer control is disabled. Ask the user to enable Computer Mode from the app.",
    };
  }
  return null;
}

function requiresConfirmation(args) {
  return args.confirmed !== true && (args.risk === "may_send_or_modify" || args.risk === "private_or_sensitive");
}

// FAZA 11: tool names whose execution is delegated to the Python backend.
// Low-risk memory tools (notes/records/artifacts) + system tools that require
// computer_mode (screen_snapshot/ui_inspect). Legacy Electron handlers below
// remain as fallback.
const PHASE11_DELEGATED_TOOLS = new Set([
  "note_add",
  "note_search",
  "note_list",
  "records_create",
  "records_search",
  "records_update",
  "records_delete",
  "artifact_create",
  "artifact_get",
  "artifact_list",
  "artifact_show",
  "screen_snapshot",
  "ui_inspect",
  // FAZA 16: OpenAI/Exa/image integrations now live in the Python backend.
  "web_search",
  "image_generate",
  // FAZA 13: computer-use tools now have Python equivalents (ctypes + Win32 API).
  "computer_open_app",
  "computer_type_text",
  "computer_press_key",
  "computer_click",
  "computer_scroll",
  // FAZA 14: element-targeting tools (UIA).
  "computer_find_elements",
  "computer_click_element",
  "computer_set_text_element",
  "computer_get_element_text",
]);

// FAZA S-4 fail-closed (audit R2, agent_reports/2026-07-07_pi-security-audit-d1-d2.md):
// high-risk tools whose Python definitions set requires_confirmation=true. The
// backend's permission_engine is the ONLY place a confirmation_id is verified;
// the legacy PowerShell fallback cannot verify one (it runs precisely because
// the backend is unavailable). So these must NEVER execute via the legacy path —
// running them there would perform a confirmed-only action unconfirmed. They
// fail closed instead, matching the S-4 "backend down => high-risk blocked" rule.
const LEGACY_FAIL_CLOSED_TOOLS = new Set([
  "computer_type_text",
  "computer_click",
  "computer_click_element",
  "computer_set_text_element",
]);

// Adapt a Python ToolExecutionResponse into the legacy {ok, artifact, ...}
// shape that App.tsx and the Realtime function-call flow expect. Python handlers
// embed an `artifact` inside `result`; surface it so the artifact panel updates.
function adaptPythonToolResponse(response, toolName) {
  if (!response || typeof response !== "object") {
    return { ok: false, error: `Empty response from backend for ${toolName}.` };
  }
  if (response.ok === false) {
    return {
      ok: false,
      error: response.error?.message || `Tool ${toolName} failed.`,
      errorCode: response.error?.code,
      execution_id: response.execution_id,
      tool_state: response.tool_state,
    };
  }
  const result = response.result || {};
  const artifact = result.artifact;
  // Spread remaining result fields (note, record, notes, records, image_path,
  // active_window, ...) so legacy callers see the same shape as before.
  const { artifact: _omit, ...rest } = result;
  return {
    ok: true,
    artifact,
    execution_id: response.execution_id,
    tool_state: response.tool_state,
    ...rest,
  };
}

async function prepareWindowData() {
  await ensureData();
  await clearStartupLoadingThumbnails();
}

// --- FAZA 9: confirmations + plans IPC handlers ---
// Context: agent_reports/2026-07-05_faza9-confirmations-plans.md
// Thin pass-through handlers that forward to the Python backend. No business
// logic lives here (architecture rule: electron/main.cjs is only shell/IPC).
// The permission/risk layer that *issues* confirmations from tool execution is
// FAZA 10 — here we only expose storage + state machine transitions.



// FAZA 11: event bridge handler.

// --- FAZA 12: Companion orb IPC handlers ---
// Context: agent_reports/2026-07-05_faza12-companion-orb.md
// Thin pass-through handlers for the companion orb lifecycle and voice state
// forwarding. No business logic — the orb is a separate BrowserWindow whose
// renderer mounts CompanionOrb.tsx (see src/main.tsx ?view=companion).



async function handleToolsExecute(_event, toolCall) {
  const name = String(toolCall?.name || "");
  const args = asObject(toolCall?.arguments);

  // FAZA 11: delegate memory/artifact/system tools to the Python backend.
  // Context: agent_reports/2026-07-05_faza11-tool-registry-local-tools.md
  // Legacy handlers below remain as fallback if the backend is unavailable
  // (per MIGRATION_PLAN.md "Keep legacy implementations available until the
  // Python versions are verified"). screen_snapshot/ui_inspect still require
  // computer_mode; the Python permission engine (FAZA 10) enforces it.
  if (PHASE11_DELEGATED_TOOLS.has(name)) {
    try {
      const toolContext = toolCall?.context || {};
      const response = await executeTool({
        tool_name: name,
        arguments: args,
        context: {
          computer_mode: currentMode === "computer",
          ...(toolContext.confirmation_id ? { confirmation_id: String(toolContext.confirmation_id) } : {}),
          // S-2 prompt-injection escalation for the voice path (agent_reports/
          // 2026-07-10_s2-voice-path-fix.md): the renderer tracks whether a
          // reads_external_content tool has succeeded this voice session and
          // forwards the flag here so permission_engine's escalation can see it.
          // Previously always omitted, so the voice path could never escalate.
          ...(toolContext.external_content_seen === true ? { external_content_seen: true } : {}),
        },
      });
      return adaptPythonToolResponse(response, name);
    } catch (error) {
      // FAZA 17: if legacy tools are disabled, don't fall through to the
      // legacy handler — return a structured error instead.
      // Context: agent_reports/2026-07-06_faza17-disable-legacy-powershell.md
      if (!isLegacyEnabled()) {
        return {
          ok: false,
          error: `Tool '${name}' failed via Python backend and legacy fallback is disabled (${LEGACY_FLAG}=0): ${error instanceof Error ? error.message : error}`,
          errorCode: "PYTHON_FAILED_LEGACY_DISABLED",
        };
      }
      // FAZA S-4 fail-closed (audit R2): even with legacy enabled, high-risk
      // confirmation-required tools must NOT run through the legacy path, which
      // cannot verify the approved confirmation_id the backend would require.
      // Blocking here keeps a backend outage from turning into unconfirmed
      // keystrokes/clicks.
      if (LEGACY_FAIL_CLOSED_TOOLS.has(name)) {
        return {
          ok: false,
          error: `Tool '${name}' requires an approved confirmation, which only the Python backend can verify. The backend is unavailable, so it will not run via the unconfirmed legacy fallback.`,
          errorCode: "HIGH_RISK_LEGACY_BLOCKED",
        };
      }
      // Fall through to legacy handler below — keeps the app working if the
      // backend is down or the tool is not yet registered there.
      console.warn(
        `[faza11] Python backend failed for ${name}, falling back to legacy:`,
        error instanceof Error ? error.message : error,
      );
    }
  }

  try {
    if (name === "set_mode") {
      currentMode = args.mode === "computer" ? "computer" : "display";
      setWindowMode(currentMode);
      // Orb presence (docs/ORB_PRESENCE_SPEC.md): the floating companion orb carries
      // the Stop control, so it must be on screen whenever the agent can act on the
      // computer. Auto-show it entering Computer Mode; hide it going back to display.
      if (currentMode === "computer") {
        showCompanion();
      } else {
        hideCompanion();
      }
      return {
        ok: true,
        mode: currentMode,
        artifact: {
          title: "Ricky Mode",
          kind: "progress",
          content: `Mode switched to ${currentMode === "computer" ? "computer use" : "display"} mode.`,
        },
      };
    }

    if (name === "artifact_show") {
      return { ok: true, artifact: args };
    }

    if (name === "show_menu") {
      return {
        ok: true,
        artifact: {
          title: "Ricky Menu",
          kind: "markdown",
          content: buildMenuMarkdown(),
        },
      };
    }

    if (name === "web_search") {
      return await webSearch(args);
    }

    if (name === "image_generate") {
      return await generateImage(args);
    }

    if (name === "thumbnail_loading_prepare") {
      return await thumbnailLoadingPrepare(args);
    }

    // S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): no model
    // tool for adding a reference image anymore — thumbnail_reference_add is
    // no longer in realtimeToolSpecs.cjs, so the model can never request it
    // via the Realtime protocol. Registration only happens through the
    // "thumbnails:add-reference" IPC channel below, triggered by a native
    // file picker click.

    if (name === "thumbnail_generate") {
      return await thumbnailGenerate(args);
    }

    if (name === "thumbnail_edit") {
      return await thumbnailEdit(args);
    }

    if (name === "thumbnail_select") {
      return await thumbnailSelect(args);
    }

    if (name === "thumbnail_grid") {
      const { db } = await updateDb(async (currentDb) => {
        currentDb.thumbnailBoard.view = "grid";
        currentDb.thumbnailBoard.page = pageForArgs(args);
      });
      return { ok: true, board: thumbnailBoardSummary(db), artifact: await thumbnailBoardArtifact(db, "grid") };
    }

    if (name === "mermaid_render") {
      const diagram = normalizeMermaidDiagram(String(args.diagram || ""), String(args.title || "Mermaid chart"));
      return {
        ok: true,
        artifact: {
          title: String(args.title || "Mermaid chart"),
          kind: "mermaid",
          content: diagram,
        },
      };
    }

    if (name === "note_add") {
      const db = await readDb();
      const note = {
        id: crypto.randomUUID(),
        text: String(args.text || ""),
        tags: Array.isArray(args.tags) ? args.tags.map(String) : [],
        createdAt: new Date().toISOString(),
      };
      db.notes.unshift(note);
      await writeDb(db);
      return {
        ok: true,
        note,
        artifact: {
          title: "Fun Notes",
          kind: "notes",
          content: JSON.stringify(db.notes.slice(0, 20), null, 2),
        },
      };
    }

    if (name === "records_create") {
      const db = await readDb();
      const record = {
        id: crypto.randomUUID(),
        collection: String(args.collection || "default"),
        title: String(args.title || "Untitled"),
        fields: asObject(args.fields),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      db.records.unshift(record);
      await writeDb(db);
      return { ok: true, record, artifact: recordsArtifact(db.records, record.collection) };
    }

    if (name === "records_search") {
      const db = await readDb();
      const collection = String(args.collection || "default");
      const query = String(args.query || "").toLowerCase();
      const records = db.records.filter((record) => {
        if (record.collection !== collection) return false;
        if (!query) return true;
        return JSON.stringify(record).toLowerCase().includes(query);
      });
      return { ok: true, records, artifact: recordsArtifact(records, collection) };
    }

    if (name === "records_update") {
      const db = await readDb();
      const record = db.records.find((item) => item.id === args.id);
      if (!record) return { ok: false, error: "Record not found." };
      record.title = typeof args.title === "string" ? args.title : record.title;
      record.fields = { ...record.fields, ...asObject(args.fields) };
      record.updatedAt = new Date().toISOString();
      await writeDb(db);
      return { ok: true, record, artifact: recordsArtifact(db.records, record.collection) };
    }

    if (name === "records_delete") {
      if (args.confirmed !== true) {
        return { ok: false, requiresConfirmation: true, message: "Explicit confirmation is required before deleting a record." };
      }
      const db = await readDb();
      const before = db.records.length;
      db.records = db.records.filter((record) => record.id !== args.id);
      await writeDb(db);
      return { ok: true, deleted: before !== db.records.length, artifact: recordsArtifact(db.records, "All Records") };
    }

    if (name.startsWith("computer_") || name === "screen_snapshot" || name === "ui_inspect") {
      // FAZA 17: when legacy tools are disabled, tools that have no Python
      // equivalent yet (computer_open_app/type_text/press_key/click/scroll)
      // must return a clear error rather than silently failing or crashing.
      // screen_snapshot/ui_inspect already prefer Python via PHASE11; they
      // only reach this legacy path if Python failed AND legacy is enabled.
      // Context: agent_reports/2026-07-06_faza17-disable-legacy-powershell.md
      if (!isLegacyEnabled() && hasNoPythonYet(name)) {
        return blockLegacyResponse(name);
      }
      const blocked = requireComputerMode();
      if (blocked) return blocked;
    }

    if (name === "computer_open_app") {
      const appName = String(args.appName || "");
      try {
        await computerOpenApp(appName);
      } catch (error) {
        return { ok: false, error: `Could not open ${appName}: ${error instanceof Error ? error.message : String(error)}` };
      }
      return { ok: true, message: `Opened ${appName}.` };
    }

    if (name === "computer_type_text") {
      await computerTypeText(args.text);
      return { ok: true, message: "Typed text into the active app." };
    }

    if (name === "computer_press_key") {
      await computerPressKey(args.key, args.repeat);
      return { ok: true, message: `Pressed ${args.key}.` };
    }

    if (name === "computer_click") {
      if (requiresConfirmation(args)) {
        return { ok: false, requiresConfirmation: true, message: "Confirmation required before clicking a risky target." };
      }
      await computerClick(args.x, args.y);
      return { ok: true, message: `Clicked ${args.x}, ${args.y}.` };
    }

    if (name === "computer_scroll") {
      const direction = await computerScroll(args.direction, args.amount);
      return { ok: true, message: `Scrolled ${direction}.` };
    }

    if (name === "screen_snapshot") {
      const screenshotPath = await screenSnapshot(dataDir);
      return {
        ok: true,
        path: screenshotPath,
        artifact: {
          title: "Screen Snapshot",
          kind: "image",
          content: screenshotPath,
        },
      };
    }

    if (name === "ui_inspect") {
      const summary = await uiInspect();
      return {
        ok: true,
        summary,
        artifact: {
          title: "UI Inspect",
          kind: "text",
          content: summary,
        },
      };
    }

    return { ok: false, error: `Unknown tool: ${name}` };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}

function recordsArtifact(records, collection) {
  return {
    title: `Records: ${collection}`,
    kind: "table",
    content: JSON.stringify(records, null, 2),
  };
}

function normalizeMermaidDiagram(diagram, title) {
  const stripped = diagram
    .replace(/```mermaid/gi, "")
    .replace(/```/g, "")
    .replace(/\r/g, "")
    .trim();

  if (!stripped) {
    return fallbackMermaidDiagram(title);
  }

  const lines = stripped
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) =>
      line
        .replace(/[â€œâ€]/g, '"')
        .replace(/[â€˜â€™]/g, "'")
        .replace(/[â€“â€”]/g, "-")
        .replace(/\s+-->\s+/g, " --> ")
        .replace(/\s+---\s+/g, " --- "),
    );

  const hasDiagramHeader = /^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap|timeline)\b/i.test(
    lines[0] || "",
  );

  return hasDiagramHeader ? lines.join("\n") : `flowchart TD\n${lines.join("\n")}`;
}

function fallbackMermaidDiagram(title) {
  const safeTitle = String(title || "Chart").replace(/["<>]/g, "");
  return `flowchart TD\n  A["${safeTitle}"] --> B["Chart request received"]\n  B --> C["Ricky will show a safe fallback if syntax fails"]`;
}

registerIpcHandlers({
  "tools:list": handleToolsList,
  "app:quit": handleAppQuit,
  "app:minimize": handleAppMinimize,
  "app:toggle-maximize": handleAppToggleMaximize,
  "realtime:create-token": handleRealtimeCreateToken,
  "tools:execute": handleToolsExecute,
  "tools:cancel-all": handleCancelAllExecutions,
  "settings:get": handleSettingsGet,
  "settings:update": handleSettingsUpdate,
  "text:rewrite": handleTextRewrite,
  "screenshots:list": handleScreenshotsList,
  "screenshots:delete-all": handleScreenshotsDeleteAll,
  // S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): native file
  // picker is the only way a thumbnail reference image can be registered.
  "thumbnails:add-reference": handleThumbnailAddReference,
  // User-reported gap (2026-07-13): generated thumbnails were only ever
  // auto-saved to the app's internal data dir. Native save dialog lets the
  // user export a copy anywhere.
  "thumbnails:save-as": handleThumbnailSaveAs,
  // FAZA 9: confirmations + plans IPC channels (allowlist entries).
  "confirmations:list": handleConfirmationsList,
  "confirmations:pending": handleConfirmationsPending,
  "confirmations:create": handleConfirmationCreate,
  "confirmations:approve": handleConfirmationApprove,
  "confirmations:reject": handleConfirmationReject,
  "confirmations:cancel": handleConfirmationCancel,
  "plans:list": handlePlansList,
  "plans:create": handlePlanCreate,
  "plans:get": handlePlanGet,
  "plans:update": handlePlanUpdate,
  "plans:update-step": handlePlanStepUpdate,
  // FAZA 11: event bridge.
  "events:list": handleEventsList,
  // FAZA 12: companion orb lifecycle + voice state forwarding.
  "companion:show": handleCompanionShow,
  "companion:hide": handleCompanionHide,
  "companion:toggle": handleCompanionToggle,
  "companion:voice-state-update": handleCompanionVoiceStateUpdate,
  "companion:click": handleCompanionClick,
  "companion:open-main": handleCompanionOpenMain,
  "companion:toggle-voice": handleCompanionToggleVoice,
  "companion:toggle-lock": handleCompanionToggleLock,
  "companion:menu": () => showOrbContextMenu(),
  // Stop button on the companion orb — the orb is the only visible surface in
  // Computer Mode, so it needs a visible "stop everything". Reuses the same
  // kill-switch path as Ctrl+Alt+K: forces display mode + forwards app:kill-switch
  // to the main window (whose runKillSwitch tears down voice + cancels backend tools).
  "companion:stop": triggerKillSwitch,
});

// FAZA S-4: global kill-switch hotkey. Ctrl+Alt+K only — F10/F11 were dropped
// because Windows reserves them (menu bar / fullscreen) and swallows them
// before a globalShortcut callback can fire, so they registered but never
// triggered. The fast "Escape while focused" path lives in the renderer
// (App.tsx); this global one covers the unfocused/minimized case.
const KILL_SWITCH_ACCELERATORS = ["CommandOrControl+Alt+K"];

function triggerKillSwitch() {
  console.log("[kill-switch] TRIGGERED — stopping voice/mic and forcing display mode");
  // Force Computer Mode off so no acting tool can run post-stop.
  currentMode = "display";
  const win = getMainWindow && getMainWindow();
  if (win && !win.isDestroyed()) {
    win.webContents.send("app:kill-switch");
  }
}

function registerKillSwitch() {
  const registered = [];
  for (const accelerator of KILL_SWITCH_ACCELERATORS) {
    try {
      if (globalShortcut.register(accelerator, triggerKillSwitch)) {
        registered.push(accelerator);
      } else {
        console.warn(`[kill-switch] ${accelerator} is already taken by another app`);
      }
    } catch (error) {
      console.warn(`[kill-switch] could not register ${accelerator}:`, error);
    }
  }
  if (registered.length > 0) {
    console.log(`[kill-switch] active on: ${registered.join(", ")}`);
  } else {
    console.warn("[kill-switch] no accelerator could be registered; kill-switch hotkey unavailable");
  }
  return registered;
}

app.whenReady().then(async () => {
  // FAZA 12: wire companion orb callbacks so the companion module can bring
  // the main window forward and quit the app without circular imports.
  setMainWindowFocusCallback(() => {
    const main = getMainWindow && getMainWindow();
    if (main && !main.isDestroyed()) {
      if (!main.isVisible()) main.show();
      main.focus();
    }
  });
  setQuitAppCallback(() => app.quit());
  // Orb context menu "Toggle voice": forward to the main renderer's Realtime
  // client (same path as the companion:toggle-voice IPC handler).
  setToggleVoiceCallback(() => {
    const main = getMainWindow && getMainWindow();
    if (main && !main.isDestroyed()) {
      main.webContents.send("companion:toggle-voice");
    }
  });

  try {
    await startPythonBackend({ isPackaged: app.isPackaged });
  } catch (error) {
    console.error("[python-backend] Failed to start Python backend:", error);
  }

  // Security Gate 0 (docs/SECURITY_HARDENING_PLAN.md section 18). Runs after
  // the backend is up so the backend-side half of the self-test is reachable.
  // A packaged build fails closed on any failed check; a dev build only logs
  // a warning so local iteration isn't blocked.
  // Context: agent_reports/2026-07-06_gate0-selftest-pathsandbox.md
  try {
    const selfTest = await runSecuritySelfTest({ isPackaged: app.isPackaged });
    if (!selfTest.ok) {
      const failed = selfTest.checks.filter((check) => !check.passed);
      const summary = failed.map((check) => `${check.name}: ${check.detail}`).join("\n");
      if (app.isPackaged) {
        dialog.showErrorBox("Security configuration failed. Production mode blocked.", summary);
        app.quit();
        return;
      }
      console.warn("[security-self-test] FAILED (non-blocking in dev build):\n" + summary);
    }
  } catch (error) {
    console.error("[security-self-test] Could not run self-test:", error);
  }

  await createWindow({ beforeShow: prepareWindowData });

  // Orb presence (docs/ORB_PRESENCE_SPEC.md situation #3 "Minimiziran prozor"):
  // this was a documented gap — minimize/restore of the main window previously
  // had no effect on the companion orb, so a user minimizing without having
  // manually toggled the orb on first would see no floating presence at all,
  // even though the spec calls for the small orb to be the quick-access
  // surface while the main window is out of the way. Symmetric with the
  // Computer Mode auto-show/hide already wired to set_mode above.
  const mainWindowForOrb = getMainWindow();
  if (mainWindowForOrb) {
    mainWindowForOrb.on("minimize", () => showCompanion());
    mainWindowForOrb.on("restore", () => hideCompanion());
  }

  // FAZA S-4 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md S33): global kill-switch.
  // Registers the first available hotkey from a fallback chain so it still
  // binds if the preferred key is taken by another app. On trigger it tears
  // down the voice/mic session in the renderer (even when unfocused) and forces
  // Computer Mode back off — a single always-available "stop everything".
  registerKillSwitch();

  // FAZA 12: create the companion orb after the main window so the user has
  // a quick voice entry point. Tray is best-effort (may be unavailable on
  // some CI/headless setups); the orb window itself is the primary surface.
  try {
    createCompanionWindow();
    ensureTray();
  } catch (error) {
    console.warn("[companion] Could not create companion orb:", error);
  }
});

app.on("before-quit", () => {
  globalShortcut.unregisterAll();
  stopPythonBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    void createWindow({ beforeShow: prepareWindowData });
  }
});
