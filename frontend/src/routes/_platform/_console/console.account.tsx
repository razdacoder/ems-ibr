import { createFileRoute } from "@tanstack/react-router";
import ConsoleAccountPage from "@/pages/platform/account";

export const Route = createFileRoute("/_platform/_console/console/account")({
  head: () => ({ meta: [{ title: "Your account | Ordo console" }] }),
  component: ConsoleAccountPage,
});
