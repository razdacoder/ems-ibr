import { Link, Outlet, useLocation } from "@tanstack/react-router";
import { LogOut, type LucideIcon, School, ScrollText, ShieldCheck } from "lucide-react";
import type { AppPath } from "@/lib/paths";
import {
  isPlatformOwner,
  PLATFORM_ROLE_LABELS,
  usePlatformAuth,
  type PlatformAdmin,
} from "@/lib/platform-auth";
import { cn } from "@/lib/utils";
import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface NavItem {
  to: AppPath;
  label: string;
  icon: LucideIcon;
  requires?: (a: PlatformAdmin | null) => boolean;
  /** Also active on these sub paths (the console home is /console itself). */
  also?: string;
}

// Plans and support sessions join as their build slices land.
const NAV: NavItem[] = [
  { to: "/console", label: "Schools", icon: School, also: "/console/schools" },
  { to: "/console/admins", label: "Admins", icon: ShieldCheck, requires: isPlatformOwner },
  { to: "/console/audit", label: "Audit log", icon: ScrollText },
];

/** The signed in console at admin.<base>: top bar, nav and the page. */
export function ConsoleLayout() {
  const { admin, logout } = usePlatformAuth();
  const { pathname } = useLocation();
  const items = NAV.filter((item) => !item.requires || item.requires(admin));
  const initials =
    admin?.name
      .split(/\s+/)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || "?";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-[color:var(--border)] bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <Link to="/console" className="inline-flex items-center gap-3" aria-label="Schools">
            <Wordmark />
            <span className="hidden rounded-full border border-[color:var(--border)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground sm:inline">
              Console
            </span>
          </Link>
          <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto" aria-label="Console">
            {items.map(({ to, label, icon: Icon, also }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/console" }}
                className={cn(
                  "inline-flex shrink-0 items-center gap-2 rounded-md px-2.5 py-1.5 text-[13.5px] font-medium transition-colors",
                  also && pathname.startsWith(also) && "bg-[color:var(--brand-soft)] text-[color:var(--brand-strong)]",
                )}
                activeProps={{ className: "bg-[color:var(--brand-soft)] text-[color:var(--brand-strong)]" }}
                inactiveProps={{
                  className:
                    also && pathname.startsWith(also) ? "" : "text-muted-foreground hover:text-foreground",
                }}
              >
                <Icon className="size-3.5" strokeWidth={2} aria-hidden />
                <span className="hidden md:inline">{label}</span>
                <span className="sr-only md:hidden">{label}</span>
              </Link>
            ))}
          </nav>
          <ThemeToggle size="sm" iconOnly />
          <DropdownMenu>
            <DropdownMenuTrigger
              className={cn(
                "grid size-8 shrink-0 place-items-center rounded-full font-mono text-[11px] font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
              )}
              style={{ backgroundColor: "var(--brand)", color: "var(--brand-foreground)" }}
              aria-label="Account menu"
            >
              {initials}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={8} className="min-w-[220px]">
              <DropdownMenuLabel>
                <span className="block truncate text-[13px] font-medium">{admin?.name}</span>
                <span className="block truncate text-[12px] font-normal text-muted-foreground">
                  {admin?.email} · {admin ? PLATFORM_ROLE_LABELS[admin.role] : ""}
                </span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => void logout()}>
                <LogOut className="mr-2 size-3.5" strokeWidth={2} />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
