import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CalendarPlus } from "lucide-react";
import { useTimetable, useTimetableDates } from "@/api/scheduling";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { JobProgressDialog } from "@/components/job-progress-dialog";
import { PageHeader } from "@/components/layout/page-header";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

const generateSchema = z
  .object({
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
  })
  .refine((v) => v.end_date >= v.start_date, {
    message: "End date must be on or after the start date",
    path: ["end_date"],
  });

type GenerateValues = z.infer<typeof generateSchema>;

export default function TimetablePage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const dates = useTimetableDates();
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");

  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const list = useTimetable({ date, period });

  const [genOpen, setGenOpen] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  return (
    <div className="space-y-10">
      <PageHeader
        section="Operations · Timetable"
        title="Timetable."
        description="Browse the generated exam timetable. Generate to (re-)build it."
        actions={
          isAdmin && (
            <Button onClick={() => setGenOpen(true)} size="lg" className="h-10">
              <CalendarPlus className="mr-1.5 h-4 w-4" strokeWidth={2.25} />
              Generate timetable
            </Button>
          )
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
          Filter
        </span>
        <Select
          value={date ?? ""}
          onValueChange={(v) => setDate(v ?? undefined)}
          disabled={!dates.data?.dates.length}
        >
          <SelectTrigger className="w-[200px]">
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
          <SelectTrigger className="w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="AM">AM</SelectItem>
            <SelectItem value="PM">PM</SelectItem>
          </SelectContent>
        </Select>
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
            <FormField
              control={form.control}
              name="start_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Start date</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
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
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
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
