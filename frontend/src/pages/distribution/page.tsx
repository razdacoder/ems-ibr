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
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Distribution</h1>
          <p className="text-sm text-muted-foreground">
            Hall-to-class assignments for each exam slot.
          </p>
        </div>
        {isAdmin && (
          <Button onClick={onGenerate} disabled={!date || generate.isPending}>
            <Layers className="mr-2 h-4 w-4" /> Generate distribution
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

      {stats.data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Slot summary</CardTitle>
            <CardDescription>
              {stats.data.halls_used} halls hosting {stats.data.students_seated}{" "}
              students.
            </CardDescription>
          </CardHeader>
        </Card>
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
                  <TableHead>Hall</TableHead>
                  <TableHead className="text-right">Capacity</TableHead>
                  <TableHead>Classes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.data.results.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground">
                      No distribution for this slot.
                    </TableCell>
                  </TableRow>
                ) : (
                  list.data.results.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.hall.name}</TableCell>
                      <TableCell className="text-right">{row.hall.capacity}</TableCell>
                      <TableCell>
                        <ul className="list-disc space-y-0.5 pl-4">
                          {row.items.map((item) => (
                            <li key={item.id}>
                              {item.schedule.department_slug}{" "}
                              {item.schedule.class_name} —{" "}
                              {item.schedule.course_code} (
                              {item.no_of_students})
                            </li>
                          ))}
                        </ul>
                      </TableCell>
                    </TableRow>
                  ))
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
