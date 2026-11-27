import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuthUser, UserRole } from "@/lib/auth";
import type { PaginatedResponse } from "./types";

export interface InviteRow {
  id: number;
  email: string;
  /** Null is a department officer. */
  role: UserRole | null;
  department: { id: number; name: string; slug: string } | null;
  /** Null when Ordo sent it (the school's first admin). */
  invited_by: { id: number; name: string; email: string } | null;
  expires_at: string;
  is_expired: boolean;
  created_at: string;
}

export interface InviteInput {
  email: string;
  role: UserRole | null;
  department_id: number | null;
}

/** What the emailed link shows before anyone signs in. */
export interface InviteDetails {
  school_name: string;
  email: string;
  role: UserRole | null;
  department: { id: number; name: string; slug: string } | null;
}

const KEY = ["invites"] as const;

export function useInvites(params: { page?: number } = {}) {
  return useQuery({
    queryKey: [...KEY, params],
    queryFn: async () =>
      (await api.get<PaginatedResponse<InviteRow>>("/invites/", { params })).data,
    placeholderData: keepPreviousData,
  });
}

function useInviteMutation<TVars, TData>(fn: (vars: TVars) => Promise<TData>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export const useCreateInvite = () =>
  useInviteMutation(
    async (input: InviteInput) => (await api.post<InviteRow>("/invites/", input)).data,
  );

export const useRevokeInvite = () =>
  useInviteMutation((id: number) => api.post(`/invites/${id}/revoke/`));

export const useResendInvite = () =>
  useInviteMutation(
    async (id: number) => (await api.post<InviteRow>(`/invites/${id}/resend/`)).data,
  );

export async function fetchInvite(token: string): Promise<InviteDetails> {
  return (await api.get<InviteDetails>(`/invites/${encodeURIComponent(token)}/`)).data;
}

export interface AcceptInviteInput {
  first_name: string;
  last_name: string;
  password: string;
}

export async function acceptInvite(token: string, input: AcceptInviteInput) {
  return (
    await api.post<{ token: string; user: AuthUser }>(
      `/invites/${encodeURIComponent(token)}/accept/`,
      input,
    )
  ).data;
}
