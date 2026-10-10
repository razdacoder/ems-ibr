import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Unit and component tests. Kept apart from vite.config.ts so the TanStack
// Start and Nitro plugins (and the Django dev proxy) stay out of the test run.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
