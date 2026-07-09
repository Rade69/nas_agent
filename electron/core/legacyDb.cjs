/**
 * Legacy JSON DB helpers — verbatim move from electron/main.cjs (R2b refactor).
 * Context: agent_reports/2026-07-09_pi-refactor-r2b-legacy-db.md
 *
 * Plain module: own top-level fs/path/dataDir/dbPath/dbWriteQueue so the moved
 * function bodies are byte-identical to their original definitions in main.cjs.
 * main.cjs keeps its own dataDir/dbPath (still needed for screenshot/image paths)
 * and imports these helpers via require("./core/legacyDb.cjs").
 */
const fs = require("node:fs/promises");
const path = require("node:path");

const dataDir = path.join(process.cwd(), "data");
const dbPath = path.join(dataDir, "ricky-db.json");
let dbWriteQueue = Promise.resolve();

async function ensureData() {
  await fs.mkdir(dataDir, { recursive: true });
  try {
    await fs.access(dbPath);
  } catch {
    await fs.writeFile(dbPath, JSON.stringify(defaultDb(), null, 2));
  }
}

async function readDb() {
  await ensureData();
  const raw = await fs.readFile(dbPath, "utf8");
  return normalizeDb(JSON.parse(raw));
}

async function writeDb(db) {
  await ensureData();
  await fs.writeFile(dbPath, JSON.stringify(db, null, 2));
}

async function updateDb(mutator) {
  const operation = dbWriteQueue.then(async () => {
    const db = await readDb();
    const result = await mutator(db);
    await writeDb(db);
    return { db, result };
  });
  dbWriteQueue = operation.catch(() => {});
  return operation;
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function defaultDb() {
  return {
    notes: [],
    records: [],
    thumbnailBoard: {
      references: [],
      images: [],
      nextNumber: 1,
      page: 1,
      pageSize: 9,
      selectedId: null,
      view: "grid",
    },
  };
}

function normalizeDb(db) {
  const next = db && typeof db === "object" ? db : defaultDb();
  if (!Array.isArray(next.notes)) next.notes = [];
  if (!Array.isArray(next.records)) next.records = [];
  if (!next.thumbnailBoard || typeof next.thumbnailBoard !== "object") {
    next.thumbnailBoard = defaultDb().thumbnailBoard;
  }
  if (!Array.isArray(next.thumbnailBoard.references)) next.thumbnailBoard.references = [];
  if (!Array.isArray(next.thumbnailBoard.images)) next.thumbnailBoard.images = [];
  let maxNumber = 0;
  for (const image of [...next.thumbnailBoard.images].reverse()) {
    if (!Number.isInteger(image.number) || image.number < 1) image.number = maxNumber + 1;
    maxNumber = Math.max(maxNumber, image.number);
  }
  if (!Number.isInteger(next.thumbnailBoard.nextNumber) || next.thumbnailBoard.nextNumber <= maxNumber) {
    next.thumbnailBoard.nextNumber = maxNumber + 1;
  }
  if (!Number.isInteger(next.thumbnailBoard.page) || next.thumbnailBoard.page < 1) next.thumbnailBoard.page = 1;
  if (!Number.isInteger(next.thumbnailBoard.pageSize) || next.thumbnailBoard.pageSize < 1) next.thumbnailBoard.pageSize = 9;
  if (typeof next.thumbnailBoard.view !== "string") next.thumbnailBoard.view = "grid";
  if (!("selectedId" in next.thumbnailBoard)) next.thumbnailBoard.selectedId = null;
  return next;
}

module.exports = { ensureData, readDb, writeDb, updateDb, asObject, defaultDb, normalizeDb };
