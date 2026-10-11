import { createFileRoute } from "@tanstack/react-router";
import ConsoleSchoolsPage from "@/pages/platform/schools";

export const Route = createFileRoute("/_platform/_console/console/schools/")({
  head: () => ({ meta: [{ title: "Schools | Ordo console" }] }),
  component: ConsoleSchoolsPage,
});
