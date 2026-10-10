import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import ConstraintsPage from "@/pages/constraints/page";

export const Route = createFileRoute("/_app/constraints")({
  component: () => (
    <RequireSuperAdmin>
      <ConstraintsPage />
    </RequireSuperAdmin>
  ),
});
