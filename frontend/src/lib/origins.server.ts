/**
 * One app, three hosts:
 *
 *   ordo.app      — marketing site (SSR)
 *   app.ordo.app  — dashboard (client-rendered)
 *   api.ordo.app  — Django (REST + WebSockets), a separate service
 *
 * Each origin is derived from the host the request came in on, so one build
 * serves any domain (localhost / app.localhost in dev). SITE_URL, APP_URL
 * and PUBLIC_API_URL override the derivation when the hosts don't follow
 * that pattern.
 */

export const APP_PREFIX = "app.";

export interface Origins {
  site: string;
  app: string;
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

export function isAppHost(host: string): boolean {
  return host.startsWith(APP_PREFIX);
}

export function origins(request: Request): Origins {
  const { proto, host } = requestHost(request);
  const bare = host.replace(/^(app|www)\./, "");
  const env = process.env;
  return {
    site: env.SITE_URL ? trim(env.SITE_URL) : `${proto}://${bare}`,
    app: env.APP_URL ? trim(env.APP_URL) : `${proto}://${APP_PREFIX}${bare}`,
    api: env.PUBLIC_API_URL ? trim(env.PUBLIC_API_URL) : `${proto}://api.${bare}`,
  };
}
