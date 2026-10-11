import { createFileRoute } from "@tanstack/react-router";
import ConsoleAnnouncementsPage from "@/pages/platform/announcements";

export const Route = createFileRoute("/_platform/_console/console/announcements")({
  head: () => ({ meta: [{ title: "Announcements | Ordo console" }] }),
  component: ConsoleAnnouncementsPage,
});
