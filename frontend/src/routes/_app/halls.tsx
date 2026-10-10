import { createFileRoute } from "@tanstack/react-router";
import { RequireDataOfficer } from "@/components/route-guards";
import HallsListPage from "@/pages/halls/list";

export const Route = createFileRoute("/_app/halls")({
  component: () => (
    <RequireDataOfficer>
      <HallsListPage />
    </RequireDataOfficer>
  ),
});
