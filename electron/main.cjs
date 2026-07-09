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
  ensureTray,
  setMainWindowFocusCallback,
  setQuitAppCallback,
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

const RICKY_INSTRUCTIONS = `# Role and Objective
You are Ricky, Riley's desktop AI operator. You speak through realtime voice and can use local tools.

# Personality and Tone
Concise, calm, useful. Use a confident man's voice. Talk like a smart operator, not a chatbot.

# Modes
- Display mode is the default. Use the app and artifact panel to show things. Do not control the computer.
- Computer use mode allows desktop control tools. Only use computer tools after the user asks for computer use or asks you to control the computer.

# Tool Behavior
- Use read-only tools when the user's intent is clear.
- When Riley says "show me the menu", "show me what I can do", or asks what Ricky can do, call show_menu immediately.
- For web search, notes, charts, records, image generation, and artifact display, act directly when the request is clear.
- For thumbnail creation/editing, always use the thumbnail board tools, never generic image_generate and never artifact_show with imageLoading. Generate exactly one 16:9 image per request. Never generate multiple unless Riley separately asks again. Every generate/edit request gets a permanent database number that never changes, like #18 then #19 then #20. Do not renumber visible grid positions. Show paginated 3x3 pages of the permanent numbers. Do not show a standalone fullscreen loading animation for thumbnails. Use Riley's wording literally: do not invent elaborate extra concepts, fake text, or extra thumbnail ideas. For edits, use the exact existing numbered/selected image as input and make only the requested change.
- The thumbnail board persists across sessions. If Riley references thumbnail #N, trust that permanent number and call the matching thumbnail tool. Do not say you cannot see old thumbnails. Use thumbnail_grid to refresh state or change pages if needed.
- When a thumbnail finishes generating or editing, do not announce it verbally. The UI updates silently.
- For sending messages, deleting data, buying things, account changes, sharing private information, or anything irreversible, summarize the action and ask for explicit confirmation before calling the modifying tool.
- If a tool requires a confirmed field, set confirmed to true only after the user clearly confirms.
- Typing text and pressing Enter/Return in computer use mode are allowed without extra approval when Riley asks you to type or send a prompt. Ask first before clicking controls or taking actions that delete, purchase, change settings, or expose private information.
- Explain what you are doing in one short sentence before longer tool work. Do not over-explain.

# Artifacts
Use artifacts for menus, web results, graphics, notes, database tables, code snippets, and task progress. If the user asks to show, hide, or fullscreen the artifacts panel, call the artifact tool.
For Mermaid charts, keep syntax simple: start with flowchart TD, avoid markdown fences, avoid parentheses in node labels, and use short alphanumeric node IDs.

# Audio
Let the user interrupt. If audio is unclear, ask one short clarifying question instead of guessing.`;

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
  thumbnailReferenceAdd,
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
    return {
      ok: false,
      needsMode: "computer",
      message: "Computer control is disabled. Ask Ricky to switch to computer use mode first.",
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

function handleToolsList() {
  return toolSpecs;
}

function handleAppQuit() {
  app.quit();
}

function handleAppMinimize() {
  const win = getMainWindow();
  if (win && !win.isDestroyed()) {
    win.minimize();
  }
}

function handleAppToggleMaximize() {
  const win = getMainWindow();
  if (!win || win.isDestroyed()) return;
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
}

// --- FAZA 9: confirmations + plans IPC handlers ---
// Context: agent_reports/2026-07-05_faza9-confirmations-plans.md
// Thin pass-through handlers that forward to the Python backend. No business
// logic lives here (architecture rule: electron/main.cjs is only shell/IPC).
// The permission/risk layer that *issues* confirmations from tool execution is
// FAZA 10 — here we only expose storage + state machine transitions.

async function handleConfirmationsList(_event, payload = {}) {
  const { status, limit } = payload || {};
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("limit", String(limit));
  const path = params.toString() ? `/confirmations?${params.toString()}` : "/confirmations";
  return await requestJson(path, {});
}

async function handleConfirmationsPending() {
  return await listPendingConfirmations({});
}

async function handleConfirmationCreate(_event, payload) {
  return await createConfirmation(payload || {});
}

async function handleConfirmationApprove(_event, confirmationId) {
  return await approveConfirmation(confirmationId);
}

async function handleConfirmationReject(_event, confirmationId) {
  return await rejectConfirmation(confirmationId);
}

async function handleConfirmationCancel(_event, confirmationId) {
  return await cancelConfirmation(confirmationId);
}

async function handlePlansList() {
  return await listPlans({});
}

async function handlePlanCreate(_event, payload) {
  return await createPlan(payload || {});
}

async function handlePlanGet(_event, planId) {
  return await getPlan(planId);
}

async function handlePlanUpdate(_event, { planId, payload }) {
  return await updatePlan(planId, payload || {});
}

async function handlePlanStepUpdate(_event, { planId, stepId, payload }) {
  return await updatePlanStep(planId, stepId, payload || {});
}

// FAZA 11: event bridge handler.
async function handleEventsList(_event, since) {
  return await listEvents(typeof since === "string" ? since : undefined);
}

// --- FAZA 12: Companion orb IPC handlers ---
// Context: agent_reports/2026-07-05_faza12-companion-orb.md
// Thin pass-through handlers for the companion orb lifecycle and voice state
// forwarding. No business logic — the orb is a separate BrowserWindow whose
// renderer mounts CompanionOrb.tsx (see src/main.tsx ?view=companion).

function handleCompanionShow() {
  showCompanion();
  return { ok: true };
}

function handleCompanionHide() {
  hideCompanion();
  return { ok: true };
}

function handleCompanionToggle() {
  toggleCompanion();
  return { ok: true };
}

// Valid VoiceState values (mirror of src/lib/voiceState.ts VoiceState union).
// Kept here so the main process can validate before forwarding to the companion
// renderer without importing TS.
const VALID_VOICE_STATES = new Set([
  "idle",
  "listening",
  "transcribing",
  "thinking",
  "speaking",
  "waiting_confirmation",
  "interrupted",
  "muted",
  "error",
]);

// Main renderer -> main process -> companion renderer: forward VoiceState so
// the orb can display it without running its own Realtime client.
// FAZA S-4 (audit R3): validate against a fixed allowlist before forwarding.
// The payload comes from the (potentially XSS-compromised) main renderer and is
// pushed into a *second* renderer; only known state strings are allowed through
// so an attacker can't smuggle an arbitrary object/markup across windows.
function handleCompanionVoiceStateUpdate(_event, state) {
  if (typeof state !== "string" || !VALID_VOICE_STATES.has(state)) {
    return { ok: false, error: "Invalid voice state." };
  }
  forwardVoiceStateToCompanion(state);
  return { ok: true };
}

// Orb renderer -> main process: user clicked the orb (quick voice entry).
function handleCompanionClick() {
  // Bring main window forward and focus it so the user sees the conversation.
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    if (!main.isVisible()) main.show();
    main.focus();
  }
  return { ok: true };
}

// Orb renderer -> main process: user wants the main window.
function handleCompanionOpenMain() {
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    if (!main.isVisible()) main.show();
    main.focus();
  }
  return { ok: true };
}

// Orb renderer -> main process: toggle voice (start/stop listening). The actual
// voice start/stop lives in the main renderer's Realtime client; main forwards
// a request to it.
function handleCompanionToggleVoice() {
  const main = getMainWindow && getMainWindow();
  if (main && !main.isDestroyed()) {
    main.webContents.send("companion:toggle-voice");
  }
  return { ok: true };
}

function handleCompanionToggleLock(_event, locked) {
  setLockedPosition(locked === true);
  return { ok: true };
}

async function handleRealtimeCreateToken() {
  const db = await readDb();
  const instructions = `${RICKY_INSTRUCTIONS}\n\n${buildThumbnailBoardInstructions(db)}`;

  const session = {
    type: "realtime",
    model: "gpt-realtime-2",
    instructions,
    output_modalities: ["audio"],
    reasoning: { effort: "low" },
    tool_choice: "auto",
    tools: toolSpecs.map(({ risk: _omit, ...rest }) => rest),
    audio: {
      input: {
        turn_detection: {
          type: "semantic_vad",
          eagerness: "medium",
          create_response: true,
          interrupt_response: true,
        },
      },
      output: {
        voice: "cedar",
      },
    },
    tracing: {
      workflow_name: "Ricky Desktop Companion",
    },
  };

  // Context: agent_reports/2026-07-05_faza6-realtime-session-security.md
  // The standard OpenAI API key now lives only on the Python backend side (FAZA 6 /
  // SECURITY_HARDENING_PLAN.md section 7). Electron only assembles the session config
  // (instructions/tools depend on Electron-side DB state not yet migrated) and forwards
  // it for the backend to mint the ephemeral Realtime credential.
  const { value, expiresAt } = await createRealtimeSession(session);
  return { value, expiresAt: expiresAt ?? null };
}

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

    if (name === "thumbnail_reference_add") {
      return await thumbnailReferenceAdd(args);
    }

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
