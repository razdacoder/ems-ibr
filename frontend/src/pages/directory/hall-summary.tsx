import { Fragment, useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DirectorySlot, HallRow } from "@/api/directory";
import { cn } from "@/lib/utils";
import { Eyebrow, SlotHeader, slotId } from "./shared";

export type HallView = "hall" | "class";

/**
 * Expand the backend's abbreviated range ("2430113585 - 3616") back into
 * full start and end matric numbers.
 */
function matricBounds(range: string): [string, string] | null {
  if (!range) return null;
  const [start, suffix] = range.split(" - ");
  if (!suffix) return [start, start];
  return [start, start.slice(0, start.length - suffix.length) + suffix];
}

/**
 * True when `matric` falls inside the row's block. Allocation cuts each class
 * into hall blocks in plain text matric order, so a text comparison between
 * same-length numbers is the same test the allocator used.
 */
function rowHoldsMatric(row: HallRow, matric: string) {
  const bounds = matricBounds(row.matric_range);
  if (!bounds) return false;
  const [start, end] = bounds;
  return start.length === matric.length && start <= matric && matric <= end;
}

/** A query of 6+ digits is treated as a matric lookup, anything else as text. */
export function isMatricQuery(q: string) {
  return /^\d{6,}$/.test(q.trim());
}

function filterRows(rows: HallRow[], query: string) {
  const q = query.trim();
  if (!q) return rows;
  if (isMatricQuery(q)) return rows.filter((r) => rowHoldsMatric(r, q));
  const needle = q.toLowerCase();
  return rows.filter(
    (r) =>
      r.hall.toLowerCase().includes(needle) ||
      r.class_name.toLowerCase().includes(needle),
  );
}

/** Stable key order: hall names read naturally ("Hall 2" before "Hall 10"). */
const naturalCompare = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
}).compare;

/** Rows bucketed by `key`, keeping each bucket's incoming order. */
function groupBy(rows: HallRow[], key: "hall" | "class_name") {
  const map = new Map<string, HallRow[]>();
  for (const r of rows) {
    const list = map.get(r[key]);
    if (list) list.push(r);
    else map.set(r[key], [r]);
  }
  return [...map.entries()];
}

const total = (rows: HallRow[]) => rows.reduce((n, r) => n + r.count, 0);

export function HallSummarySlot({
  slot,
  view,
  query,
}: {
  slot: DirectorySlot;
  view: HallView;
  query: string;
}) {
  const allRows = slot.rows ?? [];
  const rows = useMemo(() => filterRows(allRows, query), [allRows, query]);

  const stats = useMemo(
    () => [
      { label: "Halls", value: new Set(allRows.map((r) => r.hall)).size },
      {
        label: "Classes",
        value: new Set(allRows.map((r) => r.class_name)).size,
      },
      { label: "Students", value: total(allRows) },
    ],
    [allRows],
  );

  return (
    <section id={slotId(slot)} className="scroll-mt-6 space-y-5">
      <SlotHeader slot={slot} stats={stats} />
      {allRows.length === 0 ? (
        <p className="py-8 text-center font-serif italic text-muted-foreground">
          No seat allocation generated for this slot.
        </p>
      ) : rows.length === 0 ? (
        <p className="py-8 text-center font-serif italic text-muted-foreground">
          {isMatricQuery(query)
            ? `No hall in this slot holds ${query.trim()}.`
            : "Nothing in this slot matches your search."}
        </p>
      ) : view === "hall" ? (
        <ByHall rows={rows} highlight={isMatricQuery(query)} />
      ) : (
        <ByClass rows={rows} />
      )}
    </section>
  );
}

/** One card per hall: what an invigilator needs at the door. */
function ByHall({ rows, highlight }: { rows: HallRow[]; highlight: boolean }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      {groupBy(rows, "hall")
        .sort(([a], [b]) => naturalCompare(a, b))
        .map(([hall, list]) => (
        <Card
          key={hall}
          className={cn(highlight && "ring-2 ring-[color:var(--brand)]")}
        >
          <CardContent className="space-y-3 pt-5">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="font-serif text-[1.2rem] leading-tight tracking-tight">
                {hall}
              </h3>
              <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                <span className="text-foreground tabular-nums">
                  {total(list)}
                </span>{" "}
                students
              </span>
            </div>
            <ul className="divide-y divide-[color:var(--border)] border-t border-[color:var(--border)]">
              {list.map((r) => (
                <li
                  key={r.class_name}
                  className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 py-2.5"
                >
                  <span className="text-sm font-medium">{r.class_name}</span>
                  <span className="text-right text-sm tabular-nums">
                    {r.count}
                  </span>
                  <span className="col-span-2 font-mono text-[12px] tracking-wide text-muted-foreground">
                    {r.matric_range || "-"}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/** One block per class, listing each hall it is split across in range order. */
function ByClass({ rows }: { rows: HallRow[] }) {
  // Keep the backend's within-class order (ascending by range start).
  const groups = useMemo(() => groupBy(rows, "class_name"), [rows]);

  return (
    <Card>
      <CardContent className="pt-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[28%]">Class</TableHead>
              <TableHead>Hall</TableHead>
              <TableHead className="text-right">Students</TableHead>
              <TableHead>Matric numbers</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.map(([cls, list]) => (
              <Fragment key={cls}>
                {list.map((r, i) => (
                  <TableRow
                    key={`${cls}-${r.hall}`}
                    className={cn(i > 0 && "border-t-0")}
                  >
                    {i === 0 && (
                      <TableCell rowSpan={list.length} className="align-top">
                        <span className="font-medium">{cls}</span>
                        {list.length > 1 && (
                          <span className="mt-1 block">
                            <Eyebrow>
                              {list.length} halls · {total(list)} students
                            </Eyebrow>
                          </span>
                        )}
                      </TableCell>
                    )}
                    <TableCell>{r.hall}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.count}
                    </TableCell>
                    <TableCell className="font-mono text-[13px] tracking-wide">
                      {r.matric_range || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </Fragment>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
