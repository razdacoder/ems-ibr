import { createFileRoute } from "@tanstack/react-router";
import { getFeatures } from "@/lib/site-api";
import FeaturesPage from "@/pages/public/features";

export const Route = createFileRoute("/site/features/")({
  loader: () => getFeatures(),
  staleTime: 5 * 60 * 1000,
  head: () => ({ meta: [{ title: "Modules | Ordo" }] }),
  component: function Features() {
    return <FeaturesPage features={Route.useLoaderData()} />;
  },
});
