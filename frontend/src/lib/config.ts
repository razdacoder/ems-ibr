import { getRouteApi } from "@tanstack/react-router";

const root = getRouteApi("__root__");

/** Site, dashboard and API origins for this request (lib/origins.server.ts). */
export function useOrigins() {
  return root.useLoaderData().origins;
}

/** Branding as fetched during the server render, or null if it failed. */
export function useInitialBranding() {
  return root.useLoaderData().branding;
}
