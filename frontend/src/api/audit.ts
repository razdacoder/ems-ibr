import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PaginatedResponse } from "./types";

export interface AuditLogRow {
  id: number;
  user: number | null;
  user_email: string;
  user_name: string;
  action: string;
  method: string;
  path: string;
  object_type: string;
  object_id: string;
  status_code: number | null;
  succeeded: boolean;
  ip_address: string | null;
  user_agent: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogParams {
  page?: number;
  query?: string;
  status?: "success" | "failed";
  object_type?: string;
  date_from?: string;
  date_to?: string;
}

const KEY = ["audit-logs"] as const;

export function useAuditLogs(params: AuditLogParams = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<AuditLogRow>>(
        "/audit-logs/",
        { params },
      );
      return res.data;
    },
    placeholderData: keepPreviousData,
  });
}
