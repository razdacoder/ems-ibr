import { createFileRoute } from "@tanstack/react-router";
import { getFeature } from "@/lib/site-api";
import FeatureDetailPage, { FeatureNotFound } from "@/pages/public/feature-detail";

export const Route = createFileRoute("/site/features/$slug")({
  loader: ({ params }) => getFeature({ data: params.slug }),
  staleTime: 5 * 60 * 1000,
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.title} | Ordo` },
          { name: "description", content: loaderData.subtitle },
        ]
      : [],
  }),
  component: function Feature() {
    return <FeatureDetailPage feature={Route.useLoaderData()} />;
  },
  notFoundComponent: () => <FeatureNotFound slug={Route.useParams().slug} />,
});
