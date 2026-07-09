/** Pixel mockup drawer previews — confirmation / activity / plans empty states.
 *  Verbatim move from App.tsx (R3 refactor). JSX unchanged. */
import IconWarning from "../../../assets/brending/icons/safety/icon-warning.svg?react";
import IconChevronDown from "../../../assets/brending/icons/ui/icon-chevron-down.svg?react";
import IconSend from "../../../assets/brending/icons/voice/icon-send.svg?react";
import IconSuccess from "../../../assets/brending/icons/status/icon-status-success.svg?react";
import IconBackend from "../../../assets/brending/icons/system/icon-backend.svg?react";
import { categoryForActivity } from "../../lib/activityIcons";
import type { ActivityEvent } from "../../lib/realtime";
import type { Plan } from "../../vite-env";

export function ConfirmationPreview() {
  return (
    <div className="pixel-confirmation-preview">
      <div className="pixel-blurred-shell" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <article className="pixel-confirm-card">
        <div className="pixel-warning-icon">
          <IconWarning />
        </div>
        <div className="pixel-confirm-content">
          <h3>Ricky želi izvršiti ovu akciju</h3>
          <p>Pažljivo provjeri detalje prije potvrde.</p>
          <dl className="pixel-confirm-table">
            <div>
              <dt>Akcija</dt>
              <dd>Pošalji email</dd>
            </div>
            <div>
              <dt>Prima</dt>
              <dd>sef@firma.com</dd>
            </div>
            <div>
              <dt>Predmet</dt>
              <dd>Izvještaj o prodaji za prošli mjesec</dd>
            </div>
            <div>
              <dt>Rizik</dt>
              <dd>
                <span className="pixel-risk-badge">SREDNJI</span>
                <span className="pixel-risk-time">ističe za 02:00</span>
              </dd>
            </div>
          </dl>
          <button className="pixel-confirm-link">
            Prikaži cijeli sadržaj emaila <IconChevronDown />
          </button>
          <footer>
            <button>Izmijeni</button>
            <button>Otkaži</button>
            <button className="pixel-confirm-primary">
              <IconSend /> Pošalji email
            </button>
          </footer>
        </div>
      </article>
    </div>
  );
}

export function ActivityDrawerPreview({ activityEvents }: { activityEvents: ActivityEvent[] }) {
  return (
    <aside className="pixel-preview-drawer">
      <header>
        <strong>Aktivnost</strong>
      </header>
      <div className="pixel-preview-list">
        {activityEvents.length > 0 ? (
          activityEvents.slice(0, 5).map((event) => {
            const { Icon, className } = categoryForActivity(event);
            return (
              <article className="pixel-preview-row" key={event.id}>
                <span className={`pixel-preview-icon ${className}`}>
                  <Icon />
                </span>
                <span>
                  <strong>{event.title}</strong>
                  {event.detail ? <small>{event.detail}</small> : null}
                </span>
                <time>{event.at}</time>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title="Još nema aktivnosti" detail="Događaji će se pojaviti ovdje kada Ricky nešto uradi." />
        )}
      </div>
      <button className="pixel-full-history">Prikaži cijelu historiju</button>
    </aside>
  );
}

export function PlansDrawerPreview({ plans }: { plans: Plan[] }) {
  return (
    <aside className="pixel-preview-drawer pixel-preview-plans">
      <header>
        <strong>Planovi</strong>
      </header>
      <div className="pixel-plan-tabs">
        <button className="active">Aktivni</button>
        <button>Predloženi</button>
        <button>Završeni</button>
      </div>
      <div className="pixel-preview-list">
        {plans.length > 0 ? (
          plans.slice(0, 4).map((plan) => {
            const status = planStatusLabel(plan.status);
            return (
              <article className="pixel-plan-row" key={plan.id}>
                <span className={`pixel-preview-icon ${plan.status === "completed" ? "success" : "voice"}`}>
                  {plan.status === "completed" ? <IconSuccess /> : <IconBackend />}
                </span>
                <span>
                  <strong>{plan.title}</strong>
                  <small>{plan.summary || `${plan.steps.length} koraka`}</small>
                </span>
                <em className={status.tone}>{status.label}</em>
              </article>
            );
          })
        ) : (
          <EmptyPreviewState title="Nema aktivnih planova" detail="Napravi novi plan kada želiš da Ricky prati zadatke." />
        )}
      </div>
      <button className="pixel-full-history">Novi plan</button>
    </aside>
  );
}

export function EmptyPreviewState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="pixel-empty-preview">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function planStatusLabel(status: Plan["status"]): { label: string; tone: "active" | "pending" } {
  switch (status) {
    case "approved":
    case "running":
      return { label: "AKTIVAN", tone: "active" };
    case "completed":
      return { label: "ZAVRŠEN", tone: "active" };
    case "rejected":
    case "cancelled":
      return { label: "OTKAZAN", tone: "pending" };
    case "draft":
      return { label: "NACRT", tone: "pending" };
    case "proposed":
    default:
      return { label: "NA ČEKANJU", tone: "pending" };
  }
}
