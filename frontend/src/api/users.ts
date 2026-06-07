import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuthUser, UserRole } from "@/lib/auth";
import type { PaginatedResponse } from "./types";

export type UserRow = AuthUser & { created_at: string };

export interface UserInput {
  email: string;
  first_name: string;
  last_name: string;
  department_id: number | null;
  // null = department officer (scoped to `department_id`); a role = admin-side user.
  role: UserRole | null;
  password?: string;
}

const KEY = ["users"] as const;

export function useUsers(params: { page?: number; query?: string } = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<UserRow>>("/users/", {
        params,
      });
      return res.data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: UserInput) => {
      const res = await api.post<UserRow>("/users/", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateUser(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<UserInput>) => {
      const res = await api.patch<UserRow>(`/users/${id}/`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/users/${id}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export interface SeedDepartmentsInput {
  password?: string;
  overwrite?: boolean;
}

export interface SeedDepartmentsResult {
  detail: string;
  created: string[];
  updated: string[];
  skipped: string[];
  departments_total: number;
  password: string;
}

export function useSeedDepartmentUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: SeedDepartmentsInput) => {
      const res = await api.post<SeedDepartmentsResult>(
        "/users/seed-departments/",
        data,
      );
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useChangeUserPassword(id: number) {
  return useMutation({
    mutationFn: async (password: string) => {
      const res = await api.post<{ detail: string }>(
        `/users/${id}/change-password/`,
        { password },
      );
      return res.data;
    },
  });
}
