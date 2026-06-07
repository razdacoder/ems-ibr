import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import {
  useAllocation,
  useTimetableDates,
} from "@/api/scheduling";
import { useGenerateAllocationAll } from "@/api/jobs";
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
import { isSuperAdmin, useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

export default function AllocationPage() {
  const { user } = useAuth();
  // Only super admins may trigger generation; committee members view/export only.
  const isAdmin = isSuperAdmin(user);

  const dates = useTimetableDates();
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");
  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const list = useAllocation({ date, period });
  const generate = useGenerateAllocationAll();
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  const onGenerate = async () => {
    try {
      const out = await generate.mutateAsync();
      setJobId(out.job_id);
      setProgressOpen(true);
      toast({ title: "Seat allocation started for all slots" });
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
        section="Operations · Allocation"
        title="Seat allocation."
        description="Per-hall placement of students with anti-cheating adjacency rules. Generate once for every exam slot in the timetable; filter below to view a specific slot."
        actions={
          isAdmin && (
            <Button
              onClick={onGenerate}
              disabled={generate.isPending}
              size="lg"
              className="h-10"
            >
              <Sparkles className="mr-1.5 h-4 w-4" strokeWidth={2.25} />
              {generate.isPending ? "Starting…" : "Generate for all slots"}
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

      <Card>
        <CardHeader className="border-b border-[color:var(--border)]">
          <CardTitle className="font-serif text-[1.5rem] tracking-tight">
            {date ? `${date} · ${period}` : "Pick a slot"}
          </CardTitle>
          <CardDescription className="font-mono text-[10px] uppercase tracking-[0.14em]">
            Click a hall to view per-seat placements
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
                  <TableHead>Hall</TableHead>
                  <TableHead className="w-[120px] text-right">Placed</TableHead>
                  <TableHead className="w-[120px] text-right">
                    Unplaced
                  </TableHead>
                  <TableHead className="w-[180px]">Status</TableHead>
                  <TableHead className="w-[120px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.results.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="py-12 text-center font-serif italic text-muted-foreground"
                    >
                      No allocations for this slot.
                    </TableCell>
                  </TableRow>
                ) : (
                  list.data.results.map((row) => {
                    const total = row.placed + row.not_placed;
                    const ratio = total > 0 ? row.placed / total : 0;
                    const fullyPlaced = row.not_placed === 0;
                    return (
                      <TableRow key={row.hall_id}>
                        <TableCell className="font-serif text-[1.0625rem] tracking-[-0.005em]">
                          {row.hall__name}
                        </TableCell>
                        <TableCell className="text-right font-mono tabular-nums text-foreground">
                          {row.placed.toLocaleString()}
                        </TableCell>
                        <TableCell
                          className={
                            "text-right font-mono tabular-nums " +
                            (row.not_placed > 0
                              ? "text-[color:var(--accent-red-fg)]"
                              : "text-muted-foreground")
                          }
                        >
                          {row.not_placed.toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="relative h-1 w-20 overflow-hidden rounded-full bg-[color:var(--border)]">
                              <span
                                className={
                                  "absolute inset-y-0 left-0 " +
                                  (fullyPlaced
                                    ? "bg-[color:var(--accent-green-fg)]"
                                    : "bg-foreground")
                                }
                                style={{ width: `${Math.round(ratio * 100)}%` }}
                              />
                            </span>
                            <span className="font-mono text-[10px] tabular-nums uppercase tracking-[0.12em] text-muted-foreground">
                              {Math.round(ratio * 100)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            render={
                              date ? (
                                <Link
                                  to={`/allocation/hall?date=${date}&period=${period}&hall_id=${row.hall_id}`}
                                />
                              ) : (
                                <span />
                              )
                            }
                            size="sm"
                            variant="outline"
                            disabled={!date}
                          >
                            Open
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          ) : (
            <p className="text-center text-muted-foreground">
              No allocation generated yet for this slot.
            </p>
          )}
        </CardContent>
      </Card>

      <JobProgressDialog
        jobId={jobId}
        title="Seat allocation"
        open={progressOpen}
        onOpenChange={setProgressOpen}
        onSuccess={() => {
          list.refetch();
        }}
      />
    </div>
  );
}
