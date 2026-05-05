import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import {
  useAllocation,
  useTimetableDates,
} from "@/api/scheduling";
import { useGenerateAllocation } from "@/api/jobs";
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
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

export default function AllocationPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const dates = useTimetableDates();
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");
  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const list = useAllocation({ date, period });
  const generate = useGenerateAllocation();
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressOpen, setProgressOpen] = useState(false);

  const onGenerate = async () => {
    if (!date || !period) return;
    try {
      const out = await generate.mutateAsync({ date, period });
      setJobId(out.job_id);
      setProgressOpen(true);
      toast({ title: "Allocation generation started" });
    } catch (err) {
      toast({
        title: "Could not start",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Seat allocation</h1>
          <p className="text-sm text-muted-foreground">
            Per-hall placement of students for each exam slot.
          </p>
        </div>
        {isAdmin && (
          <Button onClick={onGenerate} disabled={!date || generate.isPending}>
            <Sparkles className="mr-2 h-4 w-4" /> Generate allocation
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <Select
          value={date ?? ""}
          onValueChange={(v) => setDate(v)}
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
        <CardHeader>
          <CardTitle className="text-base">
            {date ? `${date} · ${period}` : "Pick a slot"}
          </CardTitle>
          <CardDescription>
            Click a hall to view per-seat placements.
          </CardDescription>
        </CardHeader>
        <CardContent>
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
                  <TableHead className="text-right">Placed</TableHead>
                  <TableHead className="text-right">Unplaced</TableHead>
                  <TableHead className="w-[120px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.results.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No allocations for this slot.
                    </TableCell>
                  </TableRow>
                ) : (
                  list.data.results.map((row) => (
                    <TableRow key={row.hall_id}>
                      <TableCell className="font-medium">{row.hall__name}</TableCell>
                      <TableCell className="text-right">{row.placed}</TableCell>
                      <TableCell className="text-right">{row.not_placed}</TableCell>
                      <TableCell>
                        <Button asChild size="sm" variant="outline">
                          <Link
                            to={`/allocation/hall?date=${date}&period=${period}&hall_id=${row.hall_id}`}
                          >
                            Open
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
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
