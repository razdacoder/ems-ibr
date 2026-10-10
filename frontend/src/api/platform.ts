import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { platformApi } from "@/lib/api";
import type { PlatformRole } from "@/lib/platform-auth";
import type { PaginatedResponse } from "./types";

export interface PlatformAdminRow {
  id: number;
  email: string;
  name: string;
  role: PlatformRole;
  is_active: boolean;
  totp_enrolled: boolean;
  invite_pending: boolean;
  last_login: string | null;
  created_at: string;
}

export interface InviteAdminInput {
  email: string;
  name: string;
  role: PlatformRole;
}

export type UpdateAdminInput = Partial<
  Pick<PlatformAdminRow, "name" | "role" | "is_active">
>;

const ADMINS = ["platform", "admins"] as const;
const AUDIT = ["platform", "audit"] as const;

export function usePlatformAdmins() {
  return useQuery({
    queryKey: ADMINS,
    queryFn: async () =>
      (await platformApi.get<PlatformAdminRow[]>("/admins/")).data,
  });
}

/** Invalidate the admins list and the audit log after any admin change. */
function useAdminMutation<TVars>(fn: (vars: TVars) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ADMINS });
      void qc.invalidateQueries({ queryKey: AUDIT });
    },
  });
}

export const useInviteAdmin = () =>
  useAdminMutation((input: InviteAdminInput) =>
    platformApi.post<PlatformAdminRow>("/admins/", input),
  );

export const useUpdateAdmin = () =>
  useAdminMutation(({ id, ...input }: UpdateAdminInput & { id: number }) =>
    platformApi.patch<PlatformAdminRow>(`/admins/${id}/`, input),
  );

export const useResetAdmin2fa = () =>
  useAdminMutation((id: number) => platformApi.post(`/admins/${id}/reset-2fa/`));

export const useUnlockAdmin = () =>
  useAdminMutation((id: number) => platformApi.post(`/admins/${id}/unlock/`));

export const useResendAdminInvite = () =>
  useAdminMutation((id: number) =>
    platformApi.post(`/admins/${id}/resend-invite/`),
  );

/** Set a password from an emailed invite link. No session needed. */
export async function acceptAdminInvite(token: string, password: string) {
  await platformApi.post("/admins/accept/", { token, password });
}

export interface PlatformAuditRow {
  id: number;
  admin: { id: number; name: string; email: string } | null;
  school: { id: number; name: string; slug: string } | null;
  action: string;
  detail: Record<string, unknown>;
  ip: string | null;
  created_at: string;
}

export interface PlatformAuditParams {
  page?: number;
  action?: string;
  admin?: number;
  school?: number;
}

export function usePlatformAudit(params: PlatformAuditParams = {}) {
  return useQuery({
    queryKey: [...AUDIT, params],
    queryFn: async () =>
      (
        await platformApi.get<PaginatedResponse<PlatformAuditRow>>("/audit/", {
          params,
        })
      ).data,
    placeholderData: keepPreviousData,
  });
}
