import { createFileRoute } from "@tanstack/react-router";
import ConsoleAuditPage from "@/pages/platform/audit";

export const Route = createFileRoute("/_platform/_console/console/audit")({
  head: () => ({ meta: [{ title: "Audit log | Ordo console" }] }),
  component: ConsoleAuditPage,
});
