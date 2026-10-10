import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import UsersListPage from "@/pages/users/list";

export const Route = createFileRoute("/_app/users")({
  component: () => (
    <RequireSuperAdmin>
      <UsersListPage />
    </RequireSuperAdmin>
  ),
});
