import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SystemSettings {
  id: number;
  session: string;
  semester: string;
  has_timetable: boolean;
}

export interface DashboardStats {
  departments_count: number;
  halls_count: number;
  courses_count: number;
  classes_count: number;
  students_count: number;
  shared_courses_count: number;
  shared_courses: Array<{
    code: string;
    name: string;
    dept_count: number;
    departments: Array<{ name: string; classes: Array<string | null> }>;
  }>;
  settings: SystemSettings;
}

const SETTINGS_KEY = ["system", "settings"] as const;
const DASHBOARD_KEY = ["system", "dashboard"] as const;

export function useSystemSettings() {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: async () => {
      const res = await api.get<SystemSettings>("/system/settings/");
      return res.data;
    },
  });
}

export function useUpdateSystemSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<SystemSettings>) => {
      const res = await api.patch<SystemSettings>("/system/settings/", data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SETTINGS_KEY });
      qc.invalidateQueries({ queryKey: DASHBOARD_KEY });
    },
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: DASHBOARD_KEY,
    queryFn: async () => {
      const res = await api.get<DashboardStats>("/system/dashboard/");
      return res.data;
    },
  });
}

export type ResetScope = "all" | "timetable" | "distribution" | "allocation";

export function useResetSystem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (scope: ResetScope = "all") => {
      await api.post("/system/reset/", { scope });
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useEnableBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/system/enable-bulk-upload/");
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}
