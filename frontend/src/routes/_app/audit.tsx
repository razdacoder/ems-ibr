import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import AuditLogListPage from "@/pages/audit/list";

export const Route = createFileRoute("/_app/audit")({
  component: () => (
    <RequireSuperAdmin>
      <AuditLogListPage />
    </RequireSuperAdmin>
  ),
});
