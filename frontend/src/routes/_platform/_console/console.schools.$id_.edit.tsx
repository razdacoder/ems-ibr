import { createFileRoute } from "@tanstack/react-router";
import { RequirePlatformOwner } from "@/components/route-guards";
import ConsoleEditSchoolPage from "@/pages/platform/school-edit";
import NotFoundPage from "@/pages/not-found";

export const Route = createFileRoute("/_platform/_console/console/schools/$id_/edit")({
  head: () => ({ meta: [{ title: "Edit school | Ordo console" }] }),
  component: EditSchoolRoute,
});

function EditSchoolRoute() {
  const { id } = Route.useParams();
  const pk = Number(id);
  if (!Number.isInteger(pk) || pk <= 0) return <NotFoundPage />;
  return (
    <RequirePlatformOwner>
      <ConsoleEditSchoolPage key={pk} id={pk} />
    </RequirePlatformOwner>
  );
}
