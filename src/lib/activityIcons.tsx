/** Icon and CSS class resolver for ActivityTimeline entries.
 *  Maps ActivityEvent kind + TranscriptEntry role to a Lucide icon
 *  component and CSS modifier class for the activity timeline display.
 *  Context: agent_reports/2026-07-05_faza8-voice-first-ui-refactor.md */
import IconSuccess from "../../assets/brending/icons/status/icon-status-success.svg?react";
import IconError from "../../assets/brending/icons/status/icon-status-error.svg?react";
import IconRunning from "../../assets/brending/icons/status/icon-status-running.svg?react";
import IconMic from "../../assets/brending/icons/voice/icon-microphone.svg?react";
import IconScreenshot from "../../assets/brending/icons/actions/icon-screenshot.svg?react";
import IconOpenApp from "../../assets/brending/icons/actions/icon-open-app.svg?react";

export type ActivityLike = {
  kind: string;
  title: string;
  detail?: string;
};

export type ActivityCategory = {
  Icon: React.ComponentType<{ className?: string }>;
  className: string;
};

// Maps an activity row to one of the colored category icons from the
// approved mockup (assets/GUI-SETS/GUI-SET-4.png "Activity Drawer") — green
// success, blue voice/dictation, purple screenshot, orange generic tool, red
// error. Shared between the Aktivnost tab (ActivityTimeline) and the idle
// screen's "Zadnja aktivnost" card so both use the same categorization.
export function categoryForActivity(row: ActivityLike): ActivityCategory {
  const text = `${row.title} ${row.detail || ""}`.toLowerCase();
  if (row.kind === "error") return { Icon: IconError, className: "activity-icon-error" };
  if (text.includes("screenshot") || text.includes("snimljen")) {
    return { Icon: IconScreenshot, className: "activity-icon-screenshot" };
  }
  if (row.kind === "voice" || row.kind === "ricky" || row.kind === "user" || text.includes("diktir")) {
    return { Icon: IconMic, className: "activity-icon-voice" };
  }
  if (text.includes("otvoren") || text.includes("otvori")) {
    return { Icon: IconOpenApp, className: "activity-icon-tool" };
  }
  if (row.kind === "tool") return { Icon: IconRunning, className: "activity-icon-tool" };
  return { Icon: IconSuccess, className: "activity-icon-success" };
}
