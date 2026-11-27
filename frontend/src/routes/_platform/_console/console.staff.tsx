import { createFileRoute } from "@tanstack/react-router";
import ConsoleStaffSearchPage from "@/pages/platform/staff-search";

export const Route = createFileRoute("/_platform/_console/console/staff")({
  head: () => ({ meta: [{ title: "Find staff | Ordo console" }] }),
  component: ConsoleStaffSearchPage,
});
