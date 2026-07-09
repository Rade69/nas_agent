/** Pixel runtime drawer — verbatim move from App.tsx (R3). JSX unchanged. */
import type { ReactNode } from "react";
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
  const titles: Record<Exclude<DrawerState, null>, string> = {
    activity: "Aktivnost",
    plans: "Planovi",
    memory: "Memorija",
    screens: "Snimci ekrana",
    settings: "Postavke",
  };

  return (
    <div className="pixel-drawer-backdrop" onClick={onClose}>
      <aside className={`pixel-drawer pixel-drawer-${drawer}`} onClick={(event) => event.stopPropagation()}>
        <header>
          <strong>{titles[drawer]}</strong>
          <button onClick={onClose} aria-label="Zatvori">
            <IconClose />
          </button>
        </header>
        <div className="pixel-drawer-body">{children}</div>
      </aside>
    </div>
  );
}
