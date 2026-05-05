import { Link } from "react-router-dom";
import { useDashboardStats } from "@/api/system";
import { useAuth } from "@/lib/auth";
import {
  ArrowUpRight,
  Building2,
  CalendarDays,
  ClipboardList,
  GraduationCap,
  Grid3x3,
  School,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

const TILES = [
  {
    key: "departments_count" as const,
    label: "Departments",
    icon: Building2,
    to: "/departments",
  },
  {
    key: "classes_count" as const,
    label: "Classes",
    icon: School,
    to: "/classes",
  },
  {
    key: "courses_count" as const,
    label: "Courses",
    icon: ClipboardList,
    to: "/courses",
  },
  {
    key: "halls_count" as const,
    label: "Halls",
    icon: Grid3x3,
    to: "/halls",
  },
  {
    key: "students_count" as const,
    label: "Students",
    icon: GraduationCap,
    to: "/students",
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const stats = useDashboardStats();
  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  })();
  const today = new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="space-y-12">
      {/* HEADER */}
      <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            § Overview · {today}
          </p>
          <h1 className="mt-3 font-serif text-[2.75rem] leading-[1.05] tracking-[-0.015em] sm:text-[3.25rem]">
            {greeting},{" "}
            <span className="italic text-muted-foreground">
              {user?.first_name ?? user?.full_name ?? user?.email}
            </span>
            .
          </h1>
        </div>
        <dl className="flex flex-col items-end gap-1 self-start sm:self-end">
          <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Active session
          </dt>
          {stats.isLoading ? (
            <Skeleton className="h-7 w-32" />
          ) : (
            <dd className="font-serif text-[1.5rem] tabular-nums">
              {stats.data?.settings.session}
              <span className="ml-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                · {stats.data?.settings.semester}
              </span>
            </dd>
          )}
        </dl>
      </header>

      {/* STATS */}
      <section>
        <div className="mb-6 flex items-end justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            § 01 — Catalog
          </p>
          <Link
            to="/departments"
            className="group inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
          >
            View all
            <ArrowUpRight
              className="size-3 transition-transform group-hover:-translate-y-px group-hover:translate-x-px"
              strokeWidth={2.25}
            />
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[12px] border border-[color:var(--border)] bg-[color:var(--border)] sm:grid-cols-3 lg:grid-cols-5">
          {TILES.map(({ key, label, icon: Icon, to }) => (
            <Link
              key={key}
              to={to}
              className="group relative flex flex-col justify-between gap-6 bg-card p-6 transition-colors hover:bg-[color:var(--muted)]"
            >
              <div className="flex items-start justify-between">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  {label}
                </span>
                <Icon
                  className="size-3.5 text-muted-foreground transition-colors group-hover:text-foreground"
                  strokeWidth={2}
                />
              </div>
              {stats.isLoading ? (
                <Skeleton className="h-10 w-24" />
              ) : (
                <div className="font-serif text-[2.5rem] leading-none tabular-nums tracking-[-0.01em]">
                  {(stats.data?.[key] ?? 0).toLocaleString()}
                </div>
              )}
            </Link>
          ))}
        </div>
      </section>

      {/* OPERATIONS QUICK NAV */}
      <section>
        <div className="mb-6 flex items-end justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            § 02 — Operations
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              to: "/timetable",
              label: "Timetable",
              hint: "Generate or review the season grid.",
              accent: "var(--accent-yellow)",
              accentFg: "var(--accent-yellow-fg)",
            },
            {
              to: "/distribution",
              label: "Distribution",
              hint: "Capacity-aware hall assignment.",
              accent: "var(--accent-blue)",
              accentFg: "var(--accent-blue-fg)",
            },
            {
              to: "/allocation",
              label: "Allocation",
              hint: "Seat-by-seat anti-cheating placement.",
              accent: "var(--accent-red)",
              accentFg: "var(--accent-red-fg)",
            },
            {
              to: "/jobs",
              label: "Jobs",
              hint: "Live progress for in-flight runs.",
              accent: "var(--accent-green)",
              accentFg: "var(--accent-green-fg)",
            },
          ].map((op) => (
            <Link
              key={op.to}
              to={op.to}
              className="group flex flex-col justify-between gap-6 rounded-[12px] border border-[color:var(--border)] bg-card p-5 transition-all duration-300 hover:-translate-y-px hover:border-foreground/20"
            >
              <div className="flex items-center justify-between">
                <span
                  className="inline-block rounded-full px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
                  style={{
                    backgroundColor: op.accent,
                    color: op.accentFg,
                  }}
                >
                  {op.label}
                </span>
                <ArrowUpRight
                  className="size-3.5 text-muted-foreground transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
                  strokeWidth={2.25}
                />
              </div>
              <p className="font-serif text-[1.25rem] leading-snug tracking-[-0.005em]">
                {op.hint}
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* SHARED COURSES (admin) */}
      {user?.is_staff && (stats.data?.shared_courses_count ?? 0) > 0 && (
        <section>
          <div className="mb-6 flex items-end justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                § 03 — Cross-department
              </p>
              <h2 className="mt-2 flex items-center gap-3 font-serif text-[2rem] leading-[1.05] tracking-[-0.015em]">
                Shared courses
                <span className="rounded-full bg-[color:var(--accent-yellow)] px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--accent-yellow-fg)]">
                  {stats.data?.shared_courses_count} flagged
                </span>
              </h2>
            </div>
            <CalendarDays
              className="size-4 text-muted-foreground"
              strokeWidth={2}
            />
          </div>
          <p className="mb-6 max-w-2xl text-[14px] leading-[1.65] text-muted-foreground">
            Courses appearing in classes across multiple departments — these
            create cross-department timetable constraints. Review them before
            generating the next run.
          </p>
          <ul className="divide-y divide-[color:var(--border)] overflow-hidden rounded-[12px] border border-[color:var(--border)] bg-card">
            {stats.data?.shared_courses.slice(0, 8).map((c) => (
              <li
                key={c.code}
                className="grid grid-cols-12 gap-4 px-6 py-5 transition-colors hover:bg-[color:var(--muted)]"
              >
                <div className="col-span-12 sm:col-span-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                    {c.code}
                  </p>
                  <p className="mt-1 font-serif text-[1.125rem] leading-tight tracking-[-0.005em]">
                    {c.name}
                  </p>
                </div>
                <div className="col-span-12 sm:col-span-7">
                  <div className="flex flex-wrap gap-1.5">
                    {c.departments.flatMap((d) =>
                      d.classes.map((cls) => (
                        <span
                          key={`${d.name}-${cls}`}
                          className="rounded-md border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[10px] tracking-wide text-foreground"
                        >
                          {d.name} · {cls}
                        </span>
                      )),
                    )}
                  </div>
                </div>
                <div className="col-span-12 self-center text-right sm:col-span-1">
                  <span className="font-serif text-[1.25rem] tabular-nums">
                    {c.dept_count}
                  </span>
                  <span className="ml-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                    depts
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
