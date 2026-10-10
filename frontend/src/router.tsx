import { createRouter } from "@tanstack/react-router";
import { RedirectHome } from "@/components/route-guards";
import { routeTree } from "./routeTree.gen";

/*
 * One route tree, two hosts. The dashboard's routes sit at the root (its
 * home is "/"); the marketing site's live under /site. On any host other
 * than app.*, incoming URLs gain the /site prefix and outgoing links lose
 * it, so ordo.app/features is /site/features to the router. start.ts keeps
 * each host to its own pages. Keep "app." in sync with origins.server.ts.
 */
const SITE = "/site";

const isSiteHost = (url: URL) => !url.hostname.startsWith("app.");

export function getRouter() {
  return createRouter({
    routeTree,
    scrollRestoration: true,
    // Unknown dashboard paths land on the home page (or login, via the guard).
    defaultNotFoundComponent: RedirectHome,
    rewrite: {
      input: ({ url }) => {
        if (isSiteHost(url)) url.pathname = SITE + url.pathname;
        return url;
      },
      output: ({ url }) => {
        if (url.pathname === SITE || url.pathname.startsWith(`${SITE}/`)) {
          url.pathname = url.pathname.slice(SITE.length) || "/";
        }
        return url;
      },
    },
  });
}
