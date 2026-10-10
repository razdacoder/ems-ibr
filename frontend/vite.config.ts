import { defineConfig, loadEnv } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// One TanStack Start app on Node (Nitro) serving two hosts:
//   ordo.app      — marketing site, server-rendered
//   app.ordo.app  — dashboard, rendered in the browser (ssr: false)
// Host routing lives in src/start.ts. Django is a separate service on
// api.ordo.app that the browser calls directly. Server-side env (API_URL,
// PUBLIC_API_URL, …) comes from the process in production; in dev,
// .env.development fills it in. Dev: http://ordo.localhost:3000 is the
// site, http://app.ordo.localhost:3000 the dashboard (plain localhost /
// app.localhost work too, but can't share the theme cookie).
export default defineConfig(({ mode }) => {
  Object.assign(process.env, loadEnv(mode, process.cwd(), ""), process.env);
  return {
    plugins: [tailwindcss(), tanstackStart(), nitro(), react()],
    resolve: {
      alias: { "@": new URL("./src", import.meta.url).pathname },
    },
    server: { port: 3000 },
  };
});
