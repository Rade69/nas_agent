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

const NAV_ITEMS: { id: string; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "home", label: "Početna", Icon: IconHome },
  { id: "activity", label: "Aktivnost", Icon: IconActivity },
  { id: "plans", label: "Planovi", Icon: IconPlans },
  { id: "memory", label: "Memorija", Icon: IconMemory },
  { id: "screens", label: "Snimci ekrana", Icon: IconScreenshots },
  { id: "settings", label: "Postavke", Icon: IconSettings },
];

export function Sidebar({ activeTab, onTabChange, backendConnected }: SidebarProps) {
  return (
    <nav className="sidebar">
      <div className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, Icon }) => (
          <button
            key={id}
            className={`sidebar-item${activeTab === id ? " active" : ""}`}
            onClick={() => onTabChange(id)}
          >
            <Icon className="sidebar-item-icon" />
            <span>{label}</span>
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        {/* Real app version from package.json (1.0.0) — not the mockup's
            illustrative "v0.4.0" placeholder, which isn't a real release number. */}
        <div className="sidebar-footer-version">Ricky v1.0.0</div>
        <div className="sidebar-footer-backend">
          <span className={`sidebar-backend-dot ${backendConnected ? "connected" : "disconnected"}`} />
          <span>{backendConnected ? "Backend: OK · Lokalno" : "Backend: offline"}</span>
        </div>
      </div>
    </nav>
  );
}