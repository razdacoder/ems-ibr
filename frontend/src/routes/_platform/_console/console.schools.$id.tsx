import { createFileRoute } from "@tanstack/react-router";
import ConsoleSchoolDetailPage from "@/pages/platform/school-detail";
import NotFoundPage from "@/pages/not-found";

export const Route = createFileRoute("/_platform/_console/console/schools/$id")({
  head: () => ({ meta: [{ title: "School | Ordo console" }] }),
  component: SchoolRoute,
});

function SchoolRoute() {
  const { id } = Route.useParams();
  const pk = Number(id);
  if (!Number.isInteger(pk) || pk <= 0) return <NotFoundPage />;
  return <ConsoleSchoolDetailPage key={pk} id={pk} />;
}
