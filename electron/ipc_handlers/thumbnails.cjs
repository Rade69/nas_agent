/** Thumbnail reference image + save-as IPC handlers.
 *  handleThumbnailAddReference (S-03, docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md):
 *  native file picker is the ONLY way a reference image can ever be
 *  registered — there is no model tool for it (removed from
 *  electron/core/realtimeToolSpecs.cjs). Picked path goes to Python for
 *  validation/storage first; only on success does this commit the opaque id
 *  into the legacy thumbnail board JSON via legacyMedia.cjs's
 *  commitThumbnailReference().
 *  handleThumbnailSaveAs: user-reported gap (2026-07-13) — generated
 *  thumbnails were auto-saved into the app's internal data dir with no way
 *  to export a copy anywhere else. Native save dialog, source path
 *  restricted to the app's own dataDir (defense in depth — a compromised
 *  renderer must not be able to turn this into "copy any local file to a
 *  user-picked destination"). */
const fs = require("node:fs/promises");
const path = require("node:path");
const { dialog } = require("electron");
const { addThumbnailReference } = require("../services/pythonClient.cjs");
const { getMainWindow } = require("../core/window.cjs");
const { commitThumbnailReference } = require("../tools_legacy/legacyMedia.cjs");

// Same value as legacyMedia.cjs's own dataDir — duplicated copy is an
// already-established, approved pattern in this codebase (see that file's
// header comment, R2b).
const dataDir = path.join(process.cwd(), "data");

async function handleThumbnailAddReference() {
  const mainWindow = getMainWindow();
  const result = await dialog.showOpenDialog(mainWindow || undefined, {
    title: "Select a reference photo — it will be uploaded to OpenAI when generating thumbnails",
    properties: ["openFile"],
    filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "webp", "gif", "bmp"] }],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return { ok: true, cancelled: true };
  }

  const picked = result.filePaths[0];
  const validated = await addThumbnailReference({ path: picked });
  return await commitThumbnailReference({
    id: validated.id,
    label: validated.label,
    previewDataUrl: validated.preview_data_url,
  });
}

async function handleThumbnailSaveAs(_event, { path: sourcePath, suggestedName } = {}) {
  const resolvedSource = path.resolve(String(sourcePath || ""));
  const resolvedDataDir = path.resolve(dataDir);
  if (resolvedSource !== resolvedDataDir && !resolvedSource.startsWith(resolvedDataDir + path.sep)) {
    throw new Error("Refusing to save a file outside the app's own thumbnail storage.");
  }

  const mainWindow = getMainWindow();
  const result = await dialog.showSaveDialog(mainWindow || undefined, {
    title: "Save thumbnail as...",
    defaultPath: String(suggestedName || "thumbnail.png"),
    filters: [{ name: "PNG Image", extensions: ["png"] }],
  });

  if (result.canceled || !result.filePath) {
    return { ok: true, cancelled: true };
  }

  await fs.copyFile(resolvedSource, result.filePath);
  return { ok: true, cancelled: false, path: result.filePath };
}

module.exports = { handleThumbnailAddReference, handleThumbnailSaveAs };
