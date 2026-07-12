/** Pixel runtime drawer — verbatim move from App.tsx (R3), later localized
 *  (Localization PR-1, docs/RICKY_GUI_LOCALIZATION_PLAN.md). Titles reuse the
 *  "tabs.*" keys from Sidebar.tsx — same words, one source of truth. */
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import IconClose from "../../../assets/brending/icons/window/icon-close.svg?react";
import type { DrawerState } from "./types";

export function Drawer({
  drawer,
  onClose,
  children,
}: {
  drawer: Exclude<DrawerState, null>;
  onClose: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const titleKeys: Record<Exclude<DrawerState, null>, string> = {
    activity: "tabs.activity",
    plans: "tabs.plans",
    memory: "tabs.memory",
    screens: "tabs.screens",
    settings: "tabs.settings",
  };

  return (
    <div className="pixel-drawer-backdrop" onClick={onClose}>
      <aside className={`pixel-drawer pixel-drawer-${drawer}`} onClick={(event) => event.stopPropagation()}>
        <header>
          <strong>{t(titleKeys[drawer])}</strong>
          <button onClick={onClose} aria-label={t("drawer.close")}>
            <IconClose />
          </button>
        </header>
        <div className="pixel-drawer-body">{children}</div>
      </aside>
    </div>
  );
}
