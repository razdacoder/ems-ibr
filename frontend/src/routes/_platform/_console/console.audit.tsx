import { createFileRoute } from "@tanstack/react-router";
import ConsoleAuditPage, { type AuditFilters } from "@/pages/platform/audit";

const asId = (value: unknown) => {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : undefined;
};

export const Route = createFileRoute("/_platform/_console/console/audit")({
  head: () => ({ meta: [{ title: "Audit log | Ordo console" }] }),
  // Filters live in the URL so a school's "View all" link can open them.
  validateSearch: (search: Record<string, unknown>): AuditFilters => ({
    action: typeof search.action === "string" && search.action ? search.action : undefined,
    admin: asId(search.admin),
    school: asId(search.school),
  }),
  component: AuditRoute,
});

function AuditRoute() {
  const filters = Route.useSearch();
  const navigate = Route.useNavigate();
  return <ConsoleAuditPage filters={filters} onFiltersChange={(next) => navigate({ search: next })} />;
}
