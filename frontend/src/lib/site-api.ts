import { notFound } from "@tanstack/react-router";
import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import type { Branding } from "@/api/system";
import { origins } from "./origins.server";

/*
 * Server functions for data the app needs at render time, fetched from
 * Django's public endpoints on the server so marketing pages arrive rendered
 * (and crawlable). API_URL is Django as this server reaches it — possibly an
 * internal address — not necessarily what the browser uses.
 */

export interface FeatureSummary {
  slug: string;
  title: string;
  subtitle: string;
  icon: string | null;
}

export interface Feature extends FeatureSummary {
  overview: string;
  capabilities: string[];
  how_it_works: string[];
  benefits: string[];
}

function apiUrl(path: string): string {
  const base = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  return `${base}/api${path}`;
}

async function getJson<T>(path: string): Promise<T | null> {
  const res = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return (await res.json()) as T;
}

/** App-wide data for the root route: the three origins, and branding. */
export const getConfig = createServerFn({ method: "GET" }).handler(async () => {
  let branding: Branding | null = null;
  try {
    branding = await getJson<Branding>("/system/branding/");
  } catch (err) {
    // Branding is decoration — render the stock Ordo look rather than fail.
    console.error("branding fetch failed", err);
  }
  return { origins: origins(getRequest()), branding };
});

export const getFeatures = createServerFn({ method: "GET" }).handler(async () => {
  const data = await getJson<{ results: FeatureSummary[] }>("/public/features/");
  return data?.results ?? [];
});

export const getFeature = createServerFn({ method: "GET" })
  .validator((slug: string) => slug)
  .handler(async ({ data: slug }) => {
    const feature = await getJson<Feature>(`/public/features/${encodeURIComponent(slug)}/`);
    if (!feature) throw notFound();
    return feature;
  });
