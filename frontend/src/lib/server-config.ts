import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import type { Branding } from "@/api/system";
import { getFromDjango } from "./django.server";
import { hostKind, origins, requestHost, type HostKind } from "./origins.server";

/*
 * App-wide config for the root route, resolved on the server per request:
 * which part of Ordo this host is, the origins, and the school's branding
 * (so the first paint is on-brand). Nothing is cached across requests: the
 * next one may be a different school.
 */

/** Host kind, origins and branding for this request. */
export const getConfig = createServerFn({ method: "GET" }).handler(async () => {
  const request = getRequest();
  const where = requestHost(request);
  let host: HostKind = hostKind(where.host);
  let branding: Branding | null = null;

  // The console has no school, so no branding. A would be school asks
  // Django, which answers 404 for an unknown or purged one.
  if (host === "school") {
    try {
      const res = await getFromDjango<Branding>("/system/branding/", where);
      if (res.status === 404) host = "unknown";
      else if (res.status === 200) branding = res.body;
      else throw new Error(`GET /system/branding/ → ${res.status}`);
    } catch (err) {
      // Branding is decoration: render the stock Ordo look rather than fail.
      console.error("branding fetch failed", err);
    }
  }
  return { host, origins: origins(request), branding };
});
