/**
 * FAZA 18 — Electron end-to-end smoke skripta.
 *
 * Pokreće Python backend, provjerava osnovni health/tools/events tok,
 * provjerava da je backend proces uredno zaustavljen i vraća exit code 0
 * ako sve prođe, ili 1 ako bilo koji korak faila.
 *
 * Pokretanje: node scripts/smoke-test.cjs
 * Preduvjet: Python backend je instaliran (pip install -r requirements.txt)
 *
 * Context: agent_reports/2026-07-06_faza18-test-suite-quality-gate.md
 */
const { startPythonBackend, stopPythonBackend } = require("../electron/services/pythonProcess.cjs");
const {
  getHealth,
  listTools,
  executeTool,
  listEvents,
} = require("../electron/services/pythonClient.cjs");

const TIMEOUT_MS = 600;
const MAX_RETRIES = 30;

let failed = 0;

function check(label, condition, detail = "") {
  if (condition) {
    console.log(`  ✓ ${label}`);
  } else {
    console.log(`  ✗ ${label}${detail ? " — " + detail : ""}`);
    failed++;
  }
}

async function waitForHealth() {
  for (let i = 0; i < MAX_RETRIES; i++) {
    const h = await getHealth({ timeoutMs: TIMEOUT_MS });
    if (h.ok) return true;
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

async function run() {
  console.log("\n=== RileyJarvis Smoke Test (FAZA 18) ===\n");

  // 1. Start backend
  console.log("[1/6] Pokretanje Python backend-a...");
  await startPythonBackend({ isPackaged: false });

  console.log("       Čekanje /health...");
  const healthy = await waitForHealth();
  check("Backend odgovara na /health", healthy);
  if (!healthy) {
    console.log("\n  ✗ Backend nije odgovorio — prekidam smoke test.\n");
    process.exit(1);
  }

  // 2. List tools
  console.log("\n[2/6] GET /tools...");
  const tools = await listTools({});
  const toolNames = new Set(tools.tools.map((t) => t.name));
  check("Vraća listu toolova", Array.isArray(tools.tools) && tools.tools.length > 0);
  check("Sadrži echo", toolNames.has("echo"));
  check("Sadrži note_add (FAZA 11)", toolNames.has("note_add"));
  check("Sadrži web_search (FAZA 16)", toolNames.has("web_search"));
  check("Sadrži screen_snapshot (FAZA 11)", toolNames.has("screen_snapshot"));

  // 3. Execute a tool
  console.log("\n[3/6] POST /tools/execute (echo)...");
  const echo = await executeTool({
    tool_name: "echo",
    arguments: { text: "smoke" },
    context: { computer_mode: false },
  });
  check("echo vraća ok", echo.ok === true);
  check("echo result.text === 'smoke'", echo.result?.text === "smoke");

  // 4. Create note (FAZA 11)
  console.log("\n[4/6] POST /tools/execute (note_add)...");
  const note = await executeTool({
    tool_name: "note_add",
    arguments: { text: "Smoke test note", tags: ["smoke"] },
    context: { computer_mode: false },
  });
  check("note_add vraća ok", note.ok === true);
  check("note_add result.note.text tačan", note.result?.note?.text === "Smoke test note");

  // 5. Events bridge (FAZA 11)
  console.log("\n[5/6] GET /events (backend.ready event)...");
  const events = await listEvents(undefined);
  const eventTypes = new Set(events.events.map((e) => e.type));
  check("Vraća events listu", Array.isArray(events.events));
  check("Sadrži backend.ready", eventTypes.has("backend.ready"));
  check("next_cursor postavljen", typeof events.next_cursor === "string");

  // 6. Stop backend
  console.log("\n[6/6] Gašenje backend-a...");
  stopPythonBackend();
  // Uvicorn graceful shutdown može trajati nekoliko sekundi.
  await new Promise((r) => setTimeout(r, 3500));
  // getHealth vraća {ok: false, error} kad backend ne odgovara — ne baca.
  let backendDown = false;
  for (let attempt = 0; attempt < 5; attempt++) {
    const h = await getHealth({ timeoutMs: 800 });
    if (!h.ok) {
      backendDown = true;
      break;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  check("Backend više ne odgovara na /health nakon stop-a", backendDown);

  // Rezime
  console.log(`\n=== Rezime: ${failed === 0 ? "SVE PROŠLO ✓" : `${failed} GREŠAKA ✗`} ===\n`);
  process.exit(failed === 0 ? 0 : 1);
}

run().catch((error) => {
  console.error(`\n  ✗ Smoke test crash: ${error.message}\n`);
  try {
    stopPythonBackend();
  } catch {}
  process.exit(1);
});
