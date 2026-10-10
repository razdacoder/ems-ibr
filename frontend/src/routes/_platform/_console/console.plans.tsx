import { createFileRoute } from "@tanstack/react-router";
import ConsolePlansPage from "@/pages/platform/plans";

export const Route = createFileRoute("/_platform/_console/console/plans")({
  head: () => ({ meta: [{ title: "Plans | Ordo console" }] }),
  component: ConsolePlansPage,
});
