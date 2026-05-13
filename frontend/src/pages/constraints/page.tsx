import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import {
  type ClassPeriodOverrides,
  type FacultyGroupMap,
  type GenerationConstraintsInput,
  useConstraints,
  useUpdateConstraints,
} from "@/api/constraints";
import { useClasses } from "@/api/classes";
import { useFaculties } from "@/api/faculties";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { PageHeader } from "@/components/layout/page-header";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { cn } from "@/lib/utils";

const WEEKDAYS = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
];

type FormState = {
  cbe_autosplit_threshold: number;
  cbe_fullday_threshold: number;
  cbe_daily_cap_per_period: number;
  cbe_group_count: number;
  pbe_hall_utilization: number;
  excluded_weekdays: number[];
  remainder_merge_threshold: number;
  placement_success_threshold_pct: number;
};

export default function ConstraintsPage() {
  const constraints = useConstraints();
  const classesQ = useClasses({ page: 1 });
  const facultiesQ = useFaculties({ page: 1 });
  const update = useUpdateConstraints();

  const [form, setForm] = useState<FormState | null>(null);
  // Keyed by class NAME (case-preserving but matched insensitively).
  // "" means "auto" (= AM at runtime). "AM"/"PM" are explicit.
  const [periodByName, setPeriodByName] = useState<Record<string, "" | "AM" | "PM">>({});
  // CBE faculty groups: faculty slug → group number (1..cbe_group_count).
  const [facultyGroups, setFacultyGroups] = useState<FacultyGroupMap>({});
  const [topError, setTopError] = useState<string | null>(null);

  // Distinct class names found in current classes list, sorted.
  const uniqueClassNames = useMemo<string[]>(() => {
    const set = new Set<string>();
    for (const c of classesQ.data?.results ?? []) {
      const name = (c.name ?? "").trim();
      if (name) set.add(name);
    }
    return [...set].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }, [classesQ.data]);

  useEffect(() => {
    if (constraints.data && !form) {
      setForm({
        cbe_autosplit_threshold: constraints.data.cbe_autosplit_threshold,
        cbe_fullday_threshold: constraints.data.cbe_fullday_threshold,
        cbe_daily_cap_per_period: constraints.data.cbe_daily_cap_per_period,
        cbe_group_count: constraints.data.cbe_group_count,
        pbe_hall_utilization: Number(constraints.data.pbe_hall_utilization),
        excluded_weekdays: [...constraints.data.excluded_weekdays],
        remainder_merge_threshold: constraints.data.remainder_merge_threshold,
        placement_success_threshold_pct:
          constraints.data.placement_success_threshold_pct,
      });
      setFacultyGroups({ ...(constraints.data.cbe_faculty_groups ?? {}) });
    }
  }, [constraints.data, form]);

  // Initialize/refresh the by-name editor from server overrides whenever
  // constraints land or the class set changes.
  useEffect(() => {
    if (!constraints.data) return;
    const serverMap = constraints.data.class_period_overrides ?? {};
    // Build a case-insensitive lookup of server keys.
    const ciLookup: Record<string, "AM" | "PM"> = {};
    for (const [k, v] of Object.entries(serverMap)) {
      ciLookup[k.trim().toLowerCase()] = v;
    }
    setPeriodByName((prev) => {
      const next: Record<string, "" | "AM" | "PM"> = { ...prev };
      for (const name of uniqueClassNames) {
        if (!(name in next)) {
          next[name] = ciLookup[name.toLowerCase()] ?? "";
        }
      }
      return next;
    });
  }, [constraints.data, uniqueClassNames]);

  const unassignedCount = useMemo(
    () =>
      uniqueClassNames.filter((n) => (periodByName[n] ?? "") === "").length,
    [uniqueClassNames, periodByName],
  );

  if (constraints.isLoading || !form) {
    return (
      <div className="space-y-10">
        <PageHeader
          section="Admin · Constraints"
          title="Constraints."
          description="Tune the timetable, distribution, and allocation algorithms."
        />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  const toggleWeekday = (day: number) => {
    set(
      "excluded_weekdays",
      form.excluded_weekdays.includes(day)
        ? form.excluded_weekdays.filter((d) => d !== day)
        : [...form.excluded_weekdays, day].sort(),
    );
  };

  const onSave = async () => {
    setTopError(null);
    if (form.excluded_weekdays.length === 0) {
      setTopError("Select at least one excluded weekday.");
      return;
    }

    const class_period_overrides: ClassPeriodOverrides = {};
    for (const name of uniqueClassNames) {
      const v = periodByName[name];
      if (v === "AM" || v === "PM") class_period_overrides[name] = v;
    }

    // Only persist faculty entries that have a valid group within the count.
    const cleanedFacultyGroups: FacultyGroupMap = {};
    for (const [slug, group] of Object.entries(facultyGroups)) {
      if (
        Number.isInteger(group) &&
        group >= 1 &&
        group <= form.cbe_group_count
      ) {
        cleanedFacultyGroups[slug] = group;
      }
    }

    const payload: GenerationConstraintsInput = {
      ...form,
      pbe_hall_utilization: form.pbe_hall_utilization.toFixed(2) as unknown as string,
      class_period_overrides,
      cbe_faculty_groups: cleanedFacultyGroups,
    };
    try {
      await update.mutateAsync(payload);
      toast({ title: "Constraints saved" });
    } catch (err) {
      const envelope = extractErrorEnvelope(err);
      setTopError(envelope.detail);
      toast({
        title: "Save failed",
        description: envelope.detail,
        variant: "destructive",
      });
    }
  };

  const initialized = !!constraints.data?.configured;
  const configuredAt = constraints.data?.configured_at
    ? new Date(constraints.data.configured_at).toLocaleString()
    : null;

  return (
    <div className="space-y-10">
      <PageHeader
        section="Admin · Constraints"
        title="Constraints."
        description="Tune algorithm thresholds for timetable, distribution, and allocation. Without saving here once, generation is blocked."
      />

      {initialized ? (
        <Alert>
          <CheckCircle2 className="size-4" />
          <AlertTitle>Initialized</AlertTitle>
          <AlertDescription>
            Last saved {configuredAt}
            {constraints.data?.configured_by_email
              ? ` by ${constraints.data.configured_by_email}`
              : ""}
            . Generation is unlocked.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Not initialized</AlertTitle>
          <AlertDescription>
            Save these constraints once to unlock timetable, distribution, and
            allocation generation.
          </AlertDescription>
        </Alert>
      )}

      {topError && (
        <Alert variant="destructive">
          <AlertDescription>{topError}</AlertDescription>
        </Alert>
      )}

      {/* Timetable */}
      <Card>
        <CardHeader>
          <CardTitle>Timetable</CardTitle>
          <CardDescription>
            Date selection, CBE thresholds, and PBE seat utilization.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <Label className="mb-2 block">Excluded weekdays</Label>
            <div className="flex flex-wrap gap-2">
              {WEEKDAYS.map((d) => {
                const checked = form.excluded_weekdays.includes(d.value);
                return (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => toggleWeekday(d.value)}
                    className={cn(
                      "rounded-md border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] transition-colors",
                      checked
                        ? "border-[color:var(--brand)] bg-[color:var(--brand-soft)] text-[color:var(--brand-strong)]"
                        : "border-[color:var(--border)] bg-card text-muted-foreground hover:border-[color:var(--brand)]/40",
                    )}
                  >
                    {d.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
              Selected days are skipped during scheduling.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <NumberField
              label="CBE auto-split threshold"
              hint="Courses exceeding this size are split into N faculty-keyed sections (see CBE faculty groups below)."
              value={form.cbe_autosplit_threshold}
              onChange={(v) => set("cbe_autosplit_threshold", v)}
            />
            <NumberField
              label="CBE full-day threshold"
              hint="Courses above this size occupy both AM and PM."
              value={form.cbe_fullday_threshold}
              onChange={(v) => set("cbe_fullday_threshold", v)}
            />
            <NumberField
              label="CBE daily cap (per period)"
              hint="Cap on total CBE students scheduled in one period of one day."
              value={form.cbe_daily_cap_per_period}
              onChange={(v) => set("cbe_daily_cap_per_period", v)}
            />
            <NumberField
              label="PBE hall utilization"
              hint="Fraction of a hall's seats used for PBE (0–1)."
              step={0.05}
              min={0.01}
              max={1}
              value={form.pbe_hall_utilization}
              onChange={(v) => set("pbe_hall_utilization", v)}
            />
          </div>
        </CardContent>
      </Card>

      {/* CBE faculty groups — drives how oversized CBE courses get split */}
      <Card>
        <CardHeader>
          <CardTitle>CBE faculty groups</CardTitle>
          <CardDescription>
            When a CBE course exceeds the auto-split threshold, classes are
            bucketed into <span className="font-mono">N</span> sections by
            faculty. Pick the group count and assign each faculty to a group.
            Every faculty must be mapped or generation is blocked.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="max-w-xs">
            <NumberField
              label="Number of groups"
              hint="At least 2. Each large CBE course will produce up to this many sections (G1, G2, …)."
              value={form.cbe_group_count}
              onChange={(v) => {
                set("cbe_group_count", v);
                // Clamp any out-of-range existing faculty entries
                setFacultyGroups((prev) => {
                  const next: FacultyGroupMap = {};
                  for (const [slug, g] of Object.entries(prev)) {
                    if (g <= v) next[slug] = g;
                  }
                  return next;
                });
              }}
              min={2}
              max={10}
            />
          </div>

          {facultiesQ.isLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : (facultiesQ.data?.results ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No faculties yet — add faculties in Admin → Faculties first.
            </p>
          ) : (
            <div className="rounded-md border border-[color:var(--border)] divide-y divide-[color:var(--border)]/60">
              {facultiesQ.data!.results.map((f) => {
                const current = facultyGroups[f.slug];
                return (
                  <div
                    key={f.id}
                    className="flex items-center gap-4 px-4 py-2.5"
                  >
                    <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[11px] tracking-wide">
                      {f.slug}
                    </kbd>
                    <span className="flex-1 font-serif text-[0.95rem]">
                      {f.name}
                    </span>
                    <div className="flex flex-wrap justify-end gap-1">
                      {Array.from(
                        { length: form.cbe_group_count },
                        (_, i) => i + 1,
                      ).map((g) => (
                        <button
                          key={g}
                          type="button"
                          onClick={() =>
                            setFacultyGroups((prev) => ({
                              ...prev,
                              [f.slug]: g,
                            }))
                          }
                          className={cn(
                            "rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
                            current === g
                              ? "border-[color:var(--brand)] bg-[color:var(--brand-soft)] text-[color:var(--brand-strong)]"
                              : "border-[color:var(--border)] bg-card text-muted-foreground hover:border-[color:var(--brand)]/40",
                          )}
                        >
                          G{g}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {(facultiesQ.data?.results ?? []).some(
            (f) => !facultyGroups[f.slug],
          ) && (
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--accent-red-fg)]">
              {(facultiesQ.data?.results ?? []).filter(
                (f) => !facultyGroups[f.slug],
              ).length}{" "}
              faculty unmapped — generation is blocked until all are set.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Class period assignments — keyed by class name */}
      <Card>
        <CardHeader>
          <CardTitle>Class period assignments</CardTitle>
          <CardDescription>
            Assignment is by class name only — setting "Level 100" to AM
            applies to every department that has a class called "Level 100".
            Names left as Auto default to AM.{" "}
            <span className="text-foreground">
              {unassignedCount} unassigned
            </span>{" "}
            of {uniqueClassNames.length} unique names.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {classesQ.isLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : uniqueClassNames.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No classes yet — upload classes first.
            </p>
          ) : (
            <div className="max-h-[420px] overflow-y-auto rounded-md border border-[color:var(--border)] divide-y divide-[color:var(--border)]/60">
              {uniqueClassNames.map((name) => {
                const current = periodByName[name] ?? "";
                return (
                  <div
                    key={name}
                    className="flex items-center gap-4 px-4 py-2.5"
                  >
                    <span className="flex-1 font-serif text-[0.95rem]">
                      {name}
                    </span>
                    <div className="flex gap-1">
                      {(["AM", "PM", ""] as const).map((opt) => (
                        <button
                          key={opt || "auto"}
                          type="button"
                          onClick={() =>
                            setPeriodByName((p) => ({ ...p, [name]: opt }))
                          }
                          className={cn(
                            "rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors",
                            current === opt
                              ? "border-[color:var(--brand)] bg-[color:var(--brand-soft)] text-[color:var(--brand-strong)]"
                              : "border-[color:var(--border)] bg-card text-muted-foreground hover:border-[color:var(--brand)]/40",
                          )}
                        >
                          {opt === "" ? "Auto" : opt}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Distribution</CardTitle>
          <CardDescription>
            How leftover students are merged when distributing classes into halls.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <NumberField
            label="Remainder merge threshold"
            hint="If fewer than this many students remain after a split, place them all in the same hall instead of splitting again."
            value={form.remainder_merge_threshold}
            onChange={(v) => set("remainder_merge_threshold", v)}
          />
        </CardContent>
      </Card>

      {/* Allocation */}
      <Card>
        <CardHeader>
          <CardTitle>Allocation</CardTitle>
          <CardDescription>
            Result threshold for the seat-allocation pass. Anti-cheating
            adjacency is fixed at 8-direction; placement attempts and pattern
            order are managed internally.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <NumberField
            label="Placement success threshold (%)"
            hint="Reported as a success when this fraction of students is placed. Partial results are still returned below the threshold."
            value={form.placement_success_threshold_pct}
            onChange={(v) => set("placement_success_threshold_pct", v)}
            min={0}
            max={100}
          />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={onSave} disabled={update.isPending} size="lg">
          {update.isPending ? "Saving…" : "Save constraints"}
        </Button>
      </div>
    </div>
  );
}

function NumberField({
  label,
  hint,
  value,
  onChange,
  step,
  min,
  max,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
}) {
  return (
    <div>
      <Label className="mb-2 block">{label}</Label>
      <Input
        type="number"
        value={value}
        step={step ?? 1}
        min={min}
        max={max}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (!Number.isNaN(v)) onChange(v);
        }}
      />
      {hint && (
        <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          {hint}
        </p>
      )}
    </div>
  );
}
