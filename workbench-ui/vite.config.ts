import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    // e2e/ belongs to Playwright (pnpm test:e2e), not vitest.
    exclude: [...configDefaults.exclude, "e2e/**"],
    // Fail fast instead of hanging to a CI wall (Wave R brief R0a).
    // A hung worker at teardown was previously an indefinite hang; these
    // caps convert any residual live-handle leak into a loud failure.
    testTimeout: 10_000,
    hookTimeout: 10_000,
    teardownTimeout: 5_000,
  },
});
