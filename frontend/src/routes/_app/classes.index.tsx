import { createFileRoute } from "@tanstack/react-router";
import ClassesListPage from "@/pages/classes/list";

export const Route = createFileRoute("/_app/classes/")({
  component: ClassesListPage,
});
