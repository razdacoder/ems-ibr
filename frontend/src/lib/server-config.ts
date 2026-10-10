import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import type { Branding } from "@/api/system";
import { origins } from "./origins.server";

/*
 * App-wide config for the root route, resolved on the server. Branding is
 * fetched from Django's public endpoint so the first paint is on-brand.
 * API_URL is Django as this server reaches it — possibly an internal
 * address — not necessarily what the browser uses.
 */

function apiUrl(path: string): string {
  const base = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  return `${base}/api${path}`;
}

/** The site and API origins, and branding. */
export const getConfig = createServerFn({ method: "GET" }).handler(async () => {
  let branding: Branding | null = null;
  try {
    const res = await fetch(apiUrl("/system/branding/"), {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`GET /system/branding/ → ${res.status}`);
    branding = (await res.json()) as Branding;
  } catch (err) {
    // Branding is decoration — render the stock Ordo look rather than fail.
    console.error("branding fetch failed", err);
  }
  return { origins: origins(getRequest()), branding };
});
