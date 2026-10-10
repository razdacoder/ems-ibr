import { createFileRoute } from "@tanstack/react-router";
import { RequireCommittee } from "@/components/route-guards";
import DistributionPage from "@/pages/distribution/page";

export const Route = createFileRoute("/_app/distribution")({
  component: () => (
    <RequireCommittee>
      <DistributionPage />
    </RequireCommittee>
  ),
});
