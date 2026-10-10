import { createFileRoute } from "@tanstack/react-router";
import { RequireFacultyOfficer } from "@/components/route-guards";
import FacultiesListPage from "@/pages/faculties/list";

export const Route = createFileRoute("/_app/faculties")({
  component: () => (
    <RequireFacultyOfficer>
      <FacultiesListPage />
    </RequireFacultyOfficer>
  ),
});
