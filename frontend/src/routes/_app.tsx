import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { RequireAuth } from "@/components/route-guards";

// Dashboard (app host). Pathless layout for every signed-in page: auth gate + sidebar shell.
// Role-gated pages add their own guard in their route file.
export const Route = createFileRoute("/_app")({
  // Needs the session token from localStorage — render in the browser only.
  ssr: false,
  head: () => ({ meta: [{ title: "Ordo" }] }),
  component: () => (
    <RequireAuth>
      <DashboardLayout />
    </RequireAuth>
  ),
});
