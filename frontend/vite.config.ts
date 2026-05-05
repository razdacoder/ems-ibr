import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production the Django container serves the build output via WhiteNoise
// from /static/, so emitted asset URLs need that prefix. In dev, Vite serves
// from /, with /api and /ws proxied to the Django dev server.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/static/" : "/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
}));
