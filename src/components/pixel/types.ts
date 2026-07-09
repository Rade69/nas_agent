/** Shared pixel UI types — kept here to avoid a circular import between
 *  App.tsx and the extracted pixel components (both import these). */

export type RickyMode = "display" | "computer";
export type ScreenState = "home" | "dictation";
export type DrawerState = "activity" | "plans" | "memory" | "screens" | "settings" | null;
