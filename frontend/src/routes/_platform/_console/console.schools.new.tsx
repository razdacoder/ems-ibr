import { createFileRoute } from "@tanstack/react-router";
import { RequirePlatformOwner } from "@/components/route-guards";
import ConsoleNewSchoolPage from "@/pages/platform/school-new";

export const Route = createFileRoute("/_platform/_console/console/schools/new")({
  head: () => ({ meta: [{ title: "New school | Ordo console" }] }),
  component: () => (
    <RequirePlatformOwner>
      <ConsoleNewSchoolPage />
    </RequirePlatformOwner>
  ),
});
