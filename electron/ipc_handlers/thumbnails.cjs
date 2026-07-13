/** Thumbnail reference image IPC handler (S-03, docs/
 *  SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md). The native file picker here
 *  is the ONLY way a reference image can ever be registered — there is no
 *  model tool for it (removed from electron/core/realtimeToolSpecs.cjs).
 *  Picked path goes to Python for validation/storage first; only on success
 *  does this commit the opaque id into the legacy thumbnail board JSON via
 *  legacyMedia.cjs's commitThumbnailReference(). */
const { dialog } = require("electron");
const { addThumbnailReference } = require("../services/pythonClient.cjs");
const { getMainWindow } = require("../core/window.cjs");
const { commitThumbnailReference } = require("../tools_legacy/legacyMedia.cjs");

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

module.exports = { handleThumbnailAddReference };
