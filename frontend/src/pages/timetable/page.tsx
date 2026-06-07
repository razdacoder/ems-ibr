import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  CalendarPlus,
  CalendarDays,
  LayoutList,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  useTimetable,
  useTimetableDates,
  useTimetableEstimate,
  type TimetableEntry,
} from "@/api/scheduling";
import { useGenerateTimetable } from "@/api/jobs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { JobProgressDialog } from "@/components/job-progress-dialog";
import { PageHeader } from "@/components/layout/page-header";
import { isSuperAdmin, useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { cn } from "@/lib/utils";

const todayIso = () => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

const pad2 = (n: number) => String(n).padStart(2, "0");
const isoOf = (d: Date) =>
  `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
const parseIso = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const generateSchema = z
  .object({
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
  })
  .superRefine((v, ctx) => {
    const today = todayIso();
    if (v.start_date && v.start_date <= today) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["start_date"],
        message: "Start date must be in the future",
      });
    }
    if (v.end_date && v.end_date <= today) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["end_date"],
        message: "End date must be in the future",
      });
    }
    if (v.start_date && v.end_date && v.end_date < v.start_date) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["end_date"],
        message: "End date must be on or after the start date",
      });
    }
  });

type GenerateValues = z.infer<typeof generateSchema>;

export default function TimetablePage() {
  const { user } = useAuth();
  // Only super admins may trigger timetable generation.
  const isAdmin = isSuperAdmin(user);

  const dates = useTimetableDates();
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");

  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const list = useTimetable({ date, period });

  const [view, setView] = useState<"list" | "calendar">("list");
  const [calPeriod, setCalPeriod] = useState<"ALL" | "AM" | "PM">("ALL");
  // Calendar view needs the whole (department-scoped) timetable at once so it
  // can show per-day counts and a day's exams without a request per click.
  const all = useTimetable({}, { enabled: view === "calendar" });
  const [genOpen, setGenOpen] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  return (
    <div className="space-y-10">
      <PageHeader
        section="Operations · Timetable"
        title="Timetable."
        description={
          isAdmin
            ? "Browse the generated exam timetable. Generate to (re-)build it."
            : "Browse your department's exam timetable."
        }
        actions={
          isAdmin && (
            <Button onClick={() => setGenOpen(true)} size="lg" className="h-10">
              <CalendarPlus className="mr-1.5 h-4 w-4" strokeWidth={2.25} />
              Generate timetable
            </Button>
          )
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <Tabs
          value={view}
          onValueChange={(v) => setView(v as "list" | "calendar")}
        >
          <TabsList>
            <TabsTrigger value="list">
              <LayoutList className="h-4 w-4" />
              List
            </TabsTrigger>
            <TabsTrigger value="calendar">
              <CalendarDays className="h-4 w-4" />
              Calendar
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {view === "list" ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              Filter
            </span>
            <Select
              value={date ?? ""}
              onValueChange={(v) => setDate(v ?? undefined)}
              disabled={!dates.data?.dates.length}
            >
              <SelectTrigger>
                <SelectValue placeholder="Pick a date" />
              </SelectTrigger>
              <SelectContent>
                {dates.data?.dates.map((d) => (
                  <SelectItem key={d} value={d}>
                    {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={period}
              onValueChange={(v) => setPeriod(v as "AM" | "PM")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AM">AM</SelectItem>
                <SelectItem value="PM">PM</SelectItem>
              </SelectContent>
            </Select>
            {(() => {
              const ds = dates.data?.dates ?? [];
              if (!ds.length) return null;
              const days = ds.length;
              const weeks = Math.round((days / 7) * 10) / 10;
              return (
                <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  {days} day{days === 1 ? "" : "s"} · {weeks} week
                  {weeks === 1 ? "" : "s"} available
                </span>
              );
            })()}
          </div>

          <Card>
            <CardHeader className="border-b border-[color:var(--border)]">
              <CardTitle className="font-serif text-[1.5rem] tracking-tight">
                {date ? `${date} · ${period}` : "Pick a date"}
              </CardTitle>
              <CardDescription className="font-mono text-[10px] uppercase tracking-[0.14em]">
                {list.data?.results.length ?? 0} exams scheduled
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {list.error ? (
                <Alert variant="destructive">
                  <AlertDescription>
                    {extractErrorEnvelope(list.error).detail}
                  </AlertDescription>
                </Alert>
              ) : null}
              {list.isLoading ? (
                <Skeleton className="h-40" />
              ) : list.data?.generated ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[110px]">Dept</TableHead>
                      <TableHead className="w-[200px]">Class</TableHead>
                      <TableHead className="w-[120px]">Course code</TableHead>
                      <TableHead>Course title</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {list.data.results.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="py-12 text-center font-serif italic text-muted-foreground"
                        >
                          No exams for this slot.
                        </TableCell>
                      </TableRow>
                    ) : (
                      list.data.results.map((row) => (
                        <TableRow key={row.id}>
                          <TableCell>
                            <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-1.5 py-0.5 font-mono text-[10px] tracking-wide">
                              {row.class.department.slug}
                            </kbd>
                          </TableCell>
                          <TableCell className="font-serif text-[1rem] tracking-[-0.005em]">
                            {row.class.name}
                          </TableCell>
                          <TableCell>
                            <span className="font-mono text-[12px] tracking-wide text-foreground">
                              {row.course.code}
                            </span>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {row.course.name}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground">
                  No timetable has been generated yet.
                </p>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <TimetableCalendar
          entries={all.data?.results ?? []}
          generated={all.data?.generated ?? false}
          isLoading={all.isLoading}
          error={all.error ? extractErrorEnvelope(all.error).detail : null}
          selected={date}
          onSelect={setDate}
          period={calPeriod}
          onPeriodChange={setCalPeriod}
        />
      )}

      <GenerateTimetableDialog
        open={genOpen}
        onOpenChange={setGenOpen}
        onLaunched={(id) => {
          setJobId(id);
          setProgressOpen(true);
          setGenOpen(false);
        }}
      />
      <JobProgressDialog
        jobId={jobId}
        title="Timetable generation"
        open={progressOpen}
        onOpenChange={setProgressOpen}
        onSuccess={() => {
          dates.refetch();
          list.refetch();
          all.refetch();
        }}
      />
    </div>
  );
}

function GenerateTimetableDialog({
  open,
  onOpenChange,
  onLaunched,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onLaunched: (jobId: string) => void;
}) {
  const generate = useGenerateTimetable();
  const estimate = useTimetableEstimate(open);
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<GenerateValues>({
    resolver: zodResolver(generateSchema),
    defaultValues: { start_date: "", end_date: "" },
  });

  useEffect(() => {
    if (open) {
      form.reset({ start_date: "", end_date: "" });
      setTopError(null);
    }
  }, [open, form]);

  const minStart = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  })();

  const watchedStart = form.watch("start_date");
  const watchedEnd = form.watch("end_date");

  const excludedSet = new Set(estimate.data?.excluded_weekdays ?? [6]);
  // JS getDay(): Sun=0..Sat=6 → Python weekday(): Mon=0..Sun=6
  const toPyWeekday = (jsDay: number) => (jsDay + 6) % 7;
  const validExamDaysInWindow = (() => {
    if (!watchedStart || !watchedEnd || watchedEnd < watchedStart) return 0;
    let count = 0;
    const cursor = new Date(watchedStart);
    const end = new Date(watchedEnd);
    while (cursor <= end) {
      if (!excludedSet.has(toPyWeekday(cursor.getDay()))) count++;
      cursor.setDate(cursor.getDate() + 1);
    }
    return count;
  })();

  const spanLabel = (() => {
    if (!watchedStart || !watchedEnd || watchedEnd < watchedStart) return null;
    const ms = new Date(watchedEnd).getTime() - new Date(watchedStart).getTime();
    const calendarDays = Math.round(ms / 86_400_000) + 1;
    const weeks = Math.round((calendarDays / 7) * 10) / 10;
    return `${calendarDays} calendar day${calendarDays === 1 ? "" : "s"} · ${validExamDaysInWindow} exam day${validExamDaysInWindow === 1 ? "" : "s"} · ${weeks} week${weeks === 1 ? "" : "s"}`;
  })();

  const windowTooShort =
    !!estimate.data &&
    validExamDaysInWindow > 0 &&
    validExamDaysInWindow < estimate.data.min_exam_days;

  const onSubmit = async (v: GenerateValues) => {
    setTopError(null);
    try {
      const out = await generate.mutateAsync(v);
      toast({ title: "Generation started" });
      onLaunched(out.job_id);
    } catch (err) {
      setTopError(extractErrorEnvelope(err).detail);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate timetable</DialogTitle>
          <DialogDescription>
            Pick the exam window. Sundays are excluded automatically.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3">
            {topError && (
              <Alert variant="destructive">
                <AlertDescription>{topError}</AlertDescription>
              </Alert>
            )}
            {estimate.data && estimate.data.class_count > 0 && (
              <div className="rounded-md border border-[color:var(--border)] bg-[color:var(--muted)]/40 p-3 text-[12px]">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Recommended window
                </p>
                <p className="mt-1 font-serif text-[1.0625rem] leading-snug tracking-[-0.005em]">
                  {estimate.data.recommended_exam_days} exam day
                  {estimate.data.recommended_exam_days === 1 ? "" : "s"}
                  {" · "}
                  {estimate.data.min_calendar_days} calendar day
                  {estimate.data.min_calendar_days === 1 ? "" : "s"}
                  {" ("}
                  {estimate.data.min_calendar_weeks} week
                  {estimate.data.min_calendar_weeks === 1 ? "" : "s"}
                  {")"}
                </p>
                <p className="mt-1 text-muted-foreground">
                  Minimum {estimate.data.min_exam_days} exam day
                  {estimate.data.min_exam_days === 1 ? "" : "s"}.{" "}
                  {estimate.data.bottleneck === "seat_throughput" ? (
                    <>
                      Bottleneck: hall seat throughput — AM demand{" "}
                      {estimate.data.am_seat_demand.toLocaleString()}, PM{" "}
                      {estimate.data.pm_seat_demand.toLocaleString()} vs{" "}
                      {estimate.data.seats_per_period.toLocaleString()} seats
                      per period (needs{" "}
                      {estimate.data.throughput_min_days} days). Per-class
                      limit only needs {estimate.data.per_class_min_days}.
                    </>
                  ) : (
                    <>
                      Bottleneck: the busiest class has AM{" "}
                      {estimate.data.worst_class_am} · PM{" "}
                      {estimate.data.worst_class_pm} exams across{" "}
                      {estimate.data.class_count} classes. Choose at least this
                      many days for maximum efficiency.
                    </>
                  )}
                </p>
              </div>
            )}
            <FormField
              control={form.control}
              name="start_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Start date</FormLabel>
                  <FormControl>
                    <Input type="date" min={minStart} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="end_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>End date</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      min={form.watch("start_date") || minStart}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {spanLabel && (
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                Window: {spanLabel}
              </p>
            )}
            {windowTooShort && estimate.data && (
              <Alert variant="destructive">
                <AlertDescription>
                  This window has only {validExamDaysInWindow} valid exam day
                  {validExamDaysInWindow === 1 ? "" : "s"}, but the busiest
                  class needs {estimate.data.min_exam_days}. Extend the end
                  date for a clean schedule.
                </AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Queueing…" : "Start generation"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

function TimetableCalendar({
  entries,
  generated,
  isLoading,
  error,
  selected,
  onSelect,
  period,
  onPeriodChange,
}: {
  entries: TimetableEntry[];
  generated: boolean;
  isLoading: boolean;
  error: string | null;
  selected?: string;
  onSelect: (iso: string) => void;
  period: "ALL" | "AM" | "PM";
  onPeriodChange: (p: "ALL" | "AM" | "PM") => void;
}) {
  // Group exams by date once for O(1) per-day lookups, honouring the period
  // filter so the grid counts and the modal only show the chosen slot.
  const byDate = useMemo(() => {
    const map = new Map<string, TimetableEntry[]>();
    for (const e of entries) {
      if (period !== "ALL" && e.period !== period) continue;
      const arr = map.get(e.date);
      if (arr) arr.push(e);
      else map.set(e.date, [e]);
    }
    return map;
  }, [entries, period]);

  const examDates = useMemo(() => [...byDate.keys()].sort(), [byDate]);

  // Default the selection to the first exam day so the side panel isn't empty
  // on open and the date filter stays in sync.
  useEffect(() => {
    if (!selected && examDates.length) onSelect(examDates[0]);
  }, [selected, examDates, onSelect]);

  const [cursor, setCursor] = useState(() => {
    const base = selected ?? examDates[0];
    const d = base ? parseIso(base) : new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  // When data arrives and nothing is picked yet, jump to the first exam month.
  useEffect(() => {
    if (selected || !examDates.length) return;
    const d = parseIso(examDates[0]);
    setCursor(new Date(d.getFullYear(), d.getMonth(), 1));
  }, [examDates, selected]);

  // Follow the selected date into its month when changed elsewhere.
  useEffect(() => {
    if (!selected) return;
    const d = parseIso(selected);
    setCursor((cur) =>
      cur.getFullYear() === d.getFullYear() && cur.getMonth() === d.getMonth()
        ? cur
        : new Date(d.getFullYear(), d.getMonth(), 1),
    );
  }, [selected]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const todayKey = isoOf(new Date());

  const cells = useMemo(() => {
    const firstWeekday = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const out: Array<{ day: number; iso: string } | null> = [];
    for (let i = 0; i < firstWeekday; i++) out.push(null);
    for (let d = 1; d <= daysInMonth; d++) {
      out.push({ day: d, iso: isoOf(new Date(year, month, d)) });
    }
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [year, month]);

  const examDaysThisMonth = cells.filter((c) => c && byDate.has(c.iso)).length;

  const selectedExams = selected ? byDate.get(selected) ?? [] : [];
  const byPeriod = (p: "AM" | "PM") =>
    selectedExams
      .filter((e) => e.period === p)
      .sort((a, b) => a.course.code.localeCompare(b.course.code));

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }
  if (isLoading) {
    return <Skeleton className="h-[28rem]" />;
  }
  if (!generated) {
    return (
      <Card>
        <CardContent className="py-16 text-center text-muted-foreground">
          No timetable has been generated yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 border-b border-[color:var(--border)]">
          <div>
            <CardTitle className="font-serif text-[1.5rem] tracking-tight">
              {MONTHS[month]} {year}
            </CardTitle>
            <CardDescription className="font-mono text-[10px] uppercase tracking-[0.14em]">
              {examDaysThisMonth} exam day{examDaysThisMonth === 1 ? "" : "s"}{" "}
              this month
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={period}
              onValueChange={(v) =>
                onPeriodChange(v as "ALL" | "AM" | "PM")
              }
            >
              <SelectTrigger size="sm" className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All periods</SelectItem>
                <SelectItem value="AM">AM only</SelectItem>
                <SelectItem value="PM">PM only</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                aria-label="Previous month"
                onClick={() => setCursor(new Date(year, month - 1, 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon-sm"
                aria-label="Next month"
                onClick={() => setCursor(new Date(year, month + 1, 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-7 gap-1">
            {WEEKDAYS.map((w) => (
              <div
                key={w}
                className="pb-2 text-center font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground"
              >
                {w}
              </div>
            ))}
            {cells.map((c, i) => {
              if (!c) return <div key={`pad-${i}`} aria-hidden />;
              const count = byDate.get(c.iso)?.length ?? 0;
              const isExam = count > 0;
              const isSelected = c.iso === selected;
              const isToday = c.iso === todayKey;
              return (
                <button
                  key={c.iso}
                  type="button"
                  disabled={!isExam}
                  onClick={() => onSelect(c.iso)}
                  aria-pressed={isSelected}
                  title={
                    isExam ? `${count} exam${count === 1 ? "" : "s"}` : undefined
                  }
                  className={cn(
                    "relative flex aspect-square flex-col items-center justify-center gap-0.5 rounded-md border text-sm transition-colors",
                    isSelected
                      ? "border-transparent bg-foreground text-background"
                      : isExam
                        ? "cursor-pointer border-[color:var(--border)] bg-[color:var(--muted)] font-medium hover:bg-accent hover:text-accent-foreground"
                        : "border-transparent text-muted-foreground/40",
                    isToday && !isSelected && "ring-1 ring-ring",
                  )}
                >
                  <span>{c.day}</span>
                  {isExam && (
                    <span
                      className={cn(
                        "rounded-full px-1.5 font-mono text-[10px] leading-tight",
                        isSelected
                          ? "bg-background/20 text-background"
                          : "bg-foreground/10 text-foreground",
                      )}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-[color:var(--border)]">
          <CardTitle className="font-serif text-[1.25rem] tracking-tight">
            {selected ?? "Pick a day"}
          </CardTitle>
          <CardDescription className="font-mono text-[10px] uppercase tracking-[0.14em]">
            {selectedExams.length} exam{selectedExams.length === 1 ? "" : "s"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 pt-5">
          {selectedExams.length === 0 ? (
            <p className="py-8 text-center font-serif italic text-muted-foreground">
              No exams on this day.
            </p>
          ) : (
            (["AM", "PM"] as const).map((label) => {
              const items = byPeriod(label);
              if (items.length === 0) return null;
              return (
                <div key={label} className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                    {label} · {items.length}
                  </p>
                  <ul className="space-y-1.5">
                    {items.map((e) => (
                      <li
                        key={e.id}
                        className="flex items-baseline gap-2 border-b border-[color:var(--border)] pb-1.5 last:border-0"
                      >
                        <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-1.5 py-0.5 font-mono text-[10px] tracking-wide">
                          {e.class.department.slug}
                        </kbd>
                        <span className="font-mono text-[12px]">
                          {e.course.code}
                        </span>
                        <span
                          className="flex-1 truncate text-muted-foreground"
                          title={e.course.name}
                        >
                          {e.course.name}
                        </span>
                        <span className="font-serif text-[0.9rem]">
                          {e.class.name}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </div>
  );
}
