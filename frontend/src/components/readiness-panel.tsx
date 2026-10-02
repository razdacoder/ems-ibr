import { Link } from "react-router-dom";
import { AlertTriangle, Info } from "lucide-react";
import type { Readiness } from "@/api/scheduling";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const SHOW = 12;

/** Lists what blocks a generate run (empty student lists, lists changed
 * since distribution, seating rules the timetable no longer matches) and,
 * as a note, inactive classes that will be skipped. Renders nothing when
 * there is nothing to say. */
export function ReadinessPanel({ report }: { report: Readiness | undefined }) {
  if (!report) return null;
  const { empty_classes, stale, skipped_inactive } = report;
  const outdated_rules = report.outdated_rules ?? [];
  const closed_halls = report.closed_halls ?? [];
  if (
    !empty_classes.length &&
    !stale.length &&
    !skipped_inactive.length &&
    !outdated_rules.length &&
    !closed_halls.length
  ) {
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

      {outdated_rules.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>
            Timetable seating rule outdated for{" "}
            {[...new Set(outdated_rules.map((o) => o.course))].join(", ")}
          </AlertTitle>
          <AlertDescription>
            <p>
              These courses changed size since the timetable was generated, so
              the seating rule it chose no longer fits. Regenerate the
              timetable before distributing.
            </p>
            <ul className="mt-2 space-y-1">
              {outdated_rules.slice(0, SHOW).map((o) => (
                <li
                  key={`${o.date}-${o.period}-${o.course}`}
                  className="font-mono text-[11px] text-muted-foreground"
                >
                  {o.date} {o.period} · {o.course} · {o.students} students ·
                  timetable says {o.stored_rule}, now {o.current_rule}
                </li>
              ))}
              {outdated_rules.length > SHOW && (
                <li className="font-mono text-[11px] text-muted-foreground">
                  and {outdated_rules.length - SHOW} more
                </li>
              )}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {closed_halls.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>
            Distribution uses closed{" "}
            {new Set(closed_halls.map((h) => h.hall_id)).size === 1 ? "hall" : "halls"}
          </AlertTitle>
          <AlertDescription>
            <p>
              Clear and regenerate the distribution for{" "}
              {[...new Set(closed_halls.map((h) => `${h.date} ${h.period}`))].join(", ")}{" "}
              so no students are seated there, or{" "}
              <Link to="/halls" className="font-medium text-foreground">
                open the halls again
              </Link>
              .
            </p>
            <ul className="mt-2 space-y-1">
              {closed_halls.slice(0, SHOW).map((h) => (
                <li
                  key={`${h.date}-${h.period}-${h.hall_id}`}
                  className="font-mono text-[11px] text-muted-foreground"
                >
                  {h.date} {h.period} · {h.hall}
                </li>
              ))}
              {closed_halls.length > SHOW && (
                <li className="font-mono text-[11px] text-muted-foreground">
                  and {closed_halls.length - SHOW} more
                </li>
              )}
            </ul>
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
