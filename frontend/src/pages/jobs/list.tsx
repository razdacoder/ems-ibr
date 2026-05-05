import { useState } from "react";
import {
  type BackgroundJob,
  type JobStatus,
  type JobType,
  useDeleteJob,
  useJobs,
  useRetryJob,
} from "@/api/jobs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { ListShell } from "@/components/data-table/list-shell";
import { PaginationFooter } from "@/components/data-table/pagination";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { JobProgressDialog } from "@/components/job-progress-dialog";

export default function JobsListPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("__all__");
  const [typeFilter, setTypeFilter] = useState<string>("__all__");
  const [activeJob, setActiveJob] = useState<BackgroundJob | null>(null);
  const [open, setOpen] = useState(false);

  const list = useJobs({
    page,
    status:
      statusFilter === "__all__" ? undefined : (statusFilter as JobStatus),
    job_type:
      typeFilter === "__all__" ? undefined : (typeFilter as JobType),
  });
  const remove = useDeleteJob();
  const retry = useRetryJob();

  const onDelete = async (job: BackgroundJob) => {
    if (!confirm(`Delete this ${job.job_type_display.toLowerCase()} job?`)) return;
    try {
      await remove.mutateAsync(job.job_id);
      toast({ title: "Job deleted" });
    } catch (err) {
      toast({
        title: "Delete failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  const onRetry = async (job: BackgroundJob) => {
    try {
      const out = await retry.mutateAsync(job.job_id);
      toast({ title: "Retry queued", description: out.job_id });
    } catch (err) {
      toast({
        title: "Retry failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <ListShell
        title="Jobs"
        description="Background jobs you've triggered (admins see jobs from everyone)."
        filters={
          <>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v); setPage(1); }}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All types</SelectItem>
                <SelectItem value="timetable">Timetable</SelectItem>
                <SelectItem value="distribution">Distribution</SelectItem>
                <SelectItem value="allocation">Allocation</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
        isLoading={list.isLoading}
        error={list.error}
        isEmpty={!list.data?.results.length}
        emptyMessage="No background jobs yet."
        pagination={
          list.data && (
            <PaginationFooter
              page={page}
              pageSize={15}
              total={list.data.count}
              onPageChange={setPage}
            />
          )
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Progress</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>By</TableHead>
              <TableHead className="w-[260px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((job) => (
              <TableRow key={job.job_id}>
                <TableCell className="font-medium">
                  {job.job_type_display}
                </TableCell>
                <TableCell>
                  <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                </TableCell>
                <TableCell className="text-right">{job.progress}%</TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(job.started_at).toLocaleString()}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {job.created_by_email}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setActiveJob(job);
                        setOpen(true);
                      }}
                    >
                      View
                    </Button>
                    {isAdmin && job.status === "failed" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onRetry(job)}
                        disabled={retry.isPending}
                      >
                        Retry
                      </Button>
                    )}
                    {isAdmin && (
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onDelete(job)}
                        disabled={
                          remove.isPending || job.status === "running"
                        }
                      >
                        Delete
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ListShell>
      <JobProgressDialog
        jobId={activeJob?.job_id ?? null}
        title={activeJob ? activeJob.job_type_display : "Job"}
        open={open}
        onOpenChange={setOpen}
      />
    </>
  );
}

function statusVariant(s: string) {
  if (s === "success") return "default" as const;
  if (s === "failed") return "destructive" as const;
  if (s === "running") return "secondary" as const;
  return "outline" as const;
}
