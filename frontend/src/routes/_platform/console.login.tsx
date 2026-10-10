import { createFileRoute } from "@tanstack/react-router";
import { str } from "@/lib/search";
import PlatformLoginPage from "@/pages/platform/login";

export const Route = createFileRoute("/_platform/console/login")({
  head: () => ({ meta: [{ title: "Sign in | Ordo console" }] }),
  // Where to go after signing in; set by the console guard.
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
    redirect: str(search.redirect),
  }),
  component: PlatformLoginPage,
});
