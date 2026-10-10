/**
 * The dashboard's neighbours:
 *
 *   ordo.app      — this dashboard (client-rendered)
 *   api.ordo.app  — Django (REST + WebSockets), a separate service
 *   SITE_URL      — the marketing site, a separate repo on its own domain
 *
 * The API origin is derived from the host the request came in on (api. of
 * the bare host), so one build serves any domain; PUBLIC_API_URL overrides
 * it. The site can't be derived, so it's only linked to when SITE_URL is set.
 */

export interface Origins {
  /** The marketing site, or null when SITE_URL isn't set. */
  site: string | null;
  /** Django as the browser reaches it. */
  api: string;
}

function trim(url: string): string {
  return url.replace(/\/+$/, "");
}

export function requestHost(request: Request): { proto: string; host: string } {
  const url = new URL(request.url);
  return {
    proto:
      request.headers.get("x-forwarded-proto") ?? url.protocol.replace(":", ""),
    host: request.headers.get("x-forwarded-host") ?? url.host,
  };
}

export function origins(request: Request): Origins {
  const { proto, host } = requestHost(request);
  const bare = host.replace(/^www\./, "");
  const env = process.env;
  return {
    site: env.SITE_URL ? trim(env.SITE_URL) : null,
    api: env.PUBLIC_API_URL ? trim(env.PUBLIC_API_URL) : `${proto}://api.${bare}`,
  };
}
