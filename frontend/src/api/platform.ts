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

export type FeatureKey = "seat_allocation" | "exports" | "publication" | "branding";

export const FEATURE_LABELS: Record<FeatureKey, string> = {
  seat_allocation: "Seat allocation",
  exports: "Exports",
  publication: "Timetable publication",
  branding: "Branding",
};

export interface PlanRow {
  id: number;
  code: string;
  name: string;
  max_students: number | null;
  max_staff_users: number | null;
  features: FeatureKey[];
  is_active: boolean;
}

export function usePlans() {
  return useQuery({
    queryKey: ["platform", "plans"],
    queryFn: async () => (await platformApi.get<PlanRow[]>("/plans/")).data,
  });
}

export type SchoolStatus =
  | "provisioning"
  | "active"
  | "failed"
  | "suspended"
  | "pending_deletion"
  | "purged";

export const SCHOOL_STATUS_LABELS: Record<SchoolStatus, string> = {
  provisioning: "Setting up",
  active: "Active",
  failed: "Setup failed",
  suspended: "Suspended",
  pending_deletion: "Pending deletion",
  purged: "Purged",
};

export interface SchoolRow {
  id: number;
  name: string;
  slug: string;
  status: SchoolStatus;
  plan: { id: number; code: string; name: string };
  domain: string | null;
  first_admin_name: string;
  first_admin_email: string;
  country: string;
  provisioning_error: string;
  created_at: string;
}

export interface SchoolDetail extends SchoolRow {
  domains: { domain: string; is_primary: boolean }[];
  max_students_override: number | null;
  max_staff_users_override: number | null;
  features_override: FeatureKey[] | null;
  contact_name: string;
  contact_email: string;
  timezone: string;
  notes: string;
  plan_started_on: string | null;
  renews_on: string | null;
  provisioning_started_at: string | null;
  was_ever_active: boolean;
  created_by: { id: number; name: string; email: string } | null;
  /** Null while the school has no live schema yet. */
  first_admin: { joined: boolean; invite_expires_at: string | null } | null;
}

export interface CreateSchoolInput {
  name: string;
  slug: string;
  plan: string;
  max_students_override?: number | null;
  max_staff_users_override?: number | null;
  features_override?: FeatureKey[] | null;
  first_admin_name: string;
  first_admin_email: string;
  contact_name?: string;
  contact_email?: string;
  country?: string;
  timezone?: string;
  notes?: string;
  plan_started_on?: string | null;
  renews_on?: string | null;
}

export interface SchoolListParams {
  page?: number;
  status?: SchoolStatus;
  q?: string;
}

const SCHOOLS = ["platform", "schools"] as const;

/** Poll while a school is being set up, so its status flips on its own. */
const settling = (statuses: SchoolStatus[]) =>
  statuses.includes("provisioning") ? 3000 : false;

export function useSchools(params: SchoolListParams = {}) {
  return useQuery({
    queryKey: [...SCHOOLS, "list", params],
    queryFn: async () =>
      (
        await platformApi.get<PaginatedResponse<SchoolRow>>("/schools/", {
          params,
        })
      ).data,
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      settling(query.state.data?.results.map((s) => s.status) ?? []),
  });
}

export function useSchool(id: number) {
  return useQuery({
    queryKey: [...SCHOOLS, "detail", id],
    queryFn: async () =>
      (await platformApi.get<SchoolDetail>(`/schools/${id}/`)).data,
    refetchInterval: (query) =>
      settling(query.state.data ? [query.state.data.status] : []),
  });
}

/** Invalidate schools and the audit log after any school change. */
function useSchoolMutation<TVars, TData>(fn: (vars: TVars) => Promise<TData>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SCHOOLS });
      void qc.invalidateQueries({ queryKey: AUDIT });
    },
  });
}

export const useCreateSchool = () =>
  useSchoolMutation(
    async (input: CreateSchoolInput) =>
      (await platformApi.post<SchoolDetail>("/schools/", input)).data,
  );

export const useRetrySchool = () =>
  useSchoolMutation((id: number) => platformApi.post(`/schools/${id}/retry/`));

export const useResendSchoolInvite = () =>
  useSchoolMutation((id: number) =>
    platformApi.post(`/schools/${id}/resend-invite/`),
  );
