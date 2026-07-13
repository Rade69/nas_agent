import { defineConfig } from "vitest/config";

/** Vitest configuration for voice-reliability unit tests (R0).
 *  Matches the project's existing Vite/TypeScript setup.
 *  Context: docs/VOICE_COMMUNICATION_RELIABILITY_IMPLEMENTATION_PLAN_FOR_PI.md */
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    environment: "node",
    globals: false,
  },
});
