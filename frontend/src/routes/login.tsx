import { createFileRoute } from "@tanstack/react-router";
import { RequireHost, RequireOpenSchool } from "@/components/route-guards";
import { str } from "@/lib/search";
import LoginPage from "@/pages/login";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({ meta: [{ title: "Sign in | Ordo" }] }),
  // Where to go after signing in; set by the auth guards.
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
    redirect: str(search.redirect),
  }),
  // A school's sign in; the console gets its own.
  component: () => (
    <RequireHost kind="school">
      <RequireOpenSchool>
        <LoginPage />
      </RequireOpenSchool>
    </RequireHost>
  ),
});
