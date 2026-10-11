/**
 * Where this request is, and who it's for. One dashboard build serves every
 * host under PLATFORM_BASE_DOMAIN (spec 0003, child 0002):
 *
 *   <slug>.<base>  — a school's dashboard
 *   console.<base>   — the platform console
 *   anything else  — not found
 *
 * Traefik sends /api, /ws and /media on the same host to Django, so the API
 * origin is the page's own origin (PUBLIC_API_URL overrides it). The
 * marketing site can't be derived, so it's only linked to when SITE_URL is set.
 */

export interface Origins {
  /** The marketing site, or null when SITE_URL isn't set. */
  site: string | null;
  /** Django as the browser reaches it. */
  api: string;
}

/** Which part of Ordo this host serves. */
export type HostKind = "school" | "console" | "unknown";

function trim(url: string): string {
  return url.replace(/\/+$/, "");
}

/**
 * The host the browser asked for. Never X-Forwarded-Host: Django picks the
 * school from the real Host header, and so must this.
 */
export function requestHost(request: Request): { proto: string; host: string } {
  const url = new URL(request.url);
  return {
    proto:
      request.headers.get("x-forwarded-proto") ?? url.protocol.replace(":", ""),
    host: request.headers.get("host") ?? url.host,
  };
}

export function origins(request: Request): Origins {
  const { proto, host } = requestHost(request);
  const env = process.env;
  return {
    site: env.SITE_URL ? trim(env.SITE_URL) : null,
    api: env.PUBLIC_API_URL ? trim(env.PUBLIC_API_URL) : `${proto}://${host}`,
  };
}

/**
 * Console, a would be school, or neither, from the host alone. Whether the
 * school exists is Django's call (lib/server-config.ts asks it).
 */
export function hostKind(host: string): HostKind {
  const base = (process.env.PLATFORM_BASE_DOMAIN ?? "localhost").toLowerCase();
  const consoleLabel = (process.env.PLATFORM_CONSOLE_SUBDOMAIN ?? "console").toLowerCase();
  const name = host.toLowerCase().replace(/:\d+$/, "");
  if (name === `${consoleLabel}.${base}`) return "console";
  const label = name.endsWith(`.${base}`) ? name.slice(0, -base.length - 1) : "";
  return /^[a-z0-9-]+$/.test(label) ? "school" : "unknown";
}
