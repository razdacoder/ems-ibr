import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "@tanstack/react-router";
import {
  canManageData,
  canManageFaculties,
  isCommittee,
  isSuperAdmin,
  useAuth,
  type AuthUser,
} from "@/lib/auth";
import { useQueryClient } from "@tanstack/react-query";
import {
  FEATURE_LABELS,
  type FeatureKey,
  SCHOOL_STATUS_KEY,
  useSchoolPlan,
  useSchoolStatus,
} from "@/api/school";
import { SCHOOL_CLOSED_EVENT, hasLiveSupportToken } from "@/lib/api";
import { useHostKind } from "@/lib/config";
import { isPlatformOwner, usePlatformAuth } from "@/lib/platform-auth";
import type { HostKind } from "@/lib/origins.server";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import NotFoundPage from "@/pages/not-found";
import { SchoolSettingUpPage, SchoolSuspendedPage } from "@/pages/school-closed";

/*
 * Redirects fire once, from an effect. TanStack's <Navigate> re-navigates
 * whenever its props object changes — i.e. on every re-render of the guard,
 * which happens while the navigation is pending — so it never settles.
 */

/** Send a signed-out visitor to /login, remembering where they were going. */
function RedirectToLogin() {
  const navigate = useNavigate();
  const [from] = useState(useLocation().href);
  useEffect(() => {
    navigate({ to: "/login", search: { redirect: from }, replace: true });
  }, [navigate, from]);
  return <FullPageSkeleton />;
}

/** Send the visitor to the dashboard home. */
export function RedirectHome() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate({ to: "/", replace: true });
  }, [navigate]);
  return null;
}

/**
 * Render children only on the right kind of host: school pages on a school,
 * console pages on console.<base>. Anywhere else is the not found page.
 */
export function RequireHost({
  kind,
  children,
}: {
  kind: HostKind;
  children: ReactNode;
}) {
  const host = useHostKind();
  // The path this guard mounted on: while the redirect below is pending, the
  // location already reads /console but this route is still rendered, and
  // checking the live path would flash the not found page.
  const [pathname] = useState(useLocation().pathname);
  if (host === kind) return <>{children}</>;
  // The console lives under /console, so its bare host lands there.
  if (host === "console" && pathname === "/") return <RedirectTo to="/console" />;
  return <NotFoundPage />;
}

function RedirectTo({ to, from }: { to: "/console" | "/console/login"; from?: string }) {
  const navigate = useNavigate();
  useEffect(() => {
    navigate({
      to,
      search: to === "/console/login" ? { redirect: from } : undefined,
      replace: true,
    } as Parameters<typeof navigate>[0]);
  }, [navigate, to, from]);
  return <FullPageSkeleton />;
}

/**
 * School pages only while the school is open. A suspended (or pending
 * deletion) school shows the suspended page, one still being set up shows
 * that; an API call refused mid session (school_suspended, school_not_ready)
 * checks again at once. Ordo support still gets into a suspended school.
 */
export function RequireOpenSchool({ children }: { children: ReactNode }) {
  const status = useSchoolStatus();
  const qc = useQueryClient();
  useEffect(() => {
    const recheck = () => void qc.invalidateQueries({ queryKey: SCHOOL_STATUS_KEY });
    window.addEventListener(SCHOOL_CLOSED_EVENT, recheck);
    return () => window.removeEventListener(SCHOOL_CLOSED_EVENT, recheck);
  }, [qc]);

  if (status.isLoading) return <FullPageSkeleton />;
  // Unreachable status: let the pages try, and refuse on their own.
  if (!status.data) return <>{children}</>;
  const { name } = status.data;
  switch (status.data.status) {
    case "suspended":
    case "pending_deletion":
      if (hasLiveSupportToken()) return <>{children}</>;
      return <SchoolSuspendedPage name={name} />;
    case "provisioning":
    case "failed":
      return <SchoolSettingUpPage name={name} />;
    default:
      return <>{children}</>;
  }
}

/** Signed in platform admins only; others go to the console sign in. */
export function RequirePlatformAuth({ children }: { children: ReactNode }) {
  const { status } = usePlatformAuth();
  const [from] = useState(useLocation().href);
  if (status === "loading") return <FullPageSkeleton />;
  if (status === "unauthenticated") return <RedirectTo to="/console/login" from={from} />;
  return <>{children}</>;
}

/** Owner only console pages; Support is sent to the console overview. */
export function RequirePlatformOwner({ children }: { children: ReactNode }) {
  const { admin } = usePlatformAuth();
  if (!isPlatformOwner(admin)) return <RedirectTo to="/console" />;
  return <>{children}</>;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "loading") return <FullPageSkeleton />;
  if (status === "unauthenticated") return <RedirectToLogin />;
  return <>{children}</>;
}

/** Gate children behind a capability predicate; redirect others home. */
function RequireCapability({
  allow,
  children,
}: {
  allow: (u: AuthUser | null) => boolean;
  children: ReactNode;
}) {
  const { status, user } = useAuth();
  if (status === "loading") return <FullPageSkeleton />;
  if (status === "unauthenticated") return <RedirectToLogin />;
  if (!allow(user)) return <RedirectHome />;
  return <>{children}</>;
}

export const RequireSuperAdmin = ({ children }: { children: ReactNode }) => (
  <RequireCapability allow={isSuperAdmin}>{children}</RequireCapability>
);

export const RequireDataOfficer = ({ children }: { children: ReactNode }) => (
  <RequireCapability allow={canManageData}>{children}</RequireCapability>
);

export const RequireFacultyOfficer = ({ children }: { children: ReactNode }) => (
  <RequireCapability allow={canManageFaculties}>{children}</RequireCapability>
);

export const RequireCommittee = ({ children }: { children: ReactNode }) => (
  <RequireCapability allow={isCommittee}>{children}</RequireCapability>
);

/**
 * A page the school's plan may leave off. The server refuses it either way;
 * this says so plainly instead of showing a page of errors.
 */
export function RequireFeature({ feature, children }: { feature: FeatureKey; children: ReactNode }) {
  const plan = useSchoolPlan();
  if (plan.isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (plan.data && !plan.data.features.includes(feature)) {
    return (
      <Alert>
        <AlertTitle>{FEATURE_LABELS[feature]} isn't in your plan</AlertTitle>
        <AlertDescription>
          Your school's plan doesn't include this. Contact Ordo if you'd like it added.
        </AlertDescription>
      </Alert>
    );
  }
  return <>{children}</>;
}

function FullPageSkeleton() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-8">
      <div className="w-full max-w-3xl space-y-3">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  );
}
