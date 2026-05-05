import { NavLink, Outlet } from "react-router-dom";
import {
  Building2,
  CalendarDays,
  ClipboardList,
  Download,
  GraduationCap,
  Grid3x3,
  LayoutDashboard,
  ListChecks,
  LogOut,
  School,
  Settings,
  Upload,
  Users,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/departments", label: "Departments", icon: Building2 },
  { to: "/classes", label: "Classes", icon: School },
  { to: "/courses", label: "Courses", icon: ClipboardList },
  { to: "/students", label: "Students", icon: GraduationCap },
  { to: "/halls", label: "Halls", icon: Grid3x3 },
  { to: "/timetable", label: "Timetable", icon: CalendarDays },
  { to: "/distribution", label: "Distribution", icon: ListChecks },
  { to: "/allocation", label: "Allocation", icon: ListChecks },
  { to: "/jobs", label: "Jobs", icon: ListChecks },
  { to: "/uploads", label: "Uploads", icon: Upload, adminOnly: true },
  { to: "/exports", label: "Exports", icon: Download },
  { to: "/users", label: "Users", icon: Users, adminOnly: true },
  { to: "/settings", label: "Settings", icon: Settings, adminOnly: true },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || user?.is_staff);

  return (
    <div className="flex min-h-screen bg-muted/30">
      <aside className="hidden w-64 flex-col border-r bg-background lg:flex">
        <div className="flex h-16 items-center border-b px-6 font-semibold">
          EMS-IBR
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t p-3">
          <div className="mb-2 px-3 text-xs text-muted-foreground">
            <div className="font-medium text-foreground">{user?.full_name}</div>
            <div>{user?.email}</div>
          </div>
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={() => {
              void logout();
            }}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
