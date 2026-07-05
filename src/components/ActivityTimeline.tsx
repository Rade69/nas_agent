import type { ActivityEvent } from "../lib/voiceState";
import type { TranscriptEntry } from "../lib/realtime";

type ActivityTimelineProps = {
  transcript: TranscriptEntry[];
  activityEvents: ActivityEvent[];
};

export function ActivityTimeline({ transcript, activityEvents }: ActivityTimelineProps) {
  const rows = [
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
      title: entry.role === "ricky" ? "Ricky" : entry.role,
      detail: entry.text,
      at: entry.at,
    })),
  ].slice(0, 90);

  return (
    <section className="transcript activity-timeline">
      <div className="section-title">
        <span>Activity</span>
        <small>{rows.length} events</small>
      </div>
      <div className="transcript-list">
        {rows.map((row) => (
          <article className={`entry entry-${row.kind}`} key={row.id}>
            <div>
              <strong>{row.title}</strong>
              <time>{row.at}</time>
            </div>
            {row.detail ? <p>{row.detail}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}