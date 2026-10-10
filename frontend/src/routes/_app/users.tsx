import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import UsersListPage from "@/pages/users/list";

export const Route = createFileRoute("/_app/users")({
  // ?tab=invites opens the Invites tab.
  validateSearch: (search: Record<string, unknown>): { tab?: "invites" } => ({
    tab: search.tab === "invites" ? "invites" : undefined,
  }),
  component: () => (
    <RequireSuperAdmin>
      <UsersListPage />
    </RequireSuperAdmin>
  ),
});
