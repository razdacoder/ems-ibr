import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SystemSettings {
  id: number;
  session: string;
  semester: string;
  has_timetable: boolean;
  institution_name: string;
  institution_short_name: string;
  institution_address: string;
  exam_heading: string;
  contact_email: string;
  contact_phone: string;
  logo_url: string | null;
  brand_color: string;
}

/** Writable system-configuration fields. `logo` is a file picked in the form. */
export interface SystemSettingsUpdate {
  session?: string;
  semester?: string;
  institution_name?: string;
  institution_short_name?: string;
  institution_address?: string;
  exam_heading?: string;
  contact_email?: string;
  contact_phone?: string;
  brand_color?: string;
  logo?: File | null;
}

/** Public institution branding (no auth) — drives logos + theme beside the app mark. */
export interface Branding {
  institution_name: string;
  institution_short_name: string;
  logo_url: string | null;
  brand_color: string;
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
const BRANDING_KEY = ["system", "branding"] as const;

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
    mutationFn: async (data: SystemSettingsUpdate) => {
      // Send multipart so the logo file rides along with the text fields.
      const form = new FormData();
      for (const [key, value] of Object.entries(data)) {
        if (value === undefined) continue;
        if (key === "logo") {
          if (value instanceof File) form.append("logo", value);
        } else {
          form.append(key, value as string);
        }
      }
      const res = await api.patch<SystemSettings>("/system/settings/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SETTINGS_KEY });
      qc.invalidateQueries({ queryKey: DASHBOARD_KEY });
      qc.invalidateQueries({ queryKey: BRANDING_KEY });
    },
  });
}

export function useBranding() {
  return useQuery({
    queryKey: BRANDING_KEY,
    queryFn: async () => {
      const res = await api.get<Branding>("/system/branding/");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
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
