import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import JobsListPage from "@/pages/jobs/list";

export const Route = createFileRoute("/_app/jobs")({
  component: () => (
    <RequireSuperAdmin>
      <JobsListPage />
    </RequireSuperAdmin>
  ),
});
