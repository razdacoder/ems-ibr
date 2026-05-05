import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PaginatedResponse } from "./types";

export interface Hall {
  id: number;
  name: string;
  capacity: number;
  max_students: number;
  min_courses: number;
  rows: number;
  columns: number;
}

export interface HallInput {
  name: string;
  capacity: number;
  max_students: number;
  min_courses: number;
  rows: number;
  columns: number;
}

const KEY = ["halls"] as const;

export function useHalls(params: { page?: number; query?: string } = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Hall>>("/halls/", { params });
      return res.data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useCreateHall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: HallInput) => {
      const res = await api.post<Hall>("/halls/", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateHall(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: HallInput) => {
      const res = await api.patch<Hall>(`/halls/${id}/`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteHall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/halls/${id}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
