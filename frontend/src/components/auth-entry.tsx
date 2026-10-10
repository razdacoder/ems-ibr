import { ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useOrigins } from "@/lib/config";
import { cn } from "@/lib/utils";

/**
 * Where the public pages should send someone: the dashboard on the app
 * subdomain. The session token lives in the app host's storage, so the
 * site can't tell whether you're signed in — the dashboard's route guard
 * forwards anyone signed out to its login page.
 */
export function useAuthEntry() {
  return { href: `${useOrigins().app}/` };
}

/** Header call-to-action into the dashboard. */
export function AuthButton({
  size = "sm",
  className,
}: {
  size?: "sm" | "default";
  className?: string;
}) {
  const { href } = useAuthEntry();
  return (
    <Button
      render={<a href={href} />}
      variant="brand"
      size={size}
      className={cn(className)}
    >
      Sign in
      <ArrowUpRight data-icon="inline-end" strokeWidth={2.25} />
    </Button>
  );
}
