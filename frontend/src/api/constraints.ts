import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type ClassPeriodOverrides = Record<string, "AM" | "PM">;
export type FacultyGroupMap = Record<string, number>;
export type SeatPattern = "checkerboard" | "sequential";
/** Halls up to ``max_seats`` seats (null = any size) hold at most ``courses``. */
export interface HallCourseTier {
  max_seats: number | null;
  courses: number;
}

export interface GenerationConstraints {
  id: number;
  cbe_autosplit_threshold: number;
  cbe_fullday_threshold: number;
  cbe_daily_cap_per_period: number;
  cbe_group_count: number;
  cbe_faculty_groups: FacultyGroupMap;
  /** Hard cap on how full a hall may get, 0-1. DRF sends decimals as strings. */
  pbe_hall_utilization: string;
  hall_course_limits: HallCourseTier[];
  /** Hall groups in the order they stand, so courses spill to neighbours. */
  hall_group_order: string[];
  seat_pattern: SeatPattern;
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

