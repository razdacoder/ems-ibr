import { createFileRoute } from "@tanstack/react-router";
import { RequirePlatformOwner } from "@/components/route-guards";
import ConsoleAdminsPage from "@/pages/platform/admins";

export const Route = createFileRoute("/_platform/_console/console/admins")({
  head: () => ({ meta: [{ title: "Admins | Ordo console" }] }),
  component: () => (
    <RequirePlatformOwner>
      <ConsoleAdminsPage />
    </RequirePlatformOwner>
  ),
});
