import { createFileRoute } from "@tanstack/react-router";
import { RequireHost } from "@/components/route-guards";
import InvitePage from "@/pages/invite";

// The emailed invite to join a school: <slug>.<base>/invite/<token>.
export const Route = createFileRoute("/invite/$token")({
  ssr: false,
  head: () => ({ meta: [{ title: "Join | Ordo" }] }),
  component: InviteRoute,
});

function InviteRoute() {
  const { token } = Route.useParams();
  return (
    <RequireHost kind="school">
      <InvitePage token={token} />
    </RequireHost>
  );
}
