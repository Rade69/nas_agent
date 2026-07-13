/** Pixel sidebar navigation — home, activity, plans, memory, screens,
 *  settings. Indicates the current screen and opens drawers. Localized
 *  via i18next (Localization PR-1).
 *  Context: agent_reports/2026-07-11_i18n-foundation.md */
import { useTranslation } from "react-i18next";
import IconHome from "../../assets/brending/icons/navigation/icon-home.svg?react";
import IconActivity from "../../assets/brending/icons/navigation/icon-activity.svg?react";
import IconPlans from "../../assets/brending/icons/navigation/icon-plans.svg?react";
import IconMemory from "../../assets/brending/icons/navigation/icon-memory.svg?react";
import IconScreenshots from "../../assets/brending/icons/navigation/icon-screenshots.svg?react";
import IconSettings from "../../assets/brending/icons/navigation/icon-settings.svg?react";

type SidebarProps = {
  activeTab: string;
  onTabChange: (tab: string) => void;
  backendConnected: boolean;
};

// Localized labels (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md) —
// keys live in src/i18n/locales/*.json under "tabs.*".
const NAV_ITEMS: { id: string; labelKey: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "home", labelKey: "tabs.home", Icon: IconHome },
  { id: "activity", labelKey: "tabs.activity", Icon: IconActivity },
  { id: "plans", labelKey: "tabs.plans", Icon: IconPlans },
  { id: "memory", labelKey: "tabs.memory", Icon: IconMemory },
  { id: "screens", labelKey: "tabs.screens", Icon: IconScreenshots },
  { id: "settings", labelKey: "tabs.settings", Icon: IconSettings },
];

export function Sidebar({ activeTab, onTabChange, backendConnected }: SidebarProps) {
  const { t } = useTranslation();
  return (
    <nav className="sidebar">
      <div className="sidebar-nav">
        {NAV_ITEMS.map(({ id, labelKey, Icon }) => (
          <button
            key={id}
            className={`sidebar-item${activeTab === id ? " active" : ""}`}
            onClick={() => onTabChange(id)}
          >
            <Icon className="sidebar-item-icon" />
            <span>{t(labelKey)}</span>
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        {/* Real app version from package.json (1.0.0) — not the mockup's
            illustrative "v0.4.0" placeholder, which isn't a real release number. */}
        <div className="sidebar-footer-version">Ricky v1.0.0</div>
        <div className="sidebar-footer-backend">
          <span className={`sidebar-backend-dot ${backendConnected ? "connected" : "disconnected"}`} />
          <span>{backendConnected ? t("sidebar.backendConnected") : t("sidebar.backendDisconnected")}</span>
        </div>
      </div>
    </nav>
  );
}