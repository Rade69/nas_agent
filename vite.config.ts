import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

// FAZA S-3 (docs/SECURITY_GAP_ANALYSIS_AND_PLAN.md): Content-Security-Policy for
// the packaged renderer. The production app is loaded via loadFile(dist/index
// .html) over file://, and Electron's onHeadersReceived does NOT fire for
// file:// documents — so a response-header CSP can't cover the prod document.
// A <meta http-equiv> tag is the reliable mechanism for a file://-loaded page,
// injected at build time only so it never touches the Vite dev server (which
// the developer runs constantly and which needs inline/eval + ws for HMR).
//
// connect-src is intentionally tight: the renderer's only external egress is
// the OpenAI Realtime SDP exchange (src/lib/realtime.ts). Everything else
// (backend) goes through Electron IPC, never a direct fetch. 'wasm-unsafe-eval'
// is allowed for diagram/math libs (mermaid/katex) that may compile wasm;
// full 'unsafe-eval' is deliberately NOT granted.
const PROD_CSP = [
  "default-src 'self'",
  "script-src 'self' 'wasm-unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "media-src 'self' blob: mediastream:",
  "connect-src 'self' https://api.openai.com https://*.openai.com wss://*.openai.com",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-src 'none'",
  "form-action 'none'",
].join("; ");

function cspMetaPlugin() {
  return {
    name: "ricky-inject-csp-meta",
    apply: "build" as const,
    transformIndexHtml() {
      return [
        {
          tag: "meta",
          attrs: { "http-equiv": "Content-Security-Policy", content: PROD_CSP },
          injectTo: "head-prepend" as const,
        },
      ];
    },
  };
}

export default defineConfig({
  plugins: [react(), svgr(), cspMetaPlugin()],
  server: {
    host: "127.0.0.1",
    port: 5173,
  },
});
