import { useMemo } from "react";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import type { HallCourseTier } from "@/api/constraints";
import { useHalls } from "@/api/halls";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Course limits by hall size. The last tier has no seat limit and covers
 * every hall bigger than the others. Mirrors ems/halls.py.
 */
export function CourseLimitTiers({
  value,
  onChange,
}: {
  value: HallCourseTier[];
  onChange: (next: HallCourseTier[]) => void;
}) {
  const bounded = value.filter((t) => t.max_seats !== null);
  const open = value.find((t) => t.max_seats === null) ?? { max_seats: null, courses: 8 };

  const setBounded = (next: HallCourseTier[]) => onChange([...next, open]);
  const update = (i: number, patch: Partial<HallCourseTier>) =>
    setBounded(bounded.map((t, j) => (j === i ? { ...t, ...patch } : t)));

  return (
    <div className="space-y-2">
      <div className="divide-y divide-border border border-border">
        {bounded.map((tier, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
            <span className="text-muted-foreground">Halls up to</span>
            <Input
              type="number"
              min={1}
              value={tier.max_seats ?? ""}
              onChange={(e) => update(i, { max_seats: Math.max(1, Number(e.target.value) || 1) })}
              className="h-8 w-20 font-mono"
              aria-label="Seat limit of this tier"
            />
            <span className="text-muted-foreground">seats hold at most</span>
            <Input
              type="number"
              min={1}
              value={tier.courses}
              onChange={(e) => update(i, { courses: Math.max(1, Number(e.target.value) || 1) })}
              className="h-8 w-16 font-mono"
              aria-label="Courses allowed in this tier"
            />
            <span className="text-muted-foreground">courses</span>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              className="ml-auto"
              onClick={() => setBounded(bounded.filter((_, j) => j !== i))}
              aria-label="Remove this tier"
            >
              <Trash2 />
            </Button>
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
          <span className="text-muted-foreground">
            {bounded.length ? "Bigger halls hold at most" : "Every hall holds at most"}
          </span>
          <Input
            type="number"
            min={1}
            value={open.courses}
            onChange={(e) =>
              onChange([...bounded, { max_seats: null, courses: Math.max(1, Number(e.target.value) || 1) }])
            }
            className="h-8 w-16 font-mono"
            aria-label="Courses allowed in the biggest halls"
          />
          <span className="text-muted-foreground">courses</span>
        </div>
      </div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        onClick={() => {
          const last = Math.max(0, ...bounded.map((t) => t.max_seats ?? 0));
          setBounded([...bounded, { max_seats: last + 100, courses: open.courses }]);
        }}
      >
        <Plus data-icon="inline-start" /> Add size tier
      </Button>
      <p className="text-xs text-muted-foreground">
        Tiers are sorted by seats when saved. Under the strict rule one course
        uses at most a quarter of a hall, so a limit below 4 leaves seats empty.
      </p>
    </div>
  );
}

/**
 * Hall groups in the order they stand on the ground. Groups come from the
 * halls themselves; ones missing from the saved order are listed after it,
 * biggest hall first, the order distribution already uses for them.
 */
export function GroupOrder({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  const halls = useHalls({ all: true });

  const groups = useMemo(() => {
    const info = new Map<string, { halls: string[]; biggest: number }>();
    for (const h of halls.data?.results ?? []) {
      const entry = info.get(h.group) ?? { halls: [], biggest: 0 };
      entry.halls.push(h.name);
      entry.biggest = Math.max(entry.biggest, h.seat_count);
      info.set(h.group, entry);
    }
    return info;
  }, [halls.data]);

  // The saved order first, then groups it does not mention yet.
  const ordered = useMemo(() => {
    const known = value.filter((g) => groups.has(g));
    const rest = [...groups.keys()]
      .filter((g) => !known.includes(g))
      .sort((a, b) => groups.get(b)!.biggest - groups.get(a)!.biggest || a.localeCompare(b));
    return [...known, ...rest];
  }, [value, groups]);

  if (halls.isLoading) return <Skeleton className="h-40 w-full" />;
  if (!ordered.length) {
    return <p className="text-sm text-muted-foreground">No halls yet.</p>;
  }

  const move = (i: number, by: number) => {
    const next = [...ordered];
    [next[i], next[i + by]] = [next[i + by], next[i]];
    onChange(next);
  };

  return (
    <div className="max-h-[420px] divide-y divide-border overflow-y-auto border border-border">
      {ordered.map((group, i) => {
        const entry = groups.get(group)!;
        return (
          <div key={group} className="flex items-center gap-3 px-3 py-2">
            <span className="w-6 text-right font-mono text-[11px] text-muted-foreground">
              {i + 1}
            </span>
            <kbd className="min-w-12 rounded-[4px] border border-border bg-muted px-2 py-0.5 text-center font-mono text-[11px] tracking-wide">
              {group}
            </kbd>
            <span className="flex-1 truncate text-xs text-muted-foreground">
              {entry.halls.length} hall{entry.halls.length === 1 ? "" : "s"} ·{" "}
              {entry.halls.sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).join(", ")}
            </span>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              disabled={i === 0}
              onClick={() => move(i, -1)}
              aria-label={`Move ${group} up`}
            >
              <ArrowUp />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              disabled={i === ordered.length - 1}
              onClick={() => move(i, 1)}
              aria-label={`Move ${group} down`}
            >
              <ArrowDown />
            </Button>
          </div>
        );
      })}
    </div>
  );
}
