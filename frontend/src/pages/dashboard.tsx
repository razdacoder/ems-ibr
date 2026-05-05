import { useDashboardStats } from "@/api/system";
import { useAuth } from "@/lib/auth";
import {
  Building2,
  CalendarDays,
  ClipboardList,
  GraduationCap,
  Grid3x3,
  School,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const TILES = [
  { key: "departments_count" as const, label: "Departments", icon: Building2 },
  { key: "classes_count" as const, label: "Classes", icon: School },
  { key: "courses_count" as const, label: "Courses", icon: ClipboardList },
  { key: "halls_count" as const, label: "Halls", icon: Grid3x3 },
  { key: "students_count" as const, label: "Students", icon: GraduationCap },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const stats = useDashboardStats();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          Welcome, {user?.full_name}
        </h1>
        <p className="text-sm text-muted-foreground">
          {stats.data?.settings.session} · {stats.data?.settings.semester}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
        {TILES.map(({ key, label, icon: Icon }) => (
          <Card key={key}>
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{label}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {stats.isLoading ? (
                <Skeleton className="h-8 w-20" />
              ) : (
                <div className="text-2xl font-bold">
                  {stats.data?.[key] ?? 0}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {user?.is_staff && (stats.data?.shared_courses_count ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarDays className="h-4 w-4" />
              Shared courses
              <Badge variant="secondary">
                {stats.data?.shared_courses_count}
              </Badge>
            </CardTitle>
            <CardDescription>
              Courses appearing in classes across multiple departments — these
              create cross-department timetable constraints.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.data?.shared_courses.slice(0, 8).map((c) => (
              <div
                key={c.code}
                className="rounded-md border bg-muted/30 p-3 text-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold">
                    {c.code} — {c.name}
                  </div>
                  <Badge>{c.dept_count} departments</Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.departments.flatMap((d) =>
                    d.classes.map((cls) => (
                      <Badge key={`${d.name}-${cls}`} variant="outline">
                        {d.name} · {cls}
                      </Badge>
                    )),
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
