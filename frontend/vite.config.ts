import { defineConfig, loadEnv } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Ordo dashboard: TanStack Start on Node (Nitro), on the apex domain
// (ordo.app), rendered in the browser (ssr: false). Django is a separate
// service on api.ordo.app that the browser calls directly; the marketing
// site is a separate repo on its own domain (SITE_URL). Server-side env
// (API_URL, PUBLIC_API_URL, SITE_URL) comes from the process in production;
// in dev, .env.development fills it in. Dev: http://localhost:3000.
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
