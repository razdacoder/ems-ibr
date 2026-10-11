import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { RequireAuth, RequireHost, RequireOpenSchool } from "@/components/route-guards";

// School dashboard (<slug>.<base> only). Pathless layout for every signed-in page: auth gate + sidebar shell.
// Role-gated pages add their own guard in their route file.
export const Route = createFileRoute("/_app")({
  // Needs the session token from localStorage — render in the browser only.
  ssr: false,
  head: () => ({ meta: [{ title: "Ordo" }] }),
  component: () => (
    <RequireHost kind="school">
      <RequireOpenSchool>
        <RequireAuth>
          <DashboardLayout />
        </RequireAuth>
      </RequireOpenSchool>
    </RequireHost>
  ),
});
