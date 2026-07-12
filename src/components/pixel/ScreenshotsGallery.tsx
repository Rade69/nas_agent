/** "Snimci ekrana" gallery — replaces the static "Nema snimaka ekrana."
 *  placeholder that always showed regardless of what was actually on disk.
 *  Screenshots previously had zero persistent tracking: screen_snapshot only
 *  returned an ephemeral inline artifact for the one response, the PNG file
 *  itself just sat in screenshots_dir forever with no UI ever listing it.
 *  Context: agent_reports/2026-07-12_screenshot-privacy.md (FABLE-5 GUI
 *  review finding #3). */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Screenshot } from "../../vite-env";

type LoadState = "loading" | "idle" | "error";

export function ScreenshotsGallery() {
  const { t } = useTranslation();
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [deleting, setDeleting] = useState(false);

  function refresh() {
    setState("loading");
    window.ricky
      .listScreenshots()
      .then((result) => {
        setScreenshots(result.screenshots);
        setState("idle");
      })
      .catch(() => setState("error"));
  }

  useEffect(refresh, []);

  async function handleDeleteAll() {
    if (!window.confirm(t("screenshots.confirmDeleteAll"))) return;
    setDeleting(true);
    try {
      await window.ricky.deleteAllScreenshots();
      refresh();
    } catch {
      setState("error");
    } finally {
      setDeleting(false);
    }
  }

  if (state === "loading") {
    return <p className="drawer-placeholder-text">{t("screenshots.loading")}</p>;
  }
  if (state === "error") {
    return <p className="drawer-placeholder-text">{t("screenshots.loadError")}</p>;
  }

  return (
    <div className="pixel-screenshots-gallery">
      <div className="pixel-screenshots-header">
        <span className="pixel-settings-hint">{t("screenshots.retentionNote")}</span>
        <button
          className="pixel-secondary"
          onClick={() => void handleDeleteAll()}
          disabled={deleting || screenshots.length === 0}
        >
          {deleting ? t("screenshots.deleting") : t("screenshots.deleteAll")}
        </button>
      </div>
      {screenshots.length === 0 ? (
        <p className="drawer-placeholder-text">{t("dashboard.noScreenshots")}</p>
      ) : (
        <div className="pixel-screenshots-grid">
          {screenshots.map((shot) => (
            <figure key={shot.id} className="pixel-screenshot-item">
              <img src={`file://${shot.filePath}`} alt={shot.createdAt} loading="lazy" />
              <figcaption>
                <time>{new Date(shot.createdAt).toLocaleString()}</time>
                <span className="pixel-screenshot-badge">
                  {shot.sentToModel ? t("screenshots.sentToModel") : t("screenshots.localOnly")}
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
