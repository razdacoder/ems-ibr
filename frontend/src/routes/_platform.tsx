import { Outlet, createFileRoute } from "@tanstack/react-router";
import { RequireHost } from "@/components/route-guards";
import { PlatformAuthProvider } from "@/lib/platform-auth";

// Platform console (console.<base> only). Pages live under /console because
// the school group already owns /, /login and /audit; /accept is the invite
// link the spec fixes. Only the console mounts the platform session.
export const Route = createFileRoute("/_platform")({
  // Needs the platform token from localStorage: render in the browser only.
  ssr: false,
  head: () => ({ meta: [{ title: "Console | Ordo" }] }),
  component: () => (
    <RequireHost kind="console">
      <PlatformAuthProvider>
        <Outlet />
      </PlatformAuthProvider>
    </RequireHost>
  ),
});
