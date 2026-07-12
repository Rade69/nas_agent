/** Pixel idle/ready screen — verbatim move from App.tsx (R3), later localized
 *  (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md). Quick command
 *  button text is also the literal text sent via onQuickCommand — translating
 *  the label naturally translates the command sent, consistent with the
 *  "Prefer replying in languageName" prompt addition
 *  (agent_reports/2026-07-11_dictation-language-cascade.md). */
import { useTranslation } from "react-i18next";
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
  quickCommands,
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
  // Empty = show the 4 built-in localized defaults below. Non-empty = user
  // has customized their own list in Settings, use exactly that instead.
  // Context: agent_reports/2026-07-12_custom-quick-commands.md
  quickCommands: string[];
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
}) {
  const { t } = useTranslation();
  // Hero text was static ("Ricky je spreman") regardless of voiceState — the
  // header (voiceStateLabel()) already updates live per state, but this big
  // central heading never did, so it visibly contradicted the header outside
  // "idle" (e.g. header says "Slušam" while this still said "Ricky je
  // spreman"). Header stays the short machine-state label; this is the
  // human-friendly, live counterpart — deliberately different wording, not
  // a copy of the header text. Context: agent_reports/2026-07-12_hero-text-state-aware.md
  const heroTitle = voiceState === "idle" ? t("idle.ready") : t(`idle.state.${voiceState}.title`);
  const heroHint = voiceState === "idle" ? t("idle.hint") : t(`idle.state.${voiceState}.hint`);
  return (
    <div className="pixel-idle">
      <section className="pixel-hero">
        <RickyOrb voiceState={voiceState} />
        <h1>{heroTitle}</h1>
        {heroHint ? <p>{heroHint}</p> : null}
        <button
          className={`pixel-mic-button ${isActive ? "stop" : ""}`}
          onClick={isActive ? onStop : onVoiceToggle}
          title={isActive ? t("idle.stop") : isConnected ? t("idle.disconnect") : t("idle.startVoice")}
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
            placeholder={t("idle.promptPlaceholder")}
          />
          <button onClick={onSendTextPrompt} aria-label={t("idle.sendText")}>
            <IconSend />
          </button>
        </div>
      </section>
      <aside className="pixel-idle-side">
        <section className="pixel-card pixel-activity-card">
          <header>
            <h2>{t("idle.recentActivity")}</h2>
            <button onClick={onOpenActivity}>{t("idle.showAll")}</button>
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
              <EmptyPreviewState title={t("idle.noActivity")} detail={t("idle.noActivityDetail")} />
            )}
          </div>
        </section>
        <section className="pixel-card pixel-command-card">
          <header>
            <h2>{t("idle.quickCommands")}</h2>
          </header>
          {quickCommands.length > 0 ? (
            quickCommands.map((command, index) => (
              <button key={`${index}-${command}`} onClick={() => onQuickCommand(command)}>
                <IconChevronRight /> {command}
              </button>
            ))
          ) : (
            <>
              <button onClick={() => onQuickCommand(t("idle.cmdEmail"))}>
                <IconChevronRight /> {t("idle.cmdEmail")}
              </button>
              <button onClick={() => onQuickCommand(t("idle.cmdScreenshot"))}>
                <IconScreenshot /> {t("idle.cmdScreenshot")}
              </button>
              <button onClick={() => onQuickCommand(t("idle.cmdNotepad"))}>
                <IconOpenApp /> {t("idle.cmdNotepad")}
              </button>
              <button onClick={() => onQuickCommand(t("idle.cmdMeeting"))}>
                <IconCalendar /> {t("idle.cmdMeeting")}
              </button>
            </>
          )}
        </section>
      </aside>
    </div>
  );
}
