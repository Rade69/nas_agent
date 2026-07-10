import type { RickyToolResult } from "../vite-env";
import type { ResponseOutputItem, ServerEvent } from "./realtimeTypes";

export function safeParseEvent(raw: string): ServerEvent {
  try {
    return JSON.parse(raw) as ServerEvent;
  } catch {
    return {};
  }
}

export function parseToolArguments(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

export function sanitizeToolResult(result: RickyToolResult): RickyToolResult {
  if (!result.artifact) return result;

  const { artifact, ...rest } = result;
  return {
    ...rest,
    artifact: {
      title: artifact.title,
      kind: artifact.kind,
      content:
        artifact.kind === "thumbnailBoard"
          ? "Thumbnail board rendered in the UI. Use the compact board field for exact numbers, selected state, and loading state."
          : artifact.kind === "image" || artifact.kind === "imageLoading"
            ? "Image rendered in the UI."
            : artifact.content.length > 1200
              ? `${artifact.content.slice(0, 1200)}...`
              : artifact.content,
      language: artifact.language,
      fullscreen: artifact.fullscreen,
    },
  };
}

export function collectItemText(item: ServerEvent["item"]): string {
  return item?.content?.map((part) => part.transcript || part.text || "").filter(Boolean).join("\n") || "";
}

export function collectOutputText(item: ResponseOutputItem): string {
  return item.content?.map((part) => part.transcript || part.text || "").filter(Boolean).join("\n") || "";
}