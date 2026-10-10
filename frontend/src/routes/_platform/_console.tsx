import { createFileRoute } from "@tanstack/react-router";
import { ConsoleLayout } from "@/components/layout/console-layout";
import { RequirePlatformAuth } from "@/components/route-guards";

// Every signed in console page: session gate plus the console shell.
export const Route = createFileRoute("/_platform/_console")({
  component: () => (
    <RequirePlatformAuth>
      <ConsoleLayout />
    </RequirePlatformAuth>
  ),
});
