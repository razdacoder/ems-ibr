import { createFileRoute } from "@tanstack/react-router";
import ConsoleHealthPage from "@/pages/platform/health";

export const Route = createFileRoute("/_platform/_console/console/health")({
  head: () => ({ meta: [{ title: "Health | Ordo console" }] }),
  component: ConsoleHealthPage,
});
