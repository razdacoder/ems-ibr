import { createFileRoute } from "@tanstack/react-router";
import { str } from "@/lib/search";
import LoginPage from "@/pages/login";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({ meta: [{ title: "Sign in | Ordo" }] }),
  // Where to go after signing in; set by the auth guards.
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
    redirect: str(search.redirect),
  }),
  component: LoginPage,
});
