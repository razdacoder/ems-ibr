import { createFileRoute } from "@tanstack/react-router";
import { RequireSuperAdmin } from "@/components/route-guards";
import SettingsPage from "@/pages/settings/page";

export const Route = createFileRoute("/_app/settings")({
  component: () => (
    <RequireSuperAdmin>
      <SettingsPage />
    </RequireSuperAdmin>
  ),
});
