/** Pixel mockup board (all-sections preview) + MockupSection wrapper.
 *  Verbatim move from App.tsx (R3), later localized (Localization PR-1,
 *  docs/RICKY_GUI_LOCALIZATION_PLAN.md). */
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Sidebar } from "../Sidebar";
import { ActivityTimeline } from "../ActivityTimeline";
import { PlansPanel } from "../PlansPanel";
import { TopBar } from "./TopBar";
import { IdleScreen } from "./IdleScreen";
import { Drawer } from "./Drawer";
import { DictationScreen } from "./DictationScreen";
import { SettingsPanel } from "./SettingsPanel";
import { ConfirmationPreview, ActivityDrawerPreview, PlansDrawerPreview } from "./Previews";
import type { ActivityEvent, TranscriptEntry, VoiceState } from "../../lib/realtime";
import type { Confirmation, Plan, TextRewriteOperation } from "../../vite-env";
import type { DrawerState, RickyMode, ScreenState } from "./types";

export function PixelMockupBoard({
  mode,
  screen,
  voiceState,
  isActive,
  isConnected,
  textPrompt,
  dictationText,
  recentActivity,
  activityEvents,
  transcript,
  plans,
  activeDrawer,
  backendConnected,
  busyPlanId,
  busyStepId,
  pendingConfirmation,
  onToggleMode,
  onOpenPlans,
  onSidebarChange,
  onTextPromptChange,
  onSendTextPrompt,
  onVoiceToggle,
  onStop,
  onOpenActivity,
  onQuickCommand,
  onEnterDictation,
  onDictationChange,
  onDictationCancel,
  onDictationSend,
  onDictationContinue,
  onDictationRewrite,
  onDictationCopy,
  onDictationClear,
  onDictationUndo,
  onDictationDownload,
  dictationBusy,
  canUndoDictation,
  onStopAll,
  onCloseDrawer,
  onUpdatePlanStatus,
  onUpdateStepStatus,
  onCreatePlan,
}: {
  mode: RickyMode;
  screen: ScreenState;
  voiceState: VoiceState;
  isActive: boolean;
  isConnected: boolean;
  textPrompt: string;
  dictationText: string;
  recentActivity: ActivityEvent[];
  activityEvents: ActivityEvent[];
  transcript: TranscriptEntry[];
  plans: Plan[];
  activeDrawer: DrawerState;
  backendConnected: boolean;
  busyPlanId: string | null;
  busyStepId: string | null;
  pendingConfirmation: Confirmation | null;
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onSidebarChange: (id: string) => void;
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
  onEnterDictation: () => void;
  onDictationChange: (value: string) => void;
  onDictationCancel: () => void;
  onDictationSend: () => void;
  onDictationContinue: () => void;
  onDictationRewrite: (operation: TextRewriteOperation) => void;
  onDictationCopy: () => void;
  onDictationClear: () => void;
  onDictationUndo: () => void;
  onDictationDownload: () => void;
  dictationBusy: boolean;
  canUndoDictation: boolean;
  onStopAll: () => void;
  onCloseDrawer: () => void;
  onUpdatePlanStatus: (planId: string, status: string) => Promise<void>;
  onUpdateStepStatus: (planId: string, stepId: string, status: string) => Promise<void>;
  onCreatePlan: () => Promise<void>;
}) {
  const { t } = useTranslation();
  return (
    <div className="pixel-mockup-board">
      {/* Idle and Dictation are mutually exclusive main-area modes — you can't
          be both at once (unlike Confirmation/Activity/Plans below, which are
          independent glanceable info panels that legitimately coexist).
          Context: agent_reports/2026-07-10_dictation-and-dashboard-fixes.md */}
      {screen === "dictation" ? (
        <MockupSection
          className="pixel-section-main"
          number="2"
          title={t("dashboard.dictationTitle")}
          description={t("dashboard.dictationDescription")}
        >
          <section className="pixel-window pixel-window-dictation" aria-label={t("topBar.dictation")}>
            <TopBar mode={mode} screen="dictation" voiceState={voiceState} onToggleMode={onToggleMode} onOpenPlans={onOpenPlans} />
            <section className="pixel-main pixel-main-full">
              <DictationScreen
                text={dictationText}
                onChange={onDictationChange}
                onCancel={onDictationCancel}
                onSend={onDictationSend}
                onContinue={onDictationContinue}
                onRewrite={onDictationRewrite}
                onCopy={onDictationCopy}
                onClear={onDictationClear}
                onUndo={onDictationUndo}
                onDownload={onDictationDownload}
                busy={dictationBusy}
                canUndo={canUndoDictation}
              />
            </section>
          </section>
        </MockupSection>
      ) : (
        <MockupSection
          className="pixel-section-main"
          number="1"
          title={t("dashboard.readyTitle")}
          description={t("dashboard.readyDescription")}
        >
          <section className="pixel-window pixel-window-idle" aria-label={t("voice.state.idle")}>
            <TopBar
              mode={mode}
              screen={screen}
              voiceState={voiceState}
              onToggleMode={onToggleMode}
              onOpenPlans={onOpenPlans}
              onStopAll={onStopAll}
              onEnterDictation={onEnterDictation}
            />
            <Sidebar activeTab={activeDrawer ?? screen} onTabChange={onSidebarChange} backendConnected={backendConnected} />
            <section className="pixel-main">
              <IdleScreen
                voiceState={voiceState}
                isActive={isActive}
                isConnected={isConnected}
                textPrompt={textPrompt}
                recentActivity={recentActivity}
                onTextPromptChange={onTextPromptChange}
                onSendTextPrompt={onSendTextPrompt}
                onVoiceToggle={onVoiceToggle}
                onStop={onStop}
                onOpenActivity={onOpenActivity}
                onQuickCommand={onQuickCommand}
              />
              {activeDrawer ? (
                <Drawer drawer={activeDrawer} onClose={onCloseDrawer}>
                  {activeDrawer === "activity" ? (
                    <ActivityTimeline transcript={transcript} activityEvents={activityEvents} />
                  ) : null}
                  {activeDrawer === "plans" ? (
                    <PlansPanel
                      visible={true}
                      plans={plans}
                      busyPlanId={busyPlanId}
                      busyStepId={busyStepId}
                      onUpdatePlanStatus={onUpdatePlanStatus}
                      onUpdateStepStatus={onUpdateStepStatus}
                      onCreatePlan={onCreatePlan}
                    />
                  ) : null}
                  {activeDrawer === "memory" ? <p className="drawer-placeholder-text">{t("dashboard.noMemory")}</p> : null}
                  {activeDrawer === "screens" ? <p className="drawer-placeholder-text">{t("dashboard.noScreenshots")}</p> : null}
                  {activeDrawer === "settings" ? <SettingsPanel /> : null}
                </Drawer>
              ) : null}
            </section>
          </section>
        </MockupSection>
      )}

      <MockupSection
        className="pixel-section-confirmation"
        number="3"
        title={t("dashboard.confirmationTitle")}
        description={t("dashboard.confirmationDescription")}
      >
        <ConfirmationPreview confirmation={pendingConfirmation} />
      </MockupSection>

      <MockupSection
        className="pixel-section-activity"
        number="4"
        title={t("dashboard.activityTitle")}
        description={t("dashboard.activityDescription")}
      >
        <ActivityDrawerPreview activityEvents={recentActivity} />
      </MockupSection>

      <MockupSection
        className="pixel-section-plans"
        number="5"
        title={t("dashboard.plansTitle")}
        description={t("dashboard.plansDescription")}
      >
        <PlansDrawerPreview plans={plans} />
      </MockupSection>

    </div>
  );
}

export function MockupSection({
  number,
  title,
  description,
  className,
  children,
}: {
  number?: string;
  title?: string;
  description?: string;
  className: string;
  children: ReactNode;
}) {
  return (
    <section className={`pixel-mockup-section ${className}`}>
      {title ? (
        <header className="pixel-section-label">
          <h2>{number ? `${number}. ${title}` : title}</h2>
          {description ? <p>{description}</p> : null}
        </header>
      ) : null}
      {children}
    </section>
  );
}
