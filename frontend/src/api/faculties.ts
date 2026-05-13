import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PaginatedResponse } from "./departments";

export interface FacultyDepartmentBrief {
  id: number;
  name: string;
  slug: string;
}

export interface Faculty {
  id: number;
  name: string;
  slug: string;
  department_count: number;
  departments: FacultyDepartmentBrief[];
}

export interface FacultyListParams {
  page?: number;
  query?: string;
  enabled?: boolean;
}

const KEY = ["faculties"] as const;

export function useFaculties(params: FacultyListParams = {}) {
  const { enabled = true, ...query } = params;
  return useQuery({
    queryKey: [...KEY, query],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Faculty>>("/faculties/", {
        params: query,
      });
      return res.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
}

export interface FacultyInput {
  name: string;
  slug: string;
  department_ids?: number[];
}

export function useCreateFaculty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: FacultyInput) => {
      const res = await api.post<Faculty>("/faculties/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["departments"] });
    },
  });
}

export function useUpdateFaculty(originalSlug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: FacultyInput) => {
      const res = await api.patch<Faculty>(
        `/faculties/${originalSlug}/`,
        data,
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["departments"] });
    },
  });
}

export function useDeleteFaculty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (slug: string) => {
      await api.delete(`/faculties/${slug}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: ["departments"] });
    },
  });
}
