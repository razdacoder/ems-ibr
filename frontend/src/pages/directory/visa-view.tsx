import { useMemo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import type { DirectorySlot, VisaGroup } from "@/api/directory";
import { SlotHeader, slotId } from "./shared";

export type VisaView = "departments" | "print";

function filterGroups(groups: VisaGroup[], query: string) {
  const needle = query.trim().toLowerCase();
  if (!needle) return groups;
  return groups
    .map((g) =>
      g.department.toLowerCase().includes(needle) ||
      g.department_name.toLowerCase().includes(needle)
        ? g
        : { ...g, codes: g.codes.filter((c) => c.toLowerCase().includes(needle)) },
    )
    .filter((g) => g.codes.length > 0);
}

export function VisaSlot({
  slot,
  view,
  query,
}: {
  slot: DirectorySlot;
  view: VisaView;
  query: string;
}) {
  const allGroups = slot.groups ?? [];
  const groups = useMemo(
    () => filterGroups(allGroups, query),
    [allGroups, query],
  );
  const stats = [
    { label: "Departments", value: allGroups.length },
    { label: "Classes", value: slot.codes?.length ?? 0 },
  ];

  return (
    <section id={slotId(slot)} className="scroll-mt-6 space-y-5">
      <SlotHeader slot={slot} stats={stats} />
      {allGroups.length === 0 ? (
        <p className="py-8 text-center font-serif italic text-muted-foreground">
          No classes scheduled for this slot.
        </p>
      ) : view === "print" ? (
        <PrintBlock codes={slot.codes ?? []} />
      ) : groups.length === 0 ? (
        <p className="py-8 text-center font-serif italic text-muted-foreground">
          Nothing in this slot matches your search.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {groups.map((g) => (
            <Card key={g.department}>
              <CardContent className="space-y-3 pt-5">
                <div className="flex items-baseline justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-serif text-[1.2rem] leading-tight tracking-tight">
                      {g.department}
                    </h3>
                    {g.department_name && (
                      <p className="truncate text-xs text-muted-foreground">
                        {g.department_name}
                      </p>
                    )}
                  </div>
                  <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                    <span className="text-foreground tabular-nums">
                      {g.codes.length}
                    </span>{" "}
                    {g.codes.length === 1 ? "class" : "classes"}
                  </span>
                </div>
                <ul className="flex flex-wrap gap-1.5 border-t border-[color:var(--border)] pt-3">
                  {g.codes.map((code) => (
                    <li
                      key={code}
                      className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[12px] font-semibold tracking-wide"
                    >
                      {code}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}

/** The single boxed block of codes, as the PDF and Word exports print it. */
function PrintBlock({ codes }: { codes: string[] }) {
  return (
    <div className="border-2 border-foreground bg-card px-6 py-5">
      <p className="text-center text-[15px] font-bold leading-8 tracking-wide">
        {codes.join(", ")}
      </p>
    </div>
  );
}
