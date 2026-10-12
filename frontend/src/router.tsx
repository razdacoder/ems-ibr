import { createRouter } from "@tanstack/react-router";
import { RedirectHome } from "@/components/route-guards";
import { RouteError } from "@/components/route-error";
import { routeTree } from "./routeTree.gen";

export function getRouter() {
  return createRouter({
    routeTree,
    scrollRestoration: true,
    // Unknown dashboard paths land on the home page (or login, via the guard).
    defaultNotFoundComponent: RedirectHome,
    // Any route that throws: report it and offer a retry (spec 0004).
    defaultErrorComponent: RouteError,
  });
}
