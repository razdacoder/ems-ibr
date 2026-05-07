import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import {
  useDistribution,
  useDistributionStatistics,
} from "@/api/scheduling";
import { useTimetableDates } from "@/api/scheduling";
import { useGenerateDistribution } from "@/api/jobs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

export default function DistributionPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const dates = useTimetableDates();
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");
  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const list = useDistribution({ date, period });
  const stats = useDistributionStatistics(date, period);
  const generate = useGenerateDistribution();
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  const onGenerate = async () => {
    if (!date || !period) return;
    try {
      const out = await generate.mutateAsync({ date, period });
      setJobId(out.job_id);
      setProgressOpen(true);
      toast({ title: "Distribution generation started" });
    } catch (err) {
      toast({
        title: "Could not start",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-10">
      <PageHeader
        section="Operations · Distribution"
        title="Distribution."
        description="Capacity-aware hall-to-class assignments for each exam slot. Large classes split across halls; small ones share."
        actions={
          isAdmin && (
            <Button
              onClick={onGenerate}
              disabled={!date || generate.isPending}
              size="lg"
              className="h-10"
            >
              <Layers className="mr-1.5 h-4 w-4" strokeWidth={2.25} />
              Generate distribution
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
      </div>

      {stats.data && (
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[12px] border border-[color:var(--border)] bg-[color:var(--border)] sm:grid-cols-4">
          {[
            { k: "Halls used", v: stats.data.halls_used },
            { k: "Students seated", v: stats.data.students_seated },
            { k: "Date", v: date ?? "—" },
            { k: "Period", v: period },
          ].map((m) => (
            <div key={m.k} className="bg-card p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                {m.k}
              </p>
              <p className="mt-2 font-serif text-[1.75rem] tabular-nums leading-none">
                {String(m.v)}
              </p>
            </div>
          ))}
        </div>
      )}

      <Card>
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
                  <TableHead className="w-[200px]">Hall</TableHead>
                  <TableHead className="w-[140px] text-right">
                    Capacity
                  </TableHead>
                  <TableHead className="w-[140px] text-right">Used</TableHead>
                  <TableHead>Classes assigned</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.results.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="py-12 text-center font-serif italic text-muted-foreground"
                    >
                      No distribution for this slot.
                    </TableCell>
                  </TableRow>
                ) : (
                  list.data.results.map((row) => {
                    const used = row.items.reduce(
                      (n, it) => n + it.no_of_students,
                      0,
                    );
                    const ratio =
                      row.hall.capacity > 0 ? used / row.hall.capacity : 0;
                    return (
                      <TableRow key={row.id} className="align-top">
                        <TableCell className="font-serif text-[1.0625rem] tracking-[-0.005em]">
                          {row.hall.name}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-muted-foreground">
                          {row.hall.capacity.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="inline-flex flex-col items-end gap-1.5">
                            <span className="font-mono tabular-nums">
                              {used.toLocaleString()}
                            </span>
                            <span className="relative h-1 w-20 overflow-hidden rounded-full bg-[color:var(--border)]">
                              <span
                                className={
                                  "absolute inset-y-0 left-0 " +
                                  (ratio > 1
                                    ? "bg-[color:var(--accent-red-fg)]"
                                    : ratio > 0.85
                                      ? "bg-[color:var(--accent-yellow-fg)]"
                                      : "bg-foreground")
                                }
                                style={{
                                  width: `${Math.min(100, Math.round(ratio * 100))}%`,
                                }}
                              />
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="whitespace-normal">
                          <ul className="space-y-1.5">
                            {row.items.map((item) => (
                              <li
                                key={item.id}
                                className="flex flex-wrap items-baseline gap-2"
                              >
                                <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-1.5 py-0.5 font-mono text-[10px] tracking-wide">
                                  {item.schedule.department_slug}
                                </kbd>
                                <span className="font-serif text-[14px] tracking-[-0.005em]">
                                  {item.schedule.class_name}
                                </span>
                                <span className="font-mono text-[11px] text-muted-foreground">
                                  · {item.schedule.course_code}
                                </span>
                                <span className="ml-auto font-mono text-[11px] tabular-nums text-muted-foreground">
                                  {item.no_of_students}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          ) : (
            <p className="text-center text-muted-foreground">
              No distributions generated yet.
            </p>
          )}
        </CardContent>
      </Card>

      <JobProgressDialog
        jobId={jobId}
        title="Distribution generation"
        open={progressOpen}
        onOpenChange={setProgressOpen}
        onSuccess={() => {
          list.refetch();
          stats.refetch();
        }}
      />
    </div>
  );
}
