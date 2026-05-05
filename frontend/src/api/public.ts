import axios from "axios";
import { useQuery } from "@tanstack/react-query";

// Public endpoints accept anonymous access — use a vanilla axios instance
// so the auth interceptor doesn't redirect to /login on 401.
const publicApi = axios.create({ baseURL: "/api" });

export interface FeatureSummary {
  slug: string;
  title: string;
  subtitle: string;
  icon: string | null;
}

export interface Feature extends FeatureSummary {
  overview: string;
  capabilities: string[];
  how_it_works: string[];
  benefits: string[];
}

export function useFeatures() {
  return useQuery({
    queryKey: ["public", "features"],
    queryFn: async () => {
      const res = await publicApi.get<{ results: FeatureSummary[] }>(
        "/public/features/",
      );
      return res.data.results;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useFeature(slug: string | undefined) {
  return useQuery({
    queryKey: ["public", "features", slug],
    queryFn: async () => {
      const res = await publicApi.get<Feature>(`/public/features/${slug}/`);
      return res.data;
    },
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  });
}
