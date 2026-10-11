import { useState } from "react";

const W = 600;
const H = 180;

function shortDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function longDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

export interface TrendPoint {
  date: string;
  value: number;
  /** Extra lines for the tooltip, e.g. staff and jobs that day. */
  details?: Array<[string, number]>;
}

/**
 * One series over time: a 2px line on a soft area, recessive gridlines, and
 * a crosshair with a tooltip on hover. ``limit`` draws a dashed line for a
 * plan's cap. The same numbers sit in a visually hidden table.
 */
export function TrendChart({
  points,
  label,
  limit,
  empty = "The trend fills in as nightly usage snapshots are taken.",
}: {
  points: TrendPoint[];
  label: string;
  limit?: number | null;
  empty?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length < 2) {
    return <p className="px-5 py-8 text-center text-[13px] text-muted-foreground">{empty}</p>;
  }

  const max = Math.max(...points.map((p) => p.value), limit ?? 0, 1);
  // A rounded top so gridlines land on readable numbers.
  const magnitude = 10 ** Math.floor(Math.log10(max));
  const top = Math.ceil(max / magnitude) * magnitude;
  const last = points.length - 1;
  const x = (i: number) => (i / last) * W;
  const y = (v: number) => H - (v / top) * H;
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ");
  const area = `${line} L${W},${H} L0,${H} Z`;
  const point = hover === null ? null : points[hover];
  const pct = (i: number) => (i / last) * 100;

  return (
    <div className="px-5 pt-4 pb-3">
      <div className="flex gap-3">
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
            setHover(Math.round(ratio * last));
          }}
          onPointerLeave={() => setHover(null)}
        >
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            className="absolute inset-0 size-full overflow-visible"
            role="img"
            aria-label={`${label}, ${shortDate(points[0].date)} to ${shortDate(points[last].date)}`}
          >
            {[0, 0.5, 1].map((t) => (
              <line
                key={t}
                x1={0}
                x2={W}
                y1={H * t}
                y2={H * t}
                stroke="var(--border)"
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {limit != null && (
              <line
                x1={0}
                x2={W}
                y1={y(limit)}
                y2={y(limit)}
                stroke="var(--destructive)"
                strokeDasharray="5 4"
                vectorEffect="non-scaling-stroke"
              />
            )}
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
                y2={H}
                stroke="var(--muted-foreground)"
                strokeDasharray="3 3"
                vectorEffect="non-scaling-stroke"
              />
            )}
          </svg>
          {limit != null && (
            <span
              className="pointer-events-none absolute right-0 -translate-y-full pb-0.5 font-mono text-[10px] text-destructive"
              style={{ top: `${(y(limit) / H) * 100}%` }}
            >
              Limit {limit.toLocaleString()}
            </span>
          )}
          {point && hover !== null && (
            <>
              <span
                aria-hidden
                className="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card"
                style={{
                  left: `${pct(hover)}%`,
                  top: `${(y(point.value) / H) * 100}%`,
                  backgroundColor: "var(--brand-strong)",
                }}
              />
              <div
                className="pointer-events-none absolute top-0 z-10 min-w-[150px] border border-[color:var(--border)] bg-popover px-3 py-2 text-[12px] shadow-md"
                style={
                  hover > last / 2
                    ? { right: `${100 - pct(hover)}%`, marginRight: 10 }
                    : { left: `${pct(hover)}%`, marginLeft: 10 }
                }
              >
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                  {longDate(point.date)}
                </div>
                {[[label, point.value] as [string, number], ...(point.details ?? [])].map(([name, value], i) => (
                  <div key={name} className="flex justify-between gap-4">
                    <span className="text-muted-foreground">{name}</span>
                    <span className={i === 0 ? "font-medium tabular-nums" : "tabular-nums"}>
                      {value.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
      <div className="mt-2 flex justify-between pl-10 font-mono text-[10px] text-muted-foreground">
        <span>{shortDate(points[0].date)}</span>
        <span>{shortDate(points[last].date)}</span>
      </div>
      <table className="sr-only">
        <caption>{label} by day</caption>
        <thead>
          <tr>
            <th>Date</th>
            <th>{label}</th>
            {points[0].details?.map(([name]) => <th key={name}>{name}</th>)}
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.date}>
              <td>{p.date}</td>
              <td>{p.value}</td>
              {p.details?.map(([name, value]) => <td key={name}>{value}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
