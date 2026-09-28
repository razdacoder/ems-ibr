import { Link } from "react-router-dom";
import { AlertTriangle, Info } from "lucide-react";
import type { Readiness } from "@/api/scheduling";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const SHOW = 12;

/** Lists what blocks a generate run (empty student lists, lists changed
 * since distribution) and, as a note, inactive classes that will be
 * skipped. Renders nothing when there is nothing to say. */
export function ReadinessPanel({ report }: { report: Readiness | undefined }) {
  if (!report) return null;
  const { empty_classes, stale, skipped_inactive } = report;
  if (!empty_classes.length && !stale.length && !skipped_inactive.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      {empty_classes.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>
            {empty_classes.length} active{" "}
            {empty_classes.length === 1 ? "class has" : "classes have"} no
            students uploaded
          </AlertTitle>
          <AlertDescription>
            <p>
              Upload each class's student list, or switch the class off if it
              is not sitting this session. Generation stays locked until then.
            </p>
            <Items
              items={empty_classes.map((c) => ({
                key: String(c.class_id),
                classId: c.class_id,
                label: c.label,
                detail: c.courses.join(", "),
              }))}
            />
          </AlertDescription>
        </Alert>
      )}

      {stale.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>
            Student lists changed after distribution
          </AlertTitle>
          <AlertDescription>
            <p>
              Clear and regenerate the distribution for{" "}
              {[...new Set(stale.map((s) => `${s.date} ${s.period}`))].join(", ")}{" "}
              before allocating, so every student gets a seat.
            </p>
            <Items
              items={stale.map((s) => ({
                key: `${s.date}-${s.period}-${s.class_id}-${s.course}`,
                classId: s.class_id,
                label: s.label,
                detail: `${s.date} ${s.period} · ${s.course} · planned ${
                  s.planned ?? "none"
                }, now ${s.current}`,
              }))}
            />
          </AlertDescription>
        </Alert>
      )}

      {skipped_inactive.length > 0 && (
        <Alert>
          <Info />
          <AlertTitle>
            {skipped_inactive.length} timetabled{" "}
            {skipped_inactive.length === 1 ? "exam belongs" : "exams belong"} to
            inactive classes
          </AlertTitle>
          <AlertDescription>
            <p>Distribution will skip these and reserve no seats for them.</p>
            <Items
              items={skipped_inactive.map((s) => ({
                key: `${s.date}-${s.period}-${s.class_id}-${s.course}`,
                classId: s.class_id,
                label: s.label,
                detail: `${s.date} ${s.period} · ${s.course}`,
              }))}
            />
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

function Items({
  items,
}: {
  items: Array<{ key: string; classId: number; label: string; detail: string }>;
}) {
  const shown = items.slice(0, SHOW);
  return (
    <ul className="mt-2 space-y-1">
      {shown.map((it) => (
        <li key={it.key} className="flex flex-wrap items-baseline gap-2">
          <Link
            to={`/classes/${it.classId}`}
            className="font-medium text-foreground"
          >
            {it.label}
          </Link>
          <span className="font-mono text-[11px] text-muted-foreground">
            {it.detail}
          </span>
        </li>
      ))}
      {items.length > SHOW && (
        <li className="font-mono text-[11px] text-muted-foreground">
          and {items.length - SHOW} more
        </li>
      )}
    </ul>
  );
}
