import { createFileRoute } from "@tanstack/react-router";
import ConsoleHomePage from "@/pages/platform/home";

export const Route = createFileRoute("/_platform/_console/console/")({
  component: ConsoleHomePage,
});
