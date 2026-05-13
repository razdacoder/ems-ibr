import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type ClassPeriodOverrides = Record<string, "AM" | "PM">;

export interface GenerationConstraints {
  id: number;
  cbe_autosplit_threshold: number;
  cbe_fullday_threshold: number;
  cbe_daily_cap_per_period: number;
  pbe_hall_utilization: string; // DRF DecimalField serializes as string
  excluded_weekdays: number[];
  class_period_overrides: ClassPeriodOverrides;
  remainder_merge_threshold: number;
  placement_success_threshold_pct: number;
  configured_at: string | null;
  configured_by: number | null;
  configured_by_email: string | null;
  configured: boolean;
  updated_at: string;
}

export type GenerationConstraintsInput = Partial<
  Omit<
    GenerationConstraints,
    | "id"
    | "configured_at"
    | "configured_by"
    | "configured_by_email"
    | "configured"
    | "updated_at"
  >
>;

const KEY = ["constraints"] as const;

export function useConstraints() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const res = await api.get<GenerationConstraints>("/system/constraints/");
      return res.data;
    },
  });
}

export function useUpdateConstraints() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: GenerationConstraintsInput) => {
      const res = await api.patch<GenerationConstraints>(
        "/system/constraints/",
        data,
      );
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

