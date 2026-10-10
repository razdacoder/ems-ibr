import { createFileRoute } from "@tanstack/react-router";
import { RequireCommittee } from "@/components/route-guards";
import DirectoryPage from "@/pages/directory/page";

export const Route = createFileRoute("/_app/directory")({
  component: () => (
    <RequireCommittee>
      <DirectoryPage />
    </RequireCommittee>
  ),
});
