import { useClasses } from "@/api/classes";
import {
  type ClassPeriodOverrides,
  type FacultyGroupMap,
  type GenerationConstraintsInput,
  type HallCourseTier,
  useConstraints,
  useUpdateConstraints,
} from "@/api/constraints";
import { useFaculties } from "@/api/faculties";
import { CourseLimitTiers, GroupOrder } from "./hall-rules";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";

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
  /** The hard fill cap as a whole percentage (the API stores 0-1). */
  hall_fill_pct: number;
  hall_course_limits: HallCourseTier[];
  hall_group_order: string[];
  seat_pattern: "checkerboard" | "sequential";
  excluded_weekdays: number[];
  remainder_merge_threshold: number;
  placement_success_threshold_pct: number;
};

export default function ConstraintsPage() {
  const constraints = useConstraints();
  const classesQ = useClasses({ all: true });
  const facultiesQ = useFaculties({ all: true });
  const update = useUpdateConstraints();

  const [form, setForm] = useState<FormState | null>(null);
  // Keyed by class NAME (case-preserving but matched insensitively).
  // "" means "auto" (= AM at runtime). "AM"/"PM" are explicit.
  const [periodByName, setPeriodByName] = useState<
    Record<string, "" | "AM" | "PM">
  >({});
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
    return [...set].sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true }),
    );
  }, [classesQ.data]);

  useEffect(() => {
    if (constraints.data && !form) {
      setForm({
        cbe_autosplit_threshold: constraints.data.cbe_autosplit_threshold,
        cbe_fullday_threshold: constraints.data.cbe_fullday_threshold,
        cbe_daily_cap_per_period: constraints.data.cbe_daily_cap_per_period,
        cbe_group_count: constraints.data.cbe_group_count,
        hall_fill_pct: Math.round(Number(constraints.data.pbe_hall_utilization) * 100),
        hall_course_limits: constraints.data.hall_course_limits,
        hall_group_order: constraints.data.hall_group_order,
        seat_pattern: constraints.data.seat_pattern ?? "checkerboard",
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
    () => uniqueClassNames.filter((n) => (periodByName[n] ?? "") === "").length,
    [uniqueClassNames, periodByName],
  );

  if (constraints.isLoading || !form) {
    return (
      <div className="space-y-10">
        <PageHeader
          section="Admin · Constraints"
          title="Constraints"
          description="Set the rules Ordo follows when it builds the timetable, splits classes across halls and seats students."
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

    if (form.hall_fill_pct < 1 || form.hall_fill_pct > 100) {
      setTopError("Maximum hall fill must be between 1% and 100%.");
      return;
    }

    const { hall_fill_pct, ...rest } = form;
    const payload: GenerationConstraintsInput = {
      ...rest,
      pbe_hall_utilization: (hall_fill_pct / 100).toFixed(2),
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
        title="Constraints"
        description="Set the rules Ordo follows when it builds the timetable, splits classes across halls and seats students. Save this page at least once before you generate anything."
      />

      {initialized ? (
        <Alert>
          <CheckCircle2 className="size-4" />
          <AlertTitle>Rules saved</AlertTitle>
          <AlertDescription>
            Last saved {configuredAt}
            {constraints.data?.configured_by_email
              ? ` by ${constraints.data.configured_by_email}`
              : ""}
            . You're ready to generate.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Rules not saved yet</AlertTitle>
          <AlertDescription>
            Save this page once to start generating the timetable, hall distribution and seating.
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
            Which days to skip, how big CBE exams are handled, and how paper exam seats are laid out.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <FieldLabel
              label="Excluded weekdays"
              hint="No exams are scheduled on the days you select."
            />
            <div className="flex flex-wrap gap-2">
              {WEEKDAYS.map((d) => {
                const checked = form.excluded_weekdays.includes(d.value);
                return (
                  <ToggleButton
                    key={d.value}
                    pressed={checked}
                    onClick={() => toggleWeekday(d.value)}
                  >
                    {d.label}
                  </ToggleButton>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <NumberField
              label="CBE auto-split threshold"
              hint="CBE courses with more students than this are split into sections by faculty. Set up the groups further down."
              value={form.cbe_autosplit_threshold}
              onChange={(v) => set("cbe_autosplit_threshold", v)}
            />
            <NumberField
              label="CBE full-day threshold"
              hint="CBE courses with more students than this take up both the morning and the afternoon."
              value={form.cbe_fullday_threshold}
              onChange={(v) => set("cbe_fullday_threshold", v)}
            />
            <NumberField
              label="CBE daily cap (per period)"
              hint="The most CBE students that can write in a single morning or afternoon."
              value={form.cbe_daily_cap_per_period}
              onChange={(v) => set("cbe_daily_cap_per_period", v)}
            />
          </div>
          <div className="space-y-2 max-w-md">
            <FieldLabel
              label="Seat pattern"
              hint="Checkerboard leaves an empty seat between students, so each hall holds about half its capacity. Sequential fills every seat and only stops students of the same course from sitting right next to each other. It roughly doubles capacity, so the exam period can be shorter."
            />
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  {
                    value: "checkerboard" as const,
                    title: "Checkerboard",
                    hint: "Empty seat between students, about half capacity",
                  },
                  {
                    value: "sequential" as const,
                    title: "Sequential",
                    hint: "Every seat used, same course never side by side",
                  },
                ]
              ).map((opt) => {
                const active = form.seat_pattern === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() => set("seat_pattern", opt.value)}
                    className={cn(
                      "border px-4 py-3 text-left transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
                      active
                        ? "border-primary bg-muted"
                        : "border-border hover:bg-muted",
                    )}
                  >
                    <div className="text-sm font-semibold">{opt.title}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {opt.hint}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Halls: fill cap, course limits and group order */}
      <Card>
        <CardHeader>
          <CardTitle>Halls</CardTitle>
          <CardDescription>
            How full a paper exam hall may get, how many courses it may hold,
            and which halls stand next to each other.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="max-w-xs">
            <NumberField
              label="Maximum hall fill (%)"
              hint="A hard rule: no hall is ever given more than this share of its seats for the seat pattern, by the timetable, distribution, seating, overflow or a manual seat. Default 90%."
              min={1}
              max={100}
              value={form.hall_fill_pct}
              onChange={(v) => set("hall_fill_pct", v)}
            />
          </div>
          <div>
            <FieldLabel
              label="Most courses per hall"
              hint="Stops a hall being crowded with many small courses. Distribution never opens a new course in a hall that has reached its limit. Seats are counted for the seat pattern."
            />
            <CourseLimitTiers
              value={form.hall_course_limits}
              onChange={(v) => set("hall_course_limits", v)}
            />
          </div>
          <div>
            <FieldLabel
              label="Hall group order"
              hint="Put groups that stand next to each other next to each other here. Halls are filled group by group in this order, biggest hall first inside a group, and a course that outgrows its group carries on into the next one. Change a hall's group on the Halls page."
            />
            <GroupOrder
              value={form.hall_group_order}
              onChange={(v) => set("hall_group_order", v)}
            />
          </div>
        </CardContent>
      </Card>

      {/* CBE faculty groups — drives how oversized CBE courses get split */}
      <Card>
        <CardHeader>
          <CardTitle>CBE faculty groups</CardTitle>
          <CardDescription>
            When a CBE course is too big for one sitting, Ordo splits it into sections by faculty. Choose how many groups to use and put each faculty in one. Every faculty needs a group before you can generate.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="max-w-full">
            <NumberField
              label="Number of groups"
              hint="At least 2. A large CBE course is split into up to this many sections (G1, G2 and so on)."
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
              No faculties yet. Add them on the Faculties page first.
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
                        <ToggleButton
                          key={g}
                          pressed={current === g}
                          onClick={() =>
                            setFacultyGroups((prev) => ({
                              ...prev,
                              [f.slug]: g,
                            }))
                          }
                        >
                          G{g}
                        </ToggleButton>
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
              {
                (facultiesQ.data?.results ?? []).filter(
                  (f) => !facultyGroups[f.slug],
                ).length
              }{" "}
              without a group yet. Every faculty needs one before you can generate.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Class period assignments — keyed by class name */}
      <Card>
        <CardHeader>
          <CardTitle>Class period assignments</CardTitle>
          <CardDescription>
            Choose whether each class writes in the morning or the afternoon. This goes by class name, so setting "Level 100" to AM applies to every department's Level 100. Anything left on Auto goes to the morning.{" "}
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
              No classes yet. Upload some classes first.
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
                        <ToggleButton
                          key={opt || "auto"}
                          pressed={current === opt}
                          onClick={() =>
                            setPeriodByName((p) => ({ ...p, [name]: opt }))
                          }
                        >
                          {opt === "" ? "Auto" : opt}
                        </ToggleButton>
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
            What to do with the few students left over when a class is split across halls.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4">
          <NumberField
            label="Remainder merge threshold"
            hint="If a split would leave fewer students than this, keep them together in one hall instead."
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
            When a seating run counts as a success. Students of the same course are never seated next to each other in any direction, and Ordo handles the rest.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <NumberField
            label="Placement success threshold (%)"
            hint="A seating run counts as a success when at least this percentage of students get a seat. If it falls short you still get the partial result."
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
      <FieldLabel label={label} hint={hint} />
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
    </div>
  );
}

/** Field label with its description tucked behind an info tooltip. */
function FieldLabel({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="mb-2 flex items-center gap-1.5">
      <Label>{label}</Label>
      {hint && (
        <Tooltip>
          <TooltipTrigger
            aria-label={`About ${label}`}
            className="inline-flex size-4 items-center justify-center text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:text-foreground focus-visible:ring-2 focus-visible:ring-ring/30"
          >
            <Info className="size-3.5" />
          </TooltipTrigger>
          <TooltipContent className="max-w-72 leading-relaxed">
            {hint}
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}

/** A pressable choice chip in the app's Button style. */
function ToggleButton({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      size="xs"
      variant={pressed ? "default" : "outline"}
      aria-pressed={pressed}
      onClick={onClick}
    >
      {children}
    </Button>
  );
}
