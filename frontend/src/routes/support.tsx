import { createFileRoute } from "@tanstack/react-router";
import { RequireHost } from "@/components/route-guards";
import { str } from "@/lib/search";
import SupportPage from "@/pages/support";

// The console's one time support link: <slug>.<base>/support?ticket=<ticket>.
// No open school guard: support may enter a suspended school.
export const Route = createFileRoute("/support")({
  ssr: false,
  head: () => ({ meta: [{ title: "Ordo support" }] }),
  validateSearch: (search: Record<string, unknown>): { ticket?: string } => ({
    ticket: str(search.ticket),
  }),
  component: SupportRoute,
});

function SupportRoute() {
  const { ticket } = Route.useSearch();
  return (
    <RequireHost kind="school">
      <SupportPage ticket={ticket} />
    </RequireHost>
  );
}
