import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { CompanionOrb } from "./components/CompanionOrb";
import "./i18n";
import "./styles.css";

// FAZA 12: Companion orb is a separate renderer entry mounted when the window
// is loaded with ?view=companion. The orb receives VoiceState over IPC from
// the main process (forwarded from the main window's Realtime client). The orb
// itself never runs an audio pipeline — there is exactly one (src/lib/realtime.ts
// in the main window) per ARCHITECTURE_VOICE_FIRST_REVISED.md.
const params = new URLSearchParams(window.location.search);
const view = params.get("view");

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {view === "companion" ? <CompanionOrb /> : <App />}
  </React.StrictMode>,
);
