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
import { useHostKind } from "@/lib/config";
import type { HostKind } from "@/lib/origins.server";
import { Skeleton } from "@/components/ui/skeleton";
import NotFoundPage from "@/pages/not-found";

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
 * console pages on admin.<base>. Anywhere else is the not found page.
 */
export function RequireHost({
  kind,
  children,
}: {
  kind: HostKind;
  children: ReactNode;
}) {
  if (useHostKind() !== kind) return <NotFoundPage />;
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
