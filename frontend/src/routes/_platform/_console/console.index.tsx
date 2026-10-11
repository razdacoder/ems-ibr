import { createFileRoute } from "@tanstack/react-router";
import ConsoleDashboardPage from "@/pages/platform/dashboard";

export const Route = createFileRoute("/_platform/_console/console/")({
  head: () => ({ meta: [{ title: "Dashboard | Ordo console" }] }),
  component: ConsoleDashboardPage,
});
