import {
  createCsrfMiddleware,
  createMiddleware,
  createStart,
} from "@tanstack/react-start";
import { isAppHost, origins, requestHost } from "@/lib/origins.server";

// Marketing-site pages, as public URLs (internally under /site — see
// router.tsx). Everything else is the dashboard.
function isSitePath(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname === "/features" ||
    pathname.startsWith("/features/")
  );
}

/** "/site/features" → "/features": the router's internal prefix, never public. */
function stripSitePrefix(pathname: string): string | null {
  if (pathname === "/site" || pathname.startsWith("/site/")) {
    return pathname.slice("/site".length) || "/";
  }
  return null;
}

/**
 * Keeps each host to its own pages. Only page loads are steered —
 * server-function calls, assets and dev-server modules pass straight through.
 *
 *   app host:  /features…   → same path on the site
 *              /dashboard   → / (the dashboard's old home)
 *   site host: anything that isn't a site page (an old ordo.app/login
 *              bookmark) → same path on the app host, query string intact
 *   either:    /site/…      → the public site URL
 */
const hostRouting = createMiddleware().server(({ request, next }) => {
  const isPage =
    request.method === "GET" &&
    (request.headers.get("accept") ?? "").includes("text/html");
  if (!isPage) return next();

  const { pathname, search } = new URL(request.url);
  const { host } = requestHost(request);
  const to = origins(request);

  const sitePath = stripSitePrefix(pathname);
  if (sitePath !== null) return Response.redirect(to.site + sitePath + search, 302);

  if (isAppHost(host)) {
    if (pathname !== "/" && isSitePath(pathname)) {
      return Response.redirect(to.site + pathname + search, 302);
    }
    if (pathname === "/dashboard") return Response.redirect(`${to.app}/${search}`, 302);
  } else if (!isSitePath(pathname)) {
    return Response.redirect(to.app + pathname + search, 302);
  }
  return next();
});

// Server functions are only ever called by this app's own pages, so reject
// any server-function request that isn't same-origin (checked via
// Sec-Fetch-Site, falling back to Origin / Referer). Page loads and assets
// aren't affected.
const csrf = createCsrfMiddleware({
  filter: (ctx) => ctx.handlerType === "serverFn",
});

export const startInstance = createStart(() => ({
  requestMiddleware: [csrf, hostRouting],
}));
