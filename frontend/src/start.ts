import {
  createCsrfMiddleware,
  createMiddleware,
  createStart,
} from "@tanstack/react-start";

/**
 * The marketing site used to live on this domain. Its old URLs (indexed,
 * bookmarked) go to the same path on SITE_URL so they keep working. Only
 * page loads are steered — server-function calls and assets pass through.
 */
const oldSiteUrls = createMiddleware().server(({ request, next }) => {
  const site = process.env.SITE_URL?.replace(/\/+$/, "");
  const isPage =
    request.method === "GET" &&
    (request.headers.get("accept") ?? "").includes("text/html");
  if (!site || !isPage) return next();

  const { pathname, search } = new URL(request.url);
  if (pathname === "/features" || pathname.startsWith("/features/")) {
    return Response.redirect(site + pathname + search, 301);
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
  requestMiddleware: [csrf, oldSiteUrls],
}));
