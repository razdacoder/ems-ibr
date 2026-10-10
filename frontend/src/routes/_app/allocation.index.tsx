import { createFileRoute } from "@tanstack/react-router";
import { RequireCommittee } from "@/components/route-guards";
import { str } from "@/lib/search";
import AllocationPage from "@/pages/allocation/page";

export const Route = createFileRoute("/_app/allocation/")({
  validateSearch: (search: Record<string, unknown>): { date?: string; period?: string } => ({
    date: str(search.date),
    period: str(search.period),
  }),
  component: () => (
    <RequireCommittee>
      <AllocationPage />
    </RequireCommittee>
  ),
});
