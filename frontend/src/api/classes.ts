import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Course } from "./courses";
import type { DepartmentRef, PaginatedResponse } from "./types";

export type ExamPeriod = "" | "AM" | "PM";

export interface Class {
  id: number;
  name: string | null;
  size: number;
  department: DepartmentRef;
  courses: Course[];
  student_count: number;
}

export interface ClassListParams {
  page?: number;
  query?: string;
  department?: string;
}

export interface ClassInput {
  name: string;
  size: number;
  department_id: number;
}

const KEY = ["classes"] as const;

export function useClasses(params: ClassListParams = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Class>>("/classes/", {
        params,
      });
      return res.data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useClass(id: number | undefined) {
  return useQuery({
    queryKey: [...KEY, "detail", id],
    queryFn: async () => {
      const res = await api.get<Class>(`/classes/${id}/`);
      return res.data;
    },
    enabled: id !== undefined,
  });
}

export function useCreateClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ClassInput) => {
      const res = await api.post<Class>("/classes/", data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateClass(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<ClassInput>) => {
      const res = await api.patch<Class>(`/classes/${id}/`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/classes/${id}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export interface ClassCourseAssignInput {
  course_id?: number;
  name?: string;
  code?: string;
  exam_type?: "PBE" | "CBE";
}

export function useAddCourseToClass(classId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: ClassCourseAssignInput) => {
      const res = await api.post<Course>(`/classes/${classId}/courses/`, data);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useRemoveCourseFromClass(classId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (courseId: number) => {
      await api.delete(`/classes/${classId}/courses/${courseId}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
