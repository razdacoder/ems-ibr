import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import {
  canManageData,
  canManageFaculties,
  isCommittee,
  isSuperAdmin,
  useAuth,
  type AuthUser,
} from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSkeleton />;
  if (status === "unauthenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

/** Gate children behind a capability predicate; redirect elsewhere to /dashboard. */
function RequireCapability({
  allow,
  children,
}: {
  allow: (u: AuthUser | null) => boolean;
  children: ReactNode;
}) {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageSkeleton />;
  if (status === "unauthenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!allow(user)) {
    return <Navigate to="/dashboard" replace />;
  }
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
