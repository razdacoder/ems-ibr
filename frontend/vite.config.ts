import { defineConfig, loadEnv } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { djangoDevProxy } from "./django-dev-proxy";

// Ordo dashboard: TanStack Start on Node (Nitro), rendered in the browser
// (ssr: false). One build serves every school (<slug>.<base>) and the console
// (console.<base>); Traefik sends /api, /ws and /media on the same host to
// Django. The marketing site is a separate repo (SITE_URL). Server-side env
// (API_URL, PLATFORM_BASE_DOMAIN, SITE_URL) comes from the process in
// production; in dev, .env.development fills it in.
//
// Dev: http://<slug>.localhost:3000 (e.g. after `manage.py create_school
// demo`) and http://console.localhost:3000. djangoDevProxy stands in for
// Traefik and keeps the Host header, so Django sees which school is asking.
export default defineConfig(({ mode }) => {
  Object.assign(process.env, loadEnv(mode, process.cwd(), ""), process.env);
  return {
    plugins: [
      // First, so its routes are mounted before Nitro's catch all.
      djangoDevProxy("http://localhost:8000", ["/api", "/ws", "/media"]),
      tailwindcss(),
      tanstackStart(),
      nitro(),
      react(),
    ],
    resolve: {
      alias: { "@": new URL("./src", import.meta.url).pathname },
    },
    server: { port: 3000 },
  };
});
