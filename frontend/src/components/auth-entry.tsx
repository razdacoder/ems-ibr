import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

/**
 * Where the public pages should send someone: the dashboard if they're
 * already signed in, the login page otherwise.
 */
export function useAuthEntry() {
  const { status } = useAuth();
  const signedIn = status === "authenticated";
  return {
    signedIn,
    /** False while the stored session is still being checked. */
    ready: status !== "loading",
    to: signedIn ? "/dashboard" : "/login",
  };
}

/**
 * Header call-to-action that knows whether you're signed in. Holds its
 * width (invisible) while the session check runs so the header doesn't jump.
 */
export function AuthButton({
  size = "sm",
  className,
}: {
  size?: "sm" | "default";
  className?: string;
}) {
  const { signedIn, ready, to } = useAuthEntry();
  return (
    <Button
      render={<Link to={to} />}
      variant="brand"
      size={size}
      aria-hidden={!ready}
      tabIndex={ready ? undefined : -1}
      className={cn(!ready && "invisible", className)}
    >
      {signedIn ? "Dashboard" : "Sign in"}
      <ArrowUpRight data-icon="inline-end" strokeWidth={2.25} />
    </Button>
  );
}
