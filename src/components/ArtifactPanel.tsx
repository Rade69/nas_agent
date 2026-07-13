/** Floating artifact viewer panel — renders markdown, code, tables, images,
 *  Mermaid diagrams, notes, and thumbnail boards. Supports fullscreen toggle
 *  and hide/show. Localized via i18next (GUI Localization PR-3).
 *  Context: agent_reports/2026-07-05_faza8-voice-first-ui-refactor.md */
import { useEffect, useId, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import mermaid from "mermaid";
import type { RickyArtifact } from "../vite-env";

type ArtifactPanelProps = {
  artifact: RickyArtifact | null;
  visible: boolean;
  fullscreen: boolean;
  onToggleVisible: () => void;
  onToggleFullscreen: () => void;
  // S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): ThumbnailBoard's
  // "+ Add reference photo" button mutates the board directly (native file
  // picker, not a model tool call) and needs to push the refreshed board
  // artifact back up to whatever owns `artifact` state (App.tsx).
  onArtifactUpdate: (artifact: RickyArtifact) => void;
};

type MermaidState = {
  svg: string;
  error: string | null;
  source: string;
};

type NoteCard = {
  id?: string;
  text?: string;
  tags?: string[];
  createdAt?: string;
};

type ThumbnailBoardData = {
  view?: "grid" | "selected";
  selectedId?: string | null;
  references?: Array<{ id?: string; label?: string; path?: string }>;
  page?: {
    page?: number;
    pageSize?: number;
    totalImages?: number;
    totalPages?: number;
    nextNumber?: number;
  };
  images?: Array<{
    id?: string;
    number?: number;
    src?: string;
    // User-reported gap (2026-07-13): the app's internal storage path for
    // this generated thumbnail, needed by the "Save As..." export button —
    // Electron already includes it (thumbnailBoardArtifact spreads the
    // stored image record), just wasn't in this type yet.
    path?: string;
    prompt?: string;
    type?: string;
    status?: "loading" | string;
    loadingLabel?: string;
    createdAt?: string;
    selected?: boolean;
  }>;
};

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "strict",
});

export function ArtifactPanel({ artifact, visible, fullscreen, onToggleVisible, onToggleFullscreen, onArtifactUpdate }: ArtifactPanelProps) {
  const { t } = useTranslation();
  const [mermaidState, setMermaidState] = useState<MermaidState>({ svg: "", error: null, source: "" });
  const rawId = useId();
  const mermaidId = useMemo(() => `mermaid-${rawId.replace(/[^a-zA-Z0-9_-]/g, "")}`, [rawId]);

  useEffect(() => {
    let cancelled = false;
    if (artifact?.kind !== "mermaid") {
      setMermaidState({ svg: "", error: null, source: "" });
      return;
    }

    const source = normalizeMermaidSource(artifact.content, artifact.title);
    mermaid
      .render(mermaidId, source)
      .then((result) => {
        if (!cancelled) setMermaidState({ svg: result.svg, error: null, source });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        const fallback = fallbackMermaidSource(artifact.title);
        mermaid
          .render(`${mermaidId}-fallback`, fallback)
          .then((result) => {
            if (!cancelled) setMermaidState({ svg: result.svg, error: message, source });
          })
          .catch(() => {
            if (!cancelled) setMermaidState({ svg: "", error: message, source });
          });
      });

    return () => {
      cancelled = true;
    };
  }, [artifact, mermaidId]);

  if (!visible) {
    return (
      <button className="artifact-tab" onClick={onToggleVisible}>
        {t("artifact.show")}
      </button>
    );
  }

  return (
    <aside className={`artifact-panel ${fullscreen ? "artifact-fullscreen" : ""}`}>
      <header className="artifact-header">
        <div>
          <span className="eyebrow">{t("artifact.title")}</span>
          <h2>{artifact?.title || t("artifact.readyTitle")}</h2>
        </div>
        <div className="artifact-actions">
          <button onClick={onToggleFullscreen}>{fullscreen ? t("artifact.window") : t("artifact.fullscreen")}</button>
          <button onClick={onToggleVisible}>{t("artifact.hide")}</button>
        </div>
      </header>
      <div className="artifact-body">
        {artifact ? renderArtifact(artifact, mermaidState, t, onArtifactUpdate) : <EmptyArtifact />}
      </div>
    </aside>
  );
}

function EmptyArtifact() {
  const { t } = useTranslation();
  return (
    <div className="empty-artifact">
      <p>{t("artifact.emptyState")}</p>
    </div>
  );
}

function renderArtifact(
  artifact: RickyArtifact,
  mermaidState: MermaidState,
  t: TFunction,
  onArtifactUpdate: (artifact: RickyArtifact) => void,
) {
  if (artifact.kind === "table") {
    return <JsonTable content={artifact.content} />;
  }

  if (artifact.kind === "notes") {
    return <NotesGrid content={artifact.content} />;
  }

  if (artifact.kind === "mermaid") {
    return (
      <div className="mermaid-stack">
        <div className="mermaid-output" dangerouslySetInnerHTML={{ __html: mermaidState.svg }} />
        {mermaidState.error ? (
          <details className="mermaid-repair">
            <summary>{t("artifact.mermaidRepairedSummary")}</summary>
            <p>{t("artifact.mermaidRepairedDetail")}</p>
            <pre>{mermaidState.source}</pre>
          </details>
        ) : null}
      </div>
    );
  }

  if (artifact.kind === "image") {
    const src =
      artifact.content.startsWith("http") || artifact.content.startsWith("file://") || artifact.content.startsWith("data:")
        ? artifact.content
        : `file://${artifact.content}`;
    return <img className="artifact-image" src={src} alt={artifact.title} />;
  }

  if (artifact.kind === "imageLoading") {
    return (
      <div className="image-loading-artifact">
        <div className="image-loading-frame">
          <div className="image-loading-grid" />
          <div className="image-loading-orb" />
          <div className="image-loading-scan" />
        </div>
        <div className="image-loading-copy">
          <span>{t("artifact.generatingImage")}</span>
          <p>{artifact.content}</p>
        </div>
      </div>
    );
  }

  if (artifact.kind === "thumbnailBoard") {
    return <ThumbnailBoard content={artifact.content} onArtifactUpdate={onArtifactUpdate} />;
  }

  if (artifact.kind === "code") {
    return (
      <pre className="code-artifact">
        <code>{artifact.content}</code>
      </pre>
    );
  }

  if (artifact.kind === "markdown") {
    return <MarkdownArtifact content={artifact.content} />;
  }

  if (artifact.kind === "progress") {
    return (
      <div className="progress-card">
        <div className="progress-pulse" />
        <p>{artifact.content}</p>
      </div>
    );
  }

  return <pre className="text-artifact">{artifact.content}</pre>;
}

function ThumbnailBoard({
  content,
  onArtifactUpdate,
}: {
  content: string;
  onArtifactUpdate: (artifact: RickyArtifact) => void;
}) {
  const { t } = useTranslation();
  const [addingReference, setAddingReference] = useState(false);
  const [addReferenceError, setAddReferenceError] = useState<string | null>(null);
  const [savingThumbnail, setSavingThumbnail] = useState(false);
  const [saveThumbnailError, setSaveThumbnailError] = useState<string | null>(null);
  const board = parseThumbnailBoard(content);
  if (!board) return <pre className="text-artifact">{content}</pre>;

  // S-03 (docs/SECURITY_AND_IMPROVEMENT_AUDIT_2026-07-13.md): the native file
  // picker is the only way to register a reference image — there is no
  // voice/model path for this anymore. Errors here are Python's path_sandbox
  // validation failures (wrong location, wrong file type, too large).
  async function handleAddReference() {
    setAddingReference(true);
    setAddReferenceError(null);
    try {
      const result = await window.ricky.addThumbnailReference();
      if (!result.cancelled && "artifact" in result) {
        onArtifactUpdate(result.artifact);
      }
    } catch (error) {
      setAddReferenceError(error instanceof Error ? error.message : t("artifact.addReferenceError"));
    } finally {
      setAddingReference(false);
    }
  }

  // User-reported gap (2026-07-13): generated thumbnails were only ever
  // auto-saved into the app's internal data dir with no way to export a
  // copy elsewhere.
  async function handleSaveAs(image: { path?: string; number?: number }) {
    if (!image.path) return;
    setSavingThumbnail(true);
    setSaveThumbnailError(null);
    try {
      await window.ricky.saveThumbnailAs({
        path: image.path,
        suggestedName: `thumbnail-${image.number ?? "export"}.png`,
      });
    } catch (error) {
      setSaveThumbnailError(error instanceof Error ? error.message : t("artifact.saveThumbnailError"));
    } finally {
      setSavingThumbnail(false);
    }
  }

  const images = board.images || [];
  const selected = images.find((image) => image.selected) || images.find((image) => image.id === board.selectedId) || null;
  const page = board.page || {};

  if (board.view === "selected" && selected) {
    return (
      <section className="thumbnail-selected">
        <div className="thumbnail-selected-frame">
          <img src={selected.src} alt={`Thumbnail ${selected.number || ""}`} />
          <span className="thumbnail-number-large">{selected.number}</span>
        </div>
        <div className="thumbnail-selected-copy">
          <span>{selected.type || t("artifact.thumbnailTypeFallback")}</span>
          <p>{selected.prompt || t("artifact.selectedThumbnailFallback")}</p>
          <div className="thumbnail-save-actions">
            <button
              className="thumbnail-save-as"
              onClick={() => void handleSaveAs(selected)}
              disabled={savingThumbnail || !selected.path}
            >
              {savingThumbnail ? t("artifact.savingThumbnail") : t("artifact.saveThumbnailAs")}
            </button>
            {saveThumbnailError ? <span className="thumbnail-save-as-error">{saveThumbnailError}</span> : null}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="thumbnail-board">
      <header className="thumbnail-board-meta">
        <div>
          <span>{t("artifact.thumbnailCount", { count: page.totalImages ?? images.length })}</span>
          <p>{t("artifact.referenceCount", { count: (board.references || []).length })}</p>
        </div>
        <small>
          {t("artifact.pageInfo", {
            page: page.page || 1,
            totalPages: page.totalPages || 1,
            next: page.nextNumber || "?",
          })}
        </small>
      </header>
      <div className="thumbnail-reference-actions">
        <button
          className="thumbnail-add-reference"
          onClick={() => void handleAddReference()}
          disabled={addingReference}
          title={t("artifact.addReferenceTitle")}
        >
          {addingReference ? t("artifact.addingReference") : t("artifact.addReference")}
        </button>
        {addReferenceError ? <span className="thumbnail-add-reference-error">{addReferenceError}</span> : null}
      </div>
      {images.length > 0 ? (
        <div className="thumbnail-grid">
          {images.map((image) => (
            <article className={image.status === "loading" ? "thumbnail-card thumbnail-card-loading" : "thumbnail-card"} key={image.id || image.number}>
              {image.status === "loading" ? (
                <div className="thumbnail-loading-wrap">
                  <div className="thumbnail-loading-grid" />
                  <div className="thumbnail-loading-orb" />
                  <span>{image.number}</span>
                </div>
              ) : (
                <div className="thumbnail-image-wrap">
                  <img src={image.src} alt={`Thumbnail ${image.number || ""}`} />
                  <span>{image.number}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="thumbnail-empty">
          <p>{t("artifact.noReferenceImage")}</p>
        </div>
      )}
    </section>
  );
}

function parseThumbnailBoard(content: string): ThumbnailBoardData | null {
  try {
    const value = JSON.parse(content) as unknown;
    if (!value || typeof value !== "object") return null;
    return value as ThumbnailBoardData;
  } catch {
    return null;
  }
}

function MarkdownArtifact({ content }: { content: string }) {
  const [visibleContent, setVisibleContent] = useState("");

  useEffect(() => {
    setVisibleContent("");
    let index = 0;
    const step = Math.max(8, Math.ceil(content.length / 180));
    const timer = window.setInterval(() => {
      index = Math.min(content.length, index + step);
      setVisibleContent(content.slice(0, index));
      if (index >= content.length) window.clearInterval(timer);
    }, 14);

    return () => window.clearInterval(timer);
  }, [content]);

  return (
    <div className="markdown-artifact">
      <div className="stream-line" />
      {renderMarkdown(visibleContent)}
    </div>
  );
}

function renderMarkdown(content: string) {
  return content.split("\n").map((line, index) => {
    if (line.startsWith("# ")) {
      return <h1 key={index}>{renderInline(line.slice(2))}</h1>;
    }
    if (line.startsWith("## ")) {
      return <h2 key={index}>{renderInline(line.slice(3))}</h2>;
    }
    if (line.startsWith("### ")) {
      return <h3 key={index}>{renderInline(line.slice(4))}</h3>;
    }
    if (line.startsWith("- ")) {
      return <li key={index}>{renderInline(line.slice(2))}</li>;
    }
    if (!line.trim()) {
      return <div className="markdown-gap" key={index} />;
    }
    return <p key={index}>{renderInline(line)}</p>;
  });
}

function renderInline(text: string) {
  const parts: ReactNode[] = [];
  const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = linkRegex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    parts.push(
      <a href={match[2]} key={`${match[2]}-${match.index}`} target="_blank" rel="noreferrer">
        {match[1]}
      </a>,
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length > 0 ? parts : text;
}

function NotesGrid({ content }: { content: string }) {
  const { t } = useTranslation();
  const notes = parseNotes(content);
  if (notes.length === 0) return <pre className="text-artifact">{content}</pre>;

  return (
    <div className="notes-grid">
      {notes.map((note, index) => (
        <article className="note-card" key={note.id || index}>
          <p>{note.text || t("artifact.untitledNote")}</p>
          <footer>
            <span>{formatDate(note.createdAt, t)}</span>
            {note.tags && note.tags.length > 0 ? <small>{note.tags.map((tag) => `#${tag}`).join(" ")}</small> : null}
          </footer>
        </article>
      ))}
    </div>
  );
}

function parseNotes(content: string): NoteCard[] {
  try {
    const value = JSON.parse(content) as unknown;
    if (!Array.isArray(value)) return [];
    return value.filter((note): note is NoteCard => note !== null && typeof note === "object");
  } catch {
    return [];
  }
}

function formatDate(value: string | undefined, t: TFunction): string {
  if (!value) return t("artifact.justNow");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function normalizeMermaidSource(content: string, title: string): string {
  const stripped = content
    .replace(/```mermaid/gi, "")
    .replace(/```/g, "")
    .replace(/\r/g, "")
    .trim();

  if (!stripped) return fallbackMermaidSource(title);

  const lines = stripped
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/[“”]/g, '"').replace(/[‘’]/g, "'").replace(/[–—]/g, "-"));

  const first = lines[0] || "";
  const hasHeader = /^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap|timeline)\b/i.test(first);
  return hasHeader ? lines.join("\n") : `flowchart TD\n${lines.join("\n")}`;
}

function fallbackMermaidSource(title: string): string {
  const safeTitle = title.replace(/["<>]/g, "") || "Chart";
  return `flowchart TD\n  A["${safeTitle}"] --> B["Chart syntax issue"]\n  B --> C["Fallback displayed"]`;
}

function JsonTable({ content }: { content: string }) {
  const parsed = parseRows(content);
  if (!parsed) return <pre className="text-artifact">{content}</pre>;

  const rows = Array.isArray(parsed) ? parsed : [parsed];
  const keys = Array.from(
    rows.reduce<Set<string>>((set, row) => {
      Object.keys(row).forEach((key) => set.add(key));
      return set;
    }, new Set()),
  );

  if (rows.length === 0 || keys.length === 0) {
    return <pre className="text-artifact">{content}</pre>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{keys.map((key) => <th key={key}>{key}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.id || index}`}>
              {keys.map((key) => (
                <td key={key}>{formatCell(row[key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function parseRows(content: string): Array<Record<string, unknown>> | Record<string, unknown> | null {
  try {
    const value = JSON.parse(content) as unknown;
    if (Array.isArray(value) && value.every((row) => row && typeof row === "object" && !Array.isArray(row))) {
      return value as Array<Record<string, unknown>>;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
