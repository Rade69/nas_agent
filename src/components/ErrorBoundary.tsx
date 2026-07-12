import { Component, type ErrorInfo, type ReactNode } from "react";

/** Catches render errors anywhere in the tree below it and shows a fallback
 *  screen instead of a white/blank window. Class component is required —
 *  React error boundaries have no hook equivalent.
 *  Deliberately self-contained (inline styles, no i18n/CSS-file dependency,
 *  no other app state) — if something up the tree broke badly enough to
 *  reach here, the fallback itself must not be able to fail the same way.
 *  Context: agent_reports/2026-07-12_app-review-findings.md */
type ErrorBoundaryState = { error: Error | null };

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary] Uncaught render error:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "14px",
          width: "100vw",
          height: "100vh",
          padding: "24px",
          background: "#050a12",
          color: "#f6f9ff",
          fontFamily: "system-ui, sans-serif",
          textAlign: "center",
        }}
      >
        <strong style={{ fontSize: "18px" }}>Nešto je pošlo po zlu.</strong>
        <p style={{ maxWidth: "420px", color: "#aab8cb", fontSize: "13px", margin: 0 }}>
          Ricky je naišao na grešku i nije mogao normalno prikazati ekran. Ovo se prijavljuje samo lokalno
          (u konzoli), ne šalje se nikuda.
        </p>
        <pre
          style={{
            maxWidth: "560px",
            maxHeight: "160px",
            overflow: "auto",
            padding: "10px 12px",
            borderRadius: "8px",
            background: "rgba(255,255,255,0.05)",
            color: "#ff8197",
            fontSize: "11px",
            textAlign: "left",
          }}
        >
          {this.state.error.message}
        </pre>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: "10px 20px",
            borderRadius: "8px",
            border: "1px solid rgba(80,135,190,0.3)",
            background: "rgba(22,139,255,0.16)",
            color: "#f6f9ff",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Ponovo pokreni
        </button>
      </div>
    );
  }
}
