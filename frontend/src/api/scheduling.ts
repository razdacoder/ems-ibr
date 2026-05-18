import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type Period = "AM" | "PM";

export interface TimetableEntry {
  id: number;
  date: string;
  period: Period;
  course: { id: number; code: string; name: string };
  class: {
    id: number;
    name: string | null;
    department: { id: number; name: string; slug: string };
  };
}

export function useTimetable(
  params: { date?: string; period?: Period },
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["timetable", params],
    queryFn: async () => {
      const res = await api.get<{
        generated: boolean;
        results: TimetableEntry[];
      }>("/timetable/", { params });
      return res.data;
    },
    enabled: options?.enabled ?? true,
  });
}

export function useTimetableDates() {
  return useQuery({
    queryKey: ["timetable", "dates"],
    queryFn: async () => {
      const res = await api.get<{ dates: string[] }>("/timetable/dates/");
      return res.data;
    },
  });
}

export interface TimetableEstimate {
  min_exam_days: number;
  recommended_exam_days: number;
  min_calendar_days: number;
  min_calendar_weeks: number;
  excluded_weekdays: number[];
  valid_exam_days_per_week: number;
  class_count: number;
  worst_class_am: number;
  worst_class_pm: number;
  per_class_min_days: number;
  throughput_min_days: number;
  am_seat_demand: number;
  pm_seat_demand: number;
  seats_per_period: number;
  bottleneck: "per_class" | "seat_throughput";
}

export function useTimetableEstimate(enabled: boolean = true) {
  return useQuery({
    queryKey: ["timetable", "estimate"],
    queryFn: async () => {
      const res = await api.get<TimetableEstimate>("/timetable/estimate/");
      return res.data;
    },
    enabled,
  });
}

export interface DistributionRow {
  id: number;
  date: string | null;
  period: string | null;
  hall: { id: number; name: string; capacity: number };
  items: Array<{
    id: number;
    no_of_students: number;
    schedule: {
      id: number;
      course_code: string;
      course_name: string;
      class_name: string | null;
      department_slug: string;
    };
  }>;
}

export function useDistribution(params: { date?: string; period?: Period }) {
  return useQuery({
    queryKey: ["distribution", params],
    queryFn: async () => {
      const res = await api.get<{
        generated: boolean;
        results: DistributionRow[];
      }>("/distribution/", { params });
      return res.data;
    },
  });
}

export function useDistributionStatistics(date?: string, period?: Period) {
  return useQuery({
    queryKey: ["distribution", "stats", date, period],
    queryFn: async () => {
      const res = await api.get<{
        date: string;
        period: string;
        halls_used: number;
        students_seated: number;
      }>("/distribution/statistics/", { params: { date, period } });
      return res.data;
    },
    enabled: !!(date && period),
  });
}

export interface AllocationRow {
  hall_id: number;
  hall__name: string;
  date: string;
  period: string;
  placed: number;
  not_placed: number;
}

export function useAllocation(params: { date?: string; period?: Period }) {
  return useQuery({
    queryKey: ["allocation", params],
    queryFn: async () => {
      const res = await api.get<{
        generated: boolean;
        results: AllocationRow[];
      }>("/allocation/", { params });
      return res.data;
    },
  });
}

export interface HallAllocationData {
  hall: {
    id: number;
    name: string;
    rows: number;
    columns: number;
    capacity: number;
  };
  date: string;
  period: string;
  placed: Array<{
    id: number;
    seat_number: number;
    course: { id: number; code: string };
    class: { id: number; name: string | null };
    student: {
      id: number;
      matric_no: string;
      first_name: string;
      last_name: string;
    } | null;
  }>;
  unplaced: Array<{
    id: number;
    seat_number: number | null;
    course: { id: number; code: string };
    class: { id: number; name: string | null };
    student: {
      id: number;
      matric_no: string;
      first_name: string;
      last_name: string;
    } | null;
  }>;
}

export function useHallAllocation(params: {
  date?: string;
  period?: Period;
  hall_id?: number;
}) {
  return useQuery({
    queryKey: ["allocation", "hall", params],
    queryFn: async () => {
      const res = await api.get<HallAllocationData>("/allocation/hall/", {
        params,
      });
      return res.data;
    },
    enabled: !!(params.date && params.period && params.hall_id),
  });
}
