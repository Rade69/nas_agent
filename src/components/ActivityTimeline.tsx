/** Full activity timeline list — combines ActivityEvent[] and TranscriptEntry[]
 *  into a unified chronological feed with categorized icons. Localized via
 *  i18next (Localization PR-2).
 *  Context: agent_reports/2026-07-11_gui-localization-pr2.md */
import { useTranslation } from "react-i18next";
import type { ActivityEvent } from "../lib/voiceState";
import type { TranscriptEntry } from "../lib/realtime";
import { categoryForActivity } from "../lib/activityIcons";

type ActivityTimelineProps = {
  transcript: TranscriptEntry[];
  activityEvents: ActivityEvent[];
};

type ActivityRow = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  at: string;
};

export function ActivityTimeline({ transcript, activityEvents }: ActivityTimelineProps) {
  const { t } = useTranslation();
  const rows: ActivityRow[] = [
    ...activityEvents.map((event) => ({
      id: event.id,
      kind: event.kind,
      title: event.title,
      detail: event.detail || event.rawType || "",
      at: event.at,
    })),
    ...transcript.map((entry) => ({
      id: entry.id,
      kind: entry.role,
      // "Ricky" je brend ime, NE prevoditi (isto pravilo kao svuda u projektu).
      title: entry.role === "ricky" ? "Ricky" : entry.role,
      detail: entry.text,
      at: entry.at,
    })),
  ].slice(0, 90);

  return (
    <section className="transcript activity-timeline">
      <div className="transcript-list">
        {rows.length === 0 ? (
          <p className="activity-empty">{t("activity.empty")}</p>
        ) : (
          rows.map((row) => {
            const { Icon, className } = categoryForActivity(row);
            return (
              <article className={`entry entry-${row.kind}`} key={row.id}>
                <span className={`activity-icon ${className}`}>
                  <Icon className="activity-icon-svg" />
                </span>
                <div className="activity-entry-body">
                  <div className="activity-entry-head">
                    <strong>{row.title}</strong>
                    <time>{row.at}</time>
                  </div>
                  {row.detail ? <p>{row.detail}</p> : null}
                </div>
              </article>
            );
          })
        )}
      </div>
      {rows.length > 0 ? (
        <button className="activity-history-btn" type="button">{t("previews.showFullHistory")}</button>
      ) : null}
    </section>
  );
}
