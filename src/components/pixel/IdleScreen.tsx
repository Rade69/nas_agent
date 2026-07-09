/** Pixel idle/ready screen — verbatim move from App.tsx (R3). JSX unchanged. */
import IconStop from "../../../assets/brending/icons/voice/icon-stop.svg?react";
import IconMicOff from "../../../assets/brending/icons/voice/icon-microphone-muted.svg?react";
import IconMic from "../../../assets/brending/icons/voice/icon-microphone.svg?react";
import IconSend from "../../../assets/brending/icons/voice/icon-send.svg?react";
import IconChevronRight from "../../../assets/brending/icons/ui/icon-chevron-right.svg?react";
import IconScreenshot from "../../../assets/brending/icons/actions/icon-screenshot.svg?react";
import IconOpenApp from "../../../assets/brending/icons/actions/icon-open-app.svg?react";
import IconCalendar from "../../../assets/brending/icons/actions/icon-calendar.svg?react";
import { RickyOrb } from "../RickyOrb";
import { categoryForActivity } from "../../lib/activityIcons";
import { EmptyPreviewState } from "./Previews";
import type { ActivityEvent, VoiceState } from "../../lib/realtime";

export function IdleScreen({
  voiceState,
  isActive,
  isConnected,
  textPrompt,
  recentActivity,
  onTextPromptChange,
  onSendTextPrompt,
  onVoiceToggle,
  onStop,
  onOpenActivity,
  onQuickCommand,
}: {
  voiceState: VoiceState;
  isActive: boolean;
  isConnected: boolean;
  textPrompt: string;
  recentActivity: ActivityEvent[];
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
}) {
  return (
    <div className="pixel-idle">
      <section className="pixel-hero">
        <RickyOrb voiceState={voiceState} />
        <h1>Ricky je spreman</h1>
        <p>Klikni mikrofon ili reci "Ricky"</p>
        <button
          className={`pixel-mic-button ${isActive ? "stop" : ""}`}
          onClick={isActive ? onStop : onVoiceToggle}
          title={isActive ? "Stop" : isConnected ? "Prekini vezu" : "Pokreni glas"}
        >
          {isActive ? <IconStop /> : isConnected ? <IconMicOff /> : <IconMic />}
        </button>
        <div className="pixel-prompt">
          <input
            value={textPrompt}
            onChange={(event) => onTextPromptChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSendTextPrompt();
            }}
            placeholder="Upiši umjesto govora..."
          />
          <button onClick={onSendTextPrompt} aria-label="Pošalji tekst">
            <IconSend />
          </button>
        </div>
      </section>
      <aside className="pixel-idle-side">
        <section className="pixel-card pixel-activity-card">
          <header>
            <h2>Zadnja aktivnost</h2>
            <button onClick={onOpenActivity}>Prikaži sve</button>
          </header>
          <div className="pixel-list">
            {recentActivity.length > 0 ? (
              recentActivity.slice(0, 4).map((event) => {
                const { Icon, className } = categoryForActivity(event);
                return (
                  <article className="pixel-list-row" key={event.id}>
                    <span className={`pixel-row-icon ${className}`}>
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
              <EmptyPreviewState title="Nema aktivnosti" detail="Historija će se popuniti kada pokreneš glas ili alat." />
            )}
          </div>
        </section>
        <section className="pixel-card pixel-command-card">
          <header>
            <h2>Brze komande</h2>
          </header>
          <button onClick={() => onQuickCommand("Napiši email šefu")}>
            <IconChevronRight /> Napiši email šefu
          </button>
          <button onClick={() => onQuickCommand("Napravi screenshot")}>
            <IconScreenshot /> Napravi screenshot
          </button>
          <button onClick={() => onQuickCommand("Otvori Notepad")}>
            <IconOpenApp /> Otvori Notepad
          </button>
          <button onClick={() => onQuickCommand("Planiraj sastanak sutra u 10h")}>
            <IconCalendar /> Planiraj sastanak sutra u 10h
          </button>
        </section>
      </aside>
    </div>
  );
}
