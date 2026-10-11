import { useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowUpRight,
  CalendarClock,
  CircleCheck,
  GraduationCap,
  LifeBuoy,
  ListChecks,
  type LucideIcon,
  Plus,
  School,
  Trash2,
  UserRound,
  PauseCircle,
} from "lucide-react";
import {
  type AttentionKind,
  type PlatformOverview,
  type SchoolStatus,
  usePlatformOverview,
} from "@/api/platform";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorEnvelope } from "@/lib/api";
import { isPlatformOwner, usePlatformAuth } from "@/lib/platform-auth";
import { cn } from "@/lib/utils";
import { ACTION_LABELS } from "./audit";
import { SchoolStatusBadge, formatDay } from "./schools";

const LABEL = "font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground";

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function timeAgo(iso: string) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return shortDate(iso);
}

/** A square bordered panel with a title row, the dashboard's building block. */
function Panel({
  title,
  action,
  className,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn("flex flex-col border border-[color:var(--border)] bg-card", className)}>
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-[color:var(--border)] px-5">
        <h2 className="text-[13.5px] font-medium">{title}</h2>
        {action}
      </div>
      <div className="flex-1">{children}</div>
    </section>
  );
}

function PanelLink({ to, children }: { to: "/console/schools" | "/console/audit" | "/console/plans"; children: string }) {
  return (
    <Link
      to={to}
      className="group inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
    >
      {children}
      <ArrowUpRight className="size-3 transition-transform group-hover:-translate-y-px group-hover:translate-x-px" />
    </Link>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="px-5 py-8 text-center text-[13px] text-muted-foreground">{children}</p>;
}

/* ---------------------------------------------------------------- tiles */

function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  loading,
}: {
  label: string;
  value: number | undefined;
  hint?: string;
  icon: LucideIcon;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col justify-between gap-5 border border-[color:var(--border)] bg-card p-5">
      <div className="flex items-start justify-between">
        <span className={LABEL}>{label}</span>
        <span
          className="grid size-7 place-items-center"
          style={{ backgroundColor: "var(--brand-soft)", color: "var(--brand-strong)" }}
        >
          <Icon className="size-3.5" strokeWidth={2} aria-hidden />
        </span>
      </div>
      {loading ? (
        <Skeleton className="h-10 w-24" />
      ) : (
        <div>
          <div className="font-serif text-[2.5rem] leading-none tabular-nums tracking-[-0.02em]">
            {(value ?? 0).toLocaleString()}
          </div>
          {hint && <p className="mt-2 text-[12px] text-muted-foreground">{hint}</p>}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- trend */

const CHART_W = 600;
const CHART_H = 180;

/** Students across all schools per day: one line, crosshair and tooltip on hover. */
function StudentTrend({ trend }: { trend: PlatformOverview["trend"] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (trend.length < 2) {
    return <Empty>The trend fills in as nightly usage snapshots are taken.</Empty>;
  }

  const values = trend.map((d) => d.students);
  const max = Math.max(...values, 1);
  // A rounded top so gridlines land on readable numbers.
  const magnitude = 10 ** Math.floor(Math.log10(max));
  const top = Math.ceil(max / magnitude) * magnitude;
  const x = (i: number) => (i / (trend.length - 1)) * CHART_W;
  const y = (v: number) => CHART_H - (v / top) * CHART_H;
  const line = values.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
  const area = `${line} L${CHART_W},${CHART_H} L0,${CHART_H} Z`;
  const point = hover === null ? null : trend[hover];

  return (
    <div className="px-5 pt-4 pb-3">
      <div className="flex gap-3">
        {/* y axis */}
        <div className="flex h-[180px] flex-col justify-between text-right font-mono text-[10px] tabular-nums text-muted-foreground">
          <span>{top.toLocaleString()}</span>
          <span>{(top / 2).toLocaleString()}</span>
          <span>0</span>
        </div>
        <div
          className="relative h-[180px] flex-1"
          onPointerMove={(e) => {
            const box = e.currentTarget.getBoundingClientRect();
            const ratio = Math.min(Math.max((e.clientX - box.left) / box.width, 0), 1);
            setHover(Math.round(ratio * (trend.length - 1)));
          }}
          onPointerLeave={() => setHover(null)}
        >
          <svg
            viewBox={`0 0 ${CHART_W} ${CHART_H}`}
            preserveAspectRatio="none"
            className="absolute inset-0 size-full overflow-visible"
            role="img"
            aria-label={`Students across all schools, ${shortDate(trend[0].date)} to ${shortDate(trend[trend.length - 1].date)}`}
          >
            {[0, 0.5, 1].map((t) => (
              <line
                key={t}
                x1={0}
                x2={CHART_W}
                y1={CHART_H * t}
                y2={CHART_H * t}
                stroke="var(--border)"
                vectorEffect="non-scaling-stroke"
              />
            ))}
            <path d={area} fill="var(--brand-soft)" opacity={0.6} />
            <path
              d={line}
              fill="none"
              stroke="var(--brand-strong)"
              strokeWidth={2}
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
            {hover !== null && (
              <line
                x1={x(hover)}
                x2={x(hover)}
                y1={0}
                y2={CHART_H}
                stroke="var(--muted-foreground)"
                strokeDasharray="3 3"
                vectorEffect="non-scaling-stroke"
              />
            )}
          </svg>
          {point && hover !== null && (
            <>
              <span
                aria-hidden
                className="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card"
                style={{
                  left: `${(hover / (trend.length - 1)) * 100}%`,
                  top: `${(y(point.students) / CHART_H) * 100}%`,
                  backgroundColor: "var(--brand-strong)",
                }}
              />
              <div
                className="pointer-events-none absolute top-0 z-10 min-w-[150px] border border-[color:var(--border)] bg-popover px-3 py-2 text-[12px] shadow-md"
                style={
                  hover > (trend.length - 1) / 2
                    ? { right: `${100 - (hover / (trend.length - 1)) * 100}%`, marginRight: 10 }
                    : { left: `${(hover / (trend.length - 1)) * 100}%`, marginLeft: 10 }
                }
              >
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                  {formatDay(point.date)}
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Students</span>
                  <span className="font-medium tabular-nums">{point.students.toLocaleString()}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Staff</span>
                  <span className="tabular-nums">{point.staff_users.toLocaleString()}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-muted-foreground">Jobs</span>
                  <span className="tabular-nums">{point.jobs.toLocaleString()}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      <div className="mt-2 flex justify-between pl-10 font-mono text-[10px] text-muted-foreground">
        <span>{shortDate(trend[0].date)}</span>
        <span>{shortDate(trend[trend.length - 1].date)}</span>
      </div>
      {/* The same numbers for screen readers. */}
      <table className="sr-only">
        <caption>Daily usage across all schools</caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>Students</th>
            <th>Staff</th>
            <th>Jobs</th>
          </tr>
        </thead>
        <tbody>
          {trend.map((d) => (
            <tr key={d.date}>
              <td>{d.date}</td>
              <td>{d.students}</td>
              <td>{d.staff_users}</td>
              <td>{d.jobs}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------------------------------------------------------------- lists */

const STATUS_ORDER: SchoolStatus[] = [
  "active",
  "provisioning",
  "suspended",
  "pending_deletion",
  "failed",
  "purged",
];

function StatusBreakdown({ byStatus }: { byStatus: Record<SchoolStatus, number> }) {
  const rows = STATUS_ORDER.filter((s) => byStatus[s] > 0);
  if (!rows.length) return <Empty>No schools yet.</Empty>;
  return (
    <ul className="divide-y divide-[color:var(--border)]">
      {rows.map((status) => (
        <li key={status} className="flex items-center justify-between px-5 py-3">
          <SchoolStatusBadge status={status} />
          <span className="font-mono text-[13px] tabular-nums">{byStatus[status]}</span>
        </li>
      ))}
    </ul>
  );
}

const ATTENTION: Record<AttentionKind, { icon: LucideIcon; text: (at: string | null) => string; tone: string }> = {
  failed: { icon: AlertTriangle, text: () => "Setup failed", tone: "text-destructive" },
  pending_deletion: {
    icon: Trash2,
    text: (at) => (at ? `Data purged ${formatDay(at)}` : "Pending deletion"),
    tone: "text-destructive",
  },
  suspended: {
    icon: PauseCircle,
    text: (at) => (at ? `Suspended ${formatDay(at)}` : "Suspended"),
    tone: "text-[color:var(--accent-amber-fg)]",
  },
  renewal_overdue: {
    icon: CalendarClock,
    text: (at) => `Renewal lapsed ${formatDay(at)}`,
    tone: "text-destructive",
  },
  renewal_due: {
    icon: CalendarClock,
    text: (at) => `Renews ${formatDay(at)}`,
    tone: "text-[color:var(--accent-amber-fg)]",
  },
};

function AttentionList({ items }: { items: PlatformOverview["attention"] }) {
  if (!items.length) {
    return (
      <div className="flex items-center justify-center gap-2 px-5 py-8 text-[13px] text-muted-foreground">
        <CircleCheck className="size-4" aria-hidden />
        Nothing needs attention.
      </div>
    );
  }
  return (
    <ul className="divide-y divide-[color:var(--border)]">
      {items.map((item) => {
        const { icon: Icon, text, tone } = ATTENTION[item.kind];
        return (
          <li key={`${item.kind}-${item.school.id}`}>
            <Link
              to="/console/schools/$id"
              params={{ id: String(item.school.id) }}
              className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[color:var(--muted)]/50"
            >
              <Icon className={cn("size-4 shrink-0", tone)} aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13.5px] font-medium">{item.school.name}</span>
                <span className="block truncate font-mono text-[11px] text-muted-foreground">
                  {item.school.slug}
                </span>
              </span>
              <span className={cn("shrink-0 text-[12.5px]", tone)}>{text(item.at)}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function SupportList({ sessions }: { sessions: PlatformOverview["support"] }) {
  if (!sessions.length) return <Empty>No one is in a school right now.</Empty>;
  return (
    <ul className="divide-y divide-[color:var(--border)]">
      {sessions.map((s) => (
        <li key={s.id} className="px-5 py-3">
          <div className="flex items-center justify-between gap-3">
            <Link
              to="/console/schools/$id"
              params={{ id: String(s.school.id) }}
              className="truncate text-[13.5px] font-medium hover:underline"
            >
              {s.school.name}
            </Link>
            <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
              until{" "}
              {new Date(s.expires_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          <p className="mt-0.5 truncate text-[12.5px] text-muted-foreground">
            {s.admin.name}: {s.reason}
          </p>
        </li>
      ))}
    </ul>
  );
}

function PlanBars({ plans }: { plans: PlatformOverview["plans"] }) {
  if (!plans.length) return <Empty>No plans yet.</Empty>;
  const max = Math.max(...plans.map((p) => p.schools), 1);
  return (
    <ul className="space-y-3 px-5 py-4">
      {plans.map((plan) => (
        <li key={plan.id} title={`${plan.name}: ${plan.schools} schools`}>
          <div className="mb-1 flex justify-between text-[12.5px]">
            <span>{plan.name}</span>
            <span className="font-mono tabular-nums text-muted-foreground">{plan.schools}</span>
          </div>
          <div className="h-1.5 w-full bg-[color:var(--muted)]">
            <div
              className="h-full"
              style={{
                width: `${(plan.schools / max) * 100}%`,
                backgroundColor: "var(--brand-strong)",
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function RecentActivity({ rows }: { rows: PlatformOverview["recent_activity"] }) {
  if (!rows.length) return <Empty>Nothing recorded yet.</Empty>;
  return (
    <ul className="divide-y divide-[color:var(--border)]">
      {rows.map((row) => (
        <li key={row.id} className="flex items-start gap-3 px-5 py-3">
          <UserRound className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <div className="min-w-0 flex-1 text-[13px]">
            <span className="font-medium">{row.admin?.name ?? "System"}</span>{" "}
            <span className="text-muted-foreground">
              {(ACTION_LABELS[row.action] ?? row.action.replaceAll("_", " ")).toLowerCase()}
            </span>
            {row.school && <span className="font-medium"> · {row.school.name}</span>}
          </div>
          <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{timeAgo(row.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}

/* ---------------------------------------------------------------- page */

/** The console's home: platform health at a glance. */
export default function ConsoleDashboardPage() {
  const { admin } = usePlatformAuth();
  const overview = usePlatformOverview();
  const data = overview.data;
  const loading = overview.isLoading;
  const asOf = data?.usage.as_of ? `As of ${formatDay(data.usage.as_of)}` : "No snapshot yet";

  return (
    <div className="space-y-8">
      <PageHeader
        section="Console"
        title="Dashboard"
        description="Every school on Ordo at a glance: who is using it, what needs a look, and what changed."
        actions={
          isPlatformOwner(admin) && (
            <Link to="/console/schools/new" className={buttonVariants({ variant: "brand" })}>
              <Plus data-icon="inline-start" />
              New school
            </Link>
          )
        }
      />

      {overview.error && (
        <Alert variant="destructive">
          <AlertDescription>{extractErrorEnvelope(overview.error).detail}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Schools"
          icon={School}
          loading={loading}
          value={data?.schools.total}
          hint={data && `${data.schools.new_last_30_days} new in 30 days`}
        />
        <StatTile label="Students" icon={GraduationCap} loading={loading} value={data?.usage.students} hint={asOf} />
        <StatTile label="Staff users" icon={UserRound} loading={loading} value={data?.usage.staff_users} hint={asOf} />
        <StatTile
          label="Jobs in 24h"
          icon={ListChecks}
          loading={loading}
          value={data?.usage.jobs_last_24h}
          hint={asOf}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Panel title="Students across all schools" className="lg:col-span-2" action={<span className={LABEL}>30 days</span>}>
          {loading ? <Skeleton className="m-5 h-[180px]" /> : <StudentTrend trend={data?.trend ?? []} />}
        </Panel>
        <Panel title="Schools by status" action={<PanelLink to="/console/schools">All schools</PanelLink>}>
          {loading ? <Skeleton className="m-5 h-32" /> : data && <StatusBreakdown byStatus={data.schools.by_status} />}
        </Panel>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Panel
          title="Needs attention"
          className="lg:col-span-2"
          action={data && data.attention.length > 0 && <span className={LABEL}>{data.attention.length}</span>}
        >
          {loading ? <Skeleton className="m-5 h-32" /> : <AttentionList items={data?.attention ?? []} />}
        </Panel>
        <Panel
          title="Support sessions"
          action={<LifeBuoy className="size-3.5 text-muted-foreground" aria-hidden />}
        >
          {loading ? <Skeleton className="m-5 h-20" /> : <SupportList sessions={data?.support ?? []} />}
        </Panel>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Panel title="Schools per plan" action={<PanelLink to="/console/plans">Plans</PanelLink>}>
          {loading ? <Skeleton className="m-5 h-24" /> : <PlanBars plans={data?.plans ?? []} />}
        </Panel>
        <Panel
          title="Recent activity"
          className="lg:col-span-2"
          action={<PanelLink to="/console/audit">Audit log</PanelLink>}
        >
          {loading ? <Skeleton className="m-5 h-40" /> : <RecentActivity rows={data?.recent_activity ?? []} />}
        </Panel>
      </div>
    </div>
  );
}
