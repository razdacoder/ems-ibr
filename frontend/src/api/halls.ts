import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Align, SeatOrder } from "@/lib/hall-layout";
import { toPaginated, type PaginatedResponse } from "./types";

export interface Hall {
  id: number;
  name: string;
  /** Halls that stand together (AUD, BE ...); filled from the name. */
  group: string;
  capacity: number;
  rows: number;
  columns: number;
  /** Seat mask, "X" seat / "." no seat per row; null = full rectangle. */
  layout: string[] | null;
  /** How seats are numbered. */
  seat_order: SeatOrder;
  /** Seats in each row, front row first. */
  row_seats: number[];
  seat_count: number;
}

export interface HallInput {
  name: string;
  /** Blank = filled from the name ("BE 3" → BE). */
  group?: string;
  capacity: number;
  rows: number;
  columns: number;
  layout?: string[] | null;
  seat_order?: SeatOrder;
  /** Shorthand for layout: the server builds the mask from these. */
  row_seats?: number[];
  align?: Align;
}

const KEY = ["halls"] as const;

export interface HallListParams {
  page?: number;
  query?: string;
  /** Fetch every hall in one response, bypassing pagination. For pickers. */
  all?: boolean;
}

export function useHalls(params: HallListParams = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<Hall> | Hall[]>("/halls/", {
        params,
      });
      return toPaginated(res.data);
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
