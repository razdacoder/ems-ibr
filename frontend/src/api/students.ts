import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  ClassRef,
  DepartmentRef,
  PaginatedResponse,
} from "./types";

export interface Student {
  id: number;
  first_name: string;
  last_name: string;
  matric_no: string;
  email: string;
  phone: string;
  department: DepartmentRef | null;
  level: ClassRef | null;
}

export interface StudentInput {
  first_name: string;
  last_name: string;
  matric_no: string;
  email: string;
  phone: string;
  class_id: number;
}

export interface StudentListParams {
  page?: number;
  query?: string;
  department?: string;
  class?: number;
}

const KEY = ["students"] as const;

export function useStudents(params: StudentListParams = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Student>>("/students/", {
        params,
      });
      return res.data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useCreateStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: StudentInput) => {
      const res = await api.post<Student>("/students/", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateStudent(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<StudentInput>) => {
      const res = await api.patch<Student>(`/students/${id}/`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/students/${id}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
