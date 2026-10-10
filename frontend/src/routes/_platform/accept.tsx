import { createFileRoute } from "@tanstack/react-router";
import { str } from "@/lib/search";
import AcceptAdminInvitePage from "@/pages/platform/accept";

// The emailed platform admin invite: admin.<base>/accept?token=...
export const Route = createFileRoute("/_platform/accept")({
  head: () => ({ meta: [{ title: "Accept invite | Ordo console" }] }),
  validateSearch: (search: Record<string, unknown>): { token?: string } => ({
    token: str(search.token),
  }),
  component: AcceptAdminInvitePage,
});
