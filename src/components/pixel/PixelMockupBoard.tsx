/** Pixel mockup board (all-sections preview) + MockupSection wrapper.
 *  Verbatim move from App.tsx (R3). JSX unchanged. */
import type { ReactNode } from "react";
import { Sidebar } from "../Sidebar";
import { ActivityTimeline } from "../ActivityTimeline";
import { PlansPanel } from "../PlansPanel";
import { TopBar } from "./TopBar";
import { IdleScreen } from "./IdleScreen";
import { Drawer } from "./Drawer";
import { DictationScreen } from "./DictationScreen";
import { ConfirmationPreview, ActivityDrawerPreview, PlansDrawerPreview } from "./Previews";
import type { ActivityEvent, TranscriptEntry, VoiceState } from "../../lib/realtime";
import type { Plan } from "../../vite-env";
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
  onToggleMode,
  onOpenPlans,
  onSidebarChange,
  onTextPromptChange,
  onSendTextPrompt,
  onVoiceToggle,
  onStop,
  onOpenActivity,
  onQuickCommand,
  onDictationChange,
  onDictationCancel,
  onDictationSend,
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
  onToggleMode: () => void;
  onOpenPlans: () => void;
  onSidebarChange: (id: string) => void;
  onTextPromptChange: (value: string) => void;
  onSendTextPrompt: () => void;
  onVoiceToggle: () => void;
  onStop: () => void;
  onOpenActivity: () => void;
  onQuickCommand: (text: string) => void;
  onDictationChange: (value: string) => void;
  onDictationCancel: () => void;
  onDictationSend: () => void;
  onStopAll: () => void;
  onCloseDrawer: () => void;
  onUpdatePlanStatus: (planId: string, status: string) => Promise<void>;
  onUpdateStepStatus: (planId: string, stepId: string, status: string) => Promise<void>;
  onCreatePlan: () => Promise<void>;
}) {
  return (
    <div className="pixel-mockup-board">
      <MockupSection
        className="pixel-section-idle"
        number="1"
        title="SPREMAN"
        description="Mirno stanje. Fokus na mikrofon i zadnju aktivnost. Sve ostalo dostupno po potrebi."
      >
        <section className="pixel-window pixel-window-idle" aria-label="Spreman">
          <TopBar
            mode={mode}
            screen={screen}
            voiceState={voiceState}
            onToggleMode={onToggleMode}
            onOpenPlans={onOpenPlans}
            onStopAll={onStopAll}
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
                {activeDrawer === "memory" ? <p className="drawer-placeholder-text">Nema sačuvane memorije.</p> : null}
                {activeDrawer === "screens" ? <p className="drawer-placeholder-text">Nema snimaka ekrana.</p> : null}
                {activeDrawer === "settings" ? <p className="drawer-placeholder-text">Postavke nisu dostupne u ovom prikazu.</p> : null}
              </Drawer>
            ) : null}
          </section>
        </section>
      </MockupSection>

      <MockupSection
        className="pixel-section-dictation"
        number="2"
        title="DIKTIRANJE"
        description="Editor je u fokusu. Samo najvažnije akcije. Ostali paneli skriveni."
      >
        <section className="pixel-window pixel-window-dictation" aria-label="Diktiranje">
          <TopBar mode={mode} screen="dictation" voiceState={voiceState} onToggleMode={onToggleMode} onOpenPlans={onOpenPlans} />
          <section className="pixel-main pixel-main-full">
            <DictationScreen
              text={dictationText}
              onChange={onDictationChange}
              onCancel={onDictationCancel}
              onSend={onDictationSend}
            />
          </section>
        </section>
      </MockupSection>

      <MockupSection
        className="pixel-section-confirmation"
        number="3"
        title="POTVRDA"
        description="Dominantna potvrda. Ne može se previdjeti. Detalji jasni, rizik istaknut."
      >
        <ConfirmationPreview />
      </MockupSection>

      <MockupSection
        className="pixel-section-activity"
        number="4"
        title="AKTIVNOST"
        description="Detaljna historija svih događaja i akcija."
      >
        <ActivityDrawerPreview activityEvents={recentActivity} />
      </MockupSection>

      <MockupSection
        className="pixel-section-plans"
        number="5"
        title="PLANOVI"
        description="Tvoji planovi, zadaci i podsjetnici."
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
